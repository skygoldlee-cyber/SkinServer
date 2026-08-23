#!/usr/bin/env bash
# =============================================================
# remote-status.sh — 서버측 상태 스냅샷 에이전트
#
#   Windows(원격)에서 SSH 한 번으로 서버 상태 전부를 긁어오기 위한
#   서버측 단일 진입점. Windows 클라이언트(remote.ps1)가 이 스크립트를
#   ssh 로 호출하고, 사람이 읽기 좋은 스냅샷을 stdout 으로 돌려준다.
#
#   설계 원칙:
#     * 단일 왕복 — 컨테이너·헬스·디스크·메모리·큐·GPU·최근 오류를
#       한 번의 SSH 호출로 수집한다(지연·인증 비용 최소화).
#     * 읽기 전용 — 어떤 것도 변경하지 않는다(모니터링 전용).
#     * 도구 없으면 건너뜀 — nvidia-smi/psql 이 없으면 해당 섹션 생략.
#
# 사용:
#   ./remote-status.sh [dev|staging|prod] [--json]
#
#   인자 없으면 실행 중인 컨테이너로 env 를 추론한다 (sl 과 동일 규칙).
#   --json  머신 파싱용 단일 JSON 오브젝트를 stdout 으로 출력.
#
# 종료 코드: 0 = 정상(또는 경고만), 1 = FAIL 항목 있음.
#
# 환경변수 (선택):
#   OPS_DIR / COMPOSE_DIR / ENV_DIR   위치 오버라이드 (deploy.sh 와 동일)
#   DATABASE_URL                      큐 적체 점검용(psql). 없으면 생략.
#   QUEUE_MAX                         큐 경고 임계(기본 200)
#   DISK_PCT_MAX                      디스크 경고 임계(기본 85)
#   GATEWAY_HEALTH_URL                엣지를 통한 게이트웨이 헬스 URL (없으면 로컬 컨테이너 헬스로 대체)
# =============================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPS_DIR="${OPS_DIR:-$(cd "$HERE/.." && pwd)}"        # deploy/
ROOT="$(cd "$OPS_DIR/.." && pwd)"                    # 리포 루트
COMPOSE_DIR="${COMPOSE_DIR:-$OPS_DIR/compose}"
ENV_DIR="${ENV_DIR:-$OPS_DIR/env}"

QUEUE_MAX="${QUEUE_MAX:-200}"
DISK_PCT_MAX="${DISK_PCT_MAX:-85}"
GATEWAY_HEALTH_URL="${GATEWAY_HEALTH_URL:-}"

ENV_ARG=""
JSON=0
while [ $# -gt 0 ]; do
  case "$1" in
    dev|staging|prod|production) ENV_ARG="$1"; shift;;
    --json) JSON=1; shift;;
    -h|--help) sed -n '2,33p' "$0"; exit 0;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

# ---- 색상 (JSON 모드면 비활성) ---------------------------------------------
if [ "$JSON" = "1" ] || [ ! -t 1 ]; then
  R=""; G=""; Y=""; D=""; N=""
else
  R=$'\033[31m'; G=$'\033[32m'; Y=$'\033[33m'; D=$'\033[2m'; N=$'\033[0m'
fi
PASS=0; FAILC=0; WARNC=0
ok()   { [ "$JSON" = "1" ] && return; echo "  ${G}[ OK ]${N} $1"; PASS=$((PASS+1)); }
ng()   { [ "$JSON" = "1" ] && return; echo "  ${R}[FAIL]${N} $1"; FAILC=$((FAILC+1)); }
wn()   { [ "$JSON" = "1" ] && return; echo "  ${Y}[WARN]${N} $1"; WARNC=$((WARNC+1)); }
sect() { [ "$JSON" = "1" ] && return; echo; echo "${Y}== $1 ==${N}"; }

# ---- compose 조합 (deploy.sh / sl 과 동일 규칙) ------------------------------
infer_env() {
  local cid envval
  cid="$(docker ps -q --filter name=sl_gateway 2>/dev/null | head -1 || true)"
  [ -n "$cid" ] || return 1
  envval="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$cid" 2>/dev/null | grep -E '^(ENV|DEV_DEBUG)=' || true)"
  echo "$envval" | grep -q '^ENV=prod'    && { echo prod; return 0; }
  echo "$envval" | grep -q '^ENV=staging' && { echo staging; return 0; }
  echo "$envval" | grep -q '^DEV_DEBUG=1' && { echo dev; return 0; }
  echo dev
}

ENV="$ENV_ARG"
if [ -z "$ENV" ]; then
  ENV="$(infer_env 2>/dev/null || echo dev)"
