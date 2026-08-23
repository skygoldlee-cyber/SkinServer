#!/usr/bin/env bash
# =============================================================
# deploy.sh — 서버측 공통 배포 (self-hosted 러너가 호출)
#
# 하는 일: .env.images 의 해당 서비스 태그를 새 이미지로 원자적 교체
#          → (필요시 GHCR pull) → up -d → 헬스체크 대기
#          → 실패하면 이전 태그로 자동 롤백.
#
# 사용:
#   ./deploy.sh --service gateway         --image sl_gateway:abc123            --env staging
#   ./deploy.sh --service engine-analysis --image ghcr.io/OWNER/...:abc123 --env production --pull
#
# 환경변수:
#   OPS_DIR      배포 체크아웃 루트 (기본: 이 스크립트의 ../.. = deploy/)
#   COMPOSE_DIR  compose 파일 위치 (기본: $OPS_DIR/compose)
#   ENV_DIR      .env / .env.images 위치 (기본: $OPS_DIR/env)
#   HEALTH_TIMEOUT  헬스체크 대기 초 (기본 120)
#
# (통합) compose.base.yml + 환경 오버레이(compose.<env>.yml) 조합으로 실행.
#        staging→compose.staging.yml, production→compose.prod.yml.
# (P1)   동시 배포 직렬화: .env.images read-modify-write 레이스를 flock 으로 차단.
# (P0)   compose.gpu.yml / compose.tls.yml 이 존재하면 자동으로 -f 로 얹는다.
# =============================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPS_DIR="${OPS_DIR:-$(cd "$HERE/.." && pwd)}"        # deploy/
COMPOSE_DIR="${COMPOSE_DIR:-$OPS_DIR/compose}"
ENV_DIR="${ENV_DIR:-$OPS_DIR/env}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"

SERVICE=""; IMAGE=""; ENVN="staging"; DO_PULL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --service) SERVICE="$2"; shift 2;;
    --image)   IMAGE="$2";   shift 2;;
    --env)     ENVN="$2";    shift 2;;
    --pull)    DO_PULL=1;    shift;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[ -n "$SERVICE" ] && [ -n "$IMAGE" ] || { echo "usage: --service <name> --image <ref> [--env staging|production] [--pull]" >&2; exit 2; }

IMAGES_FILE="$ENV_DIR/.env.images"
[ -f "$IMAGES_FILE" ] || { echo "missing $IMAGES_FILE (cp $ENV_DIR/.env.images.example $IMAGES_FILE)" >&2; exit 1; }
[ -f "$ENV_DIR/.env" ] || { echo "missing $ENV_DIR/.env (cp $ENV_DIR/.env.example $ENV_DIR/.env)" >&2; exit 1; }

# ---- (P1) 배포 직렬화 락 ----------------------------------------------------
exec 9>"$ENV_DIR/.env.images.lock"
flock 9

# ---- compose 호출(base + 환경 오버레이 + 존재하는 하드웨어 오버레이) --------
case "$ENVN" in
  staging)              ENV_OVERLAY="compose.staging.yml";;
  production|prod)      ENV_OVERLAY="compose.prod.yml";;
  *) echo "unknown env: $ENVN (staging|production)" >&2; exit 2;;
esac

COMPOSE=(docker compose --env-file "$ENV_DIR/.env" --env-file "$IMAGES_FILE")
COMPOSE+=(-f "$COMPOSE_DIR/compose.base.yml")
COMPOSE+=(-f "$COMPOSE_DIR/$ENV_OVERLAY")
[ -f "$COMPOSE_DIR/compose.gpu.yml" ] && COMPOSE+=(-f "$COMPOSE_DIR/compose.gpu.yml")
[ -f "$COMPOSE_DIR/compose.tls.yml" ] && COMPOSE+=(-f "$COMPOSE_DIR/compose.tls.yml")

# service -> .env.images 변수명 (engine-analysis -> ENGINE_ANALYSIS_IMAGE)
VAR="$(echo "$SERVICE" | tr '[:lower:]-' '[:upper:]_')_IMAGE"

# 현재 값(롤백용) 백업
PREV="$(grep -E "^${VAR}=" "$IMAGES_FILE" | head -1 | cut -d= -f2- || true)"

set_var() {  # $1=key $2=val — 원자적 갱신(없으면 추가)
  local tmp; tmp="$(mktemp "${IMAGES_FILE}.XXXX")"
  if grep -qE "^$1=" "$IMAGES_FILE"; then
    sed "s|^$1=.*|$1=$2|" "$IMAGES_FILE" > "$tmp"
  else
    cat "$IMAGES_FILE" > "$tmp"; echo "$1=$2" >> "$tmp"
  fi
  mv "$tmp" "$IMAGES_FILE"
}

wait_healthy() {  # $1=service $2=timeout
  local svc="$1" timeout="$2" cid start hs
  cid="$("${COMPOSE[@]}" ps -q "$svc" || true)"
  [ -n "$cid" ] || { echo "  ! 컨테이너 없음: $svc"; return 1; }
  if [ "$(docker inspect --format '{{if .State.Health}}yes{{end}}' "$cid" 2>/dev/null)" = "yes" ]; then
    start=$SECONDS
    while :; do
      hs="$(docker inspect --format '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo starting)"
      case "$hs" in
        healthy)   return 0;;
        unhealthy) echo "  ! unhealthy: $svc"; return 1;;
      esac
      [ $((SECONDS-start)) -ge "$timeout" ] && { echo "  ! 헬스체크 타임아웃: $svc ($hs)"; return 1; }
      sleep 3
    done
  else
    sleep 5
    [ "$(docker inspect --format '{{.State.Running}}' "$cid" 2>/dev/null)" = "true" ] && return 0
    echo "  ! 미기동: $svc"; return 1
  fi
}

bring_up() {  # $1=image ref
  set_var "$VAR" "$1"
  if [ "$DO_PULL" = "1" ]; then
    echo "  · pull $1"
    "${COMPOSE[@]}" pull "$SERVICE"
  fi
  echo "  · up -d $SERVICE"
  "${COMPOSE[@]}" up -d "$SERVICE"
}

echo "[deploy] env=$ENVN service=$SERVICE"
echo "  · $VAR: ${PREV:-<none>}  ->  $IMAGE"
bring_up "$IMAGE"

if wait_healthy "$SERVICE" "$HEALTH_TIMEOUT"; then
  echo "[deploy] ✅ $SERVICE 정상 (=$IMAGE)"
  docker image prune -f >/dev/null 2>&1 || true
  exit 0
fi

echo "[deploy] ⛔ $SERVICE 배포 실패 → 롤백"
if [ -n "$PREV" ]; then
  echo "  · rollback -> $PREV"
  bring_up "$PREV"
  if wait_healthy "$SERVICE" "$HEALTH_TIMEOUT"; then
    echo "[deploy] ↩︎ 롤백 성공 ($SERVICE=$PREV) — 배포는 실패로 종료"
  else
    echo "[deploy] ‼︎ 롤백 후에도 비정상 — 수동 확인 필요 ($SERVICE)"
  fi
else
  echo "  ! 이전 태그 없음 — 롤백 불가(최초 배포로 추정). 로그 확인:"
  echo "    ${COMPOSE[*]} logs --tail=100 $SERVICE"
fi
exit 1
