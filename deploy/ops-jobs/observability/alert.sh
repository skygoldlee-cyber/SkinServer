#!/usr/bin/env bash
# =============================================================
# alert.sh — 최소 알림 (②)
#
#  점검: 디스크 사용률 / GPU VRAM / 큐 적체(Postgres) /
#        Supabase 상태 / AI Server gateway 헬스. 임계 초과 시 $ALERT_WEBHOOK 로 통지.
#  의존성 가볍게: bash + curl (+ 있으면 nvidia-smi, psql). 각 점검은 도구 없으면 건너뜀.
#
#  환경변수:
#    ALERT_WEBHOOK   Slack/Discord/generic incoming webhook URL (필수)
#    DISK_PCT_MAX    디스크 경고 임계(기본 85)
#    VRAM_PCT_MAX    GPU VRAM 경고 임계(기본 90)
#    QUEUE_MAX       queued+processing 잡 경고 임계(기본 200)
#    DATABASE_URL    큐 점검용(psql). 없으면 큐 점검 생략.
#    T_JOBS/C_STATUS 스키마 매핑(기본 jobs/status), OPEN_STATES(기본 'queued','processing')
#    GATEWAY_HEALTH_URL  AI Server gateway 헬스 URL (예: https://api.example.com/health/db). 없으면 생략.
#    SUPABASE_HEALTH_URL Supabase 프로젝트 헬스 URL (예: https://<ref>.supabase.co/auth/v1/health). 없으면 생략.
#
#  사용:
#    ALERT_WEBHOOK=https://hooks... ./alert.sh
#    (crontab.example 에서 5분마다. deploy.sh 실패 시에도 호출 가능 — README 참고)
# =============================================================
set -euo pipefail

WEBHOOK="${ALERT_WEBHOOK:-}"
DISK_PCT_MAX="${DISK_PCT_MAX:-85}"
VRAM_PCT_MAX="${VRAM_PCT_MAX:-90}"
QUEUE_MAX="${QUEUE_MAX:-200}"
T_JOBS="${T_JOBS:-jobs}"
C_STATUS="${C_STATUS:-status}"
# worker 큐 상태는 deploy/db/migrations/0001_init.sql 기준 queued/processing.
OPEN_STATES="${OPEN_STATES:-'queued','processing'}"
GATEWAY_HEALTH_URL="${GATEWAY_HEALTH_URL:-}"
SUPABASE_HEALTH_URL="${SUPABASE_HEALTH_URL:-}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-10}"

alerts=()

notify() {  # $1=메시지
  echo "ALERT: $1" >&2
  [ -n "$WEBHOOK" ] || { echo "  (ALERT_WEBHOOK 미설정 — 통지 생략)" >&2; return; }
  # Slack/Discord 공통으로 먹는 최소 페이로드
  curl -fsS -m 10 -H 'Content-Type: application/json' \
    -d "$(printf '{"text":"[SkinLens] %s","content":"[SkinLens] %s"}' "$1" "$1")" \
    "$WEBHOOK" >/dev/null || echo "  (webhook 전송 실패)" >&2
}

# 1) 디스크
disk=$(df -P / | awk 'NR==2{gsub("%","",$5); print $5}')
[ "${disk:-0}" -ge "$DISK_PCT_MAX" ] && alerts+=("디스크 ${disk}% (>=$DISK_PCT_MAX)")

# 2) GPU VRAM (nvidia-smi 있을 때만)
if command -v nvidia-smi >/dev/null 2>&1; then
  read -r used total < <(nvidia-smi --query-gpu=memory.used,memory.total \
      --format=csv,noheader,nounits | head -1 | tr ',' ' ')
  if [ -n "${total:-}" ] && [ "$total" -gt 0 ]; then
    pct=$(( used * 100 / total ))
    [ "$pct" -ge "$VRAM_PCT_MAX" ] && alerts+=("GPU VRAM ${pct}% (${used}/${total}MiB)")
  fi
fi

# 3) 큐 적체 (DATABASE_URL + psql 있을 때만)
if [ -n "${DATABASE_URL:-}" ] && command -v psql >/dev/null 2>&1; then
  q="select count(*) from ${T_JOBS} where ${C_STATUS} in (${OPEN_STATES});"
  n=$(psql "$DATABASE_URL" -tAc "$q" 2>/dev/null || echo "")
  if [ -n "$n" ] && [ "$n" -ge "$QUEUE_MAX" ]; then
    alerts+=("큐 적체 ${n}건 (>=$QUEUE_MAX)")
  fi
fi

# 4) AI Server gateway 헬스 (GATEWAY_HEALTH_URL 설정 시)
if [ -n "$GATEWAY_HEALTH_URL" ]; then
  code=$(curl -fsS -m "$HEALTH_TIMEOUT" -o /dev/null -w '%{http_code}' "$GATEWAY_HEALTH_URL" 2>/dev/null || echo "000")
  if [ "$code" != "200" ]; then
    alerts+=("gateway 헬스 이상 (HTTP $code @ $GATEWAY_HEALTH_URL)")
  fi
fi

# 5) Supabase 상태 (SUPABASE_HEALTH_URL 설정 시 — auth/v1/health 는 200 기대)
if [ -n "$SUPABASE_HEALTH_URL" ]; then
  code=$(curl -fsS -m "$HEALTH_TIMEOUT" -o /dev/null -w '%{http_code}' "$SUPABASE_HEALTH_URL" 2>/dev/null || echo "000")
  if [ "$code" != "200" ]; then
    alerts+=("Supabase 상태 이상 (HTTP $code @ $SUPABASE_HEALTH_URL)")
  fi
fi

if [ "${#alerts[@]}" -gt 0 ]; then
  msg=$(printf '%s · ' "${alerts[@]}"); msg="${msg% · }"
  notify "$msg"
  exit 1
fi
echo "ok: 이상 없음"