fi
[ "$ENV" = "production" ] && ENV="prod"

COMPOSE=(docker compose --env-file "$ENV_DIR/.env")
COMPOSE+=(-f "$COMPOSE_DIR/compose.base.yml")
case "$ENV" in
  dev)     COMPOSE+=(-f "$COMPOSE_DIR/compose.dev.yml");;
  staging) [ -f "$ENV_DIR/.env.images" ] && COMPOSE+=(--env-file "$ENV_DIR/.env.images"); COMPOSE+=(-f "$COMPOSE_DIR/compose.staging.yml");;
  prod)    [ -f "$ENV_DIR/.env.images" ] && COMPOSE+=(--env-file "$ENV_DIR/.env.images"); COMPOSE+=(-f "$COMPOSE_DIR/compose.prod.yml");
           [ -f "$COMPOSE_DIR/compose.tls.yml" ] && COMPOSE+=(-f "$COMPOSE_DIR/compose.tls.yml");;
esac
[ -f "$COMPOSE_DIR/compose.gpu.yml" ] && COMPOSE+=(-f "$COMPOSE_DIR/compose.gpu.yml")

# JSON 누적 버퍼 (키:값 쌍을 수집해 마지막에 방출)
J_HOST="$(hostname 2>/dev/null || echo unknown)"
J_TIME="$(date -Iseconds 2>/dev/null || date)"
J_UPTIME="$(cut -d' ' -f1 /proc/uptime 2>/dev/null || echo 0)"
J_CONTAINERS=""
J_DISK_PCT=0
J_MEM_PCT=0
J_QUEUE=-1
J_GPU_PCT=-1

# =============================================================
# 1) 호스트/시스템
# =============================================================
sect "호스트 (${J_HOST}) · env=${ENV}"
[ "$JSON" = "1" ] || echo "  ${D}시각 ${J_TIME} · 업타임 $(awk '{printf "%.1fh", $1/3600}' /proc/uptime 2>/dev/null || echo '?')${N}"

# ---- 디스크 ----
disk="$(df -P / 2>/dev/null | awk 'NR==2{gsub("%","",$5); print $5}')"
disk="${disk:-0}"; J_DISK_PCT="$disk"
if   [ "$disk" -ge "$DISK_PCT_MAX" ]; then ng "디스크 ${disk}% (>= ${DISK_PCT_MAX}%)"
elif [ "$disk" -ge $((DISK_PCT_MAX-10)) ]; then wn "디스크 ${disk}% (임계 ${DISK_PCT_MAX}% 근접)"
else ok "디스크 ${disk}%"; fi

# ---- 메모리 ----
if [ -r /proc/meminfo ]; then
  mem_total="$(awk '/MemTotal/{print $2}' /proc/meminfo)"
  mem_avail="$(awk '/MemAvailable/{print $2}' /proc/meminfo)"
  if [ -n "${mem_total:-0}" ] && [ "$mem_total" -gt 0 ]; then
    mem_pct=$(( (mem_total - mem_avail) * 100 / mem_total )); J_MEM_PCT="$mem_pct"
    if   [ "$mem_pct" -ge 90 ]; then ng "메모리 ${mem_pct}% 사용"
    elif [ "$mem_pct" -ge 75 ]; then wn "메모리 ${mem_pct}% 사용"
    else ok "메모리 ${mem_pct}% 사용"; fi
  fi
fi

# ---- GPU (있을 때만) ----
if command -v nvidia-smi >/dev/null 2>&1; then
  read -r gu gt < <(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 | tr ',' ' ')
  if [ -n "${gt:-0}" ] && [ "$gt" -gt 0 ]; then
    gp=$(( gu * 100 / gt )); J_GPU_PCT="$gp"
    [ "$gp" -ge 90 ] && wn "GPU VRAM ${gp}% (${gu}/${gt}MiB)" || ok "GPU VRAM ${gp}% (${gu}/${gt}MiB)"
  fi
fi

# =============================================================
# 2) 컨테이너 상태
# =============================================================
sect "컨테이너"
if ! docker info >/dev/null 2>&1; then
  ng "docker 데몬 무응답"
else
  # compose ps 라인을 그대로 보여주되, 헬스 불량 컨테이너를 카운트한다.
  ps_out="$("${COMPOSE[@]}" ps --format '{{.Name}}\t{{.Service}}\t{{.State}}\t{{.Status}}' 2>/dev/null || true)"
  if [ -z "$ps_out" ]; then
    wn "실행 중인 compose 컨테이너 없음 (env=${ENV})"
  else
    while IFS=$'\t' read -r name svc state status; do
      [ -n "$name" ] || continue
      line="$svc ($name) — $state $status"
      if echo "$status" | grep -qi 'unhealthy'; then ng "$line"
      elif echo "$state" | grep -qi 'running'; then
        echo "$status" | grep -qi 'health' && wn "$line" || ok "$line"
      else wn "$line"; fi
      J_CONTAINERS="${J_CONTAINERS}${name}|${svc}|${state}|${status};"
    done <<< "$ps_out"
  fi
fi

# =============================================================
# 3) 엔드포인트 헬스
# =============================================================
sect "엔드포인트"
# gateway 컨테이너 남북 헬스 (로컬) — 엣지 URL 이 없을 때의 기본 점검
gw_cid="$(docker ps -q --filter name=sl_gateway 2>/dev/null | head -1 || true)"
if [ -n "$gw_cid" ]; then
  code="$(docker exec "$gw_cid" python -c "import urllib.request,sys;sys.stdout.write(str(urllib.request.urlopen('http://localhost:8000/health').status))" 2>/dev/null || echo 000)"
  [ "$code" = "200" ] && ok "gateway /health (container) HTTP $code" || ng "gateway /health (container) HTTP $code"
else
  wn "gateway 컨테이너 없음 — /health 생략"
fi
# 엣지를 통한 외부 경로 헬스 (설정 시)
if [ -n "$GATEWAY_HEALTH_URL" ]; then
  ecode="$(curl -fsS -m 10 -o /dev/null -w '%{http_code}' "$GATEWAY_HEALTH_URL" 2>/dev/null || echo 000)"
  [ "$ecode" = "200" ] && ok "엣지 gateway 헬스 HTTP $ecode" || ng "엣지 gateway 헬스 HTTP $ecode"
fi

# =============================================================
# 4) 큐 적체 (DB)
# =============================================================
DBURL="${DATABASE_URL:-}"
[ -z "$DBURL" ] && DBURL="$(grep -E '^DATABASE_URL=' "$ENV_DIR/.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
if [ -n "$DBURL" ] && command -v psql >/dev/null 2>&1; then
  q="select count(*) from jobs where status in ('queued','processing');"
  n="$(psql "$DBURL" -tAc "$q" 2>/dev/null || echo "")"
  if [ -n "$n" ]; then
    J_QUEUE="$n"
    [ "$n" -ge "$QUEUE_MAX" ] && ng "큐 적체 ${n}건 (>= ${QUEUE_MAX})" || ok "큐 대기 ${n}건"
  else
    wn "큐 점검 실패 (psql 오류)"
  fi
else
  [ "$JSON" = "1" ] || echo "  ${D}(DATABASE_URL 또는 psql 없음 — 큐 점검 생략)${N}"
fi

# =============================================================
# 5) 최근 오류 로그 (gateway/worker, 최근 5줄)
# =============================================================
if [ "$JSON" != "1" ]; then
  sect "최근 오류 (gateway · worker)"
  err="$("${COMPOSE[@]}" logs --tail=200 gateway worker 2>/dev/null \
        | grep -iE 'error|exception|traceback|unhealthy|failed' | tail -5 || true)"
  if [ -n "$err" ]; then
    echo "$err" | while IFS= read -r l; do echo "  ${R}·${N} $l"; done
  else
    echo "  ${D}(최근 오류 없음)${D}${N}"
  fi
fi

# =============================================================
# 요약 / JSON 방출
# =============================================================
if [ "$JSON" = "1" ]; then
  printf '{'
  printf '"host":"%s","time":"%s","env":"%s",' "$J_HOST" "$J_TIME" "$ENV"
  printf '"disk_pct":%s,"mem_pct":%s,"gpu_pct":%s,"queue":%s,' "$J_DISK_PCT" "$J_MEM_PCT" "$J_GPU_PCT" "$J_QUEUE"
  printf '"fail":%s,"warn":%s,' "$FAILC" "$WARNC"
  printf '"containers":"%s"' "$J_CONTAINERS"
  printf '}\n'
  # JSON 모드에선 FAIL 여부로 종료코드 결정
  [ "$FAILC" -gt 0 ] && exit 1 || exit 0
fi

echo
if [ "$FAILC" -gt 0 ]; then
  echo "${R}상태 이상:${N} FAIL ${FAILC} · WARN ${WARNC} · OK ${PASS}"
  exit 1
elif [ "$WARNC" -gt 0 ]; then
  echo "${Y}경고 있음:${N} WARN ${WARNC} · OK ${PASS}"
  exit 0
else
  echo "${G}정상:${N} OK ${PASS}"
  exit 0
fi
