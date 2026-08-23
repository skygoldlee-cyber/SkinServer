#!/usr/bin/env bash
# =============================================================
# migrate_import.sh  — 대상(외부 호스팅) 서버에서 실행
# 번들 해제 → 프로젝트/.env 복원 → postgres 먼저 기동 → DB 복원 → 전체 스택 기동
#
# 전제: 대상 서버에 docker + docker compose plugin 설치 완료(본 가이드 8-B장)
#
# 사용법:
#   ./migrate_import.sh ~/migration_YYYYMMDD_HHMMSS.tgz
#   DEST=~/projects PG_CONTAINER=postgres ./migrate_import.sh <번들>
# =============================================================
set -euo pipefail
umask 077   # 복원되는 .env·임시 파일을 0600 으로 (비밀 노출 방지)

BUNDLE="${1:?사용법: ./migrate_import.sh <migration_YYYYMMDD_HHMMSS.tgz>}"
DEST="${DEST:-$HOME/projects}"
PG_CONTAINER="${PG_CONTAINER:-postgres}"

command -v docker >/dev/null 2>&1 || { echo "ERROR: docker 미설치 (가이드 8-B장 먼저)"; exit 1; }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
tar xzf "$BUNDLE" -C "$WORK"

echo "[1/5] 프로젝트 복원..."
mkdir -p "$DEST"
tar xzf "$WORK/project.tgz" -C "$DEST"
PROJECT_DIR="$DEST/$(tar tzf "$WORK/project.tgz" | head -n1 | cut -d/ -f1)"
echo "  → $PROJECT_DIR"

echo "[2/5] .env 확인..."
[ -f "$PROJECT_DIR/.env" ] || { echo "ERROR: .env 없음 — 보안 채널로 전송 필요"; exit 1; }
# 'source' 대신 KEY=VALUE 만 안전 파싱 (값의 $·백틱·공백을 셸이 실행하지 않도록)
load_env() {
  local file="$1" line key val
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|'#'*) continue ;; esac
    [ "${line#*=}" = "$line" ] && continue
    key="${line%%=*}"; val="${line#*=}"
    key="${key#"${key%%[![:space:]]*}"}"; key="${key%"${key##*[![:space:]]}"}"
    case "$key" in *[!A-Za-z0-9_]*|'') continue ;; esac
    val="${val%$'\r'}"
    if [ "${val#\"}" != "$val" ] && [ "${val%\"}" != "$val" ]; then val="${val#\"}"; val="${val%\"}"
    elif [ "${val#\'}" != "$val" ] && [ "${val%\'}" != "$val" ]; then val="${val#\'}"; val="${val%\'}"; fi
    export "$key=$val"
  done < "$file"
}
load_env "$PROJECT_DIR/.env"
: "${POSTGRES_USER:?ERROR: .env 에 POSTGRES_USER 없음}"
: "${POSTGRES_DB:?ERROR: .env 에 POSTGRES_DB 없음}"

echo "[3/5] postgres 먼저 기동 후 healthy 대기..."
cd "$PROJECT_DIR"
docker compose up -d postgres
ok=0
for i in $(seq 1 30); do
  if docker exec "$PG_CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then ok=1; break; fi
  sleep 2
done
[ "$ok" = 1 ] || { echo "ERROR: postgres 준비 실패"; exit 1; }

echo "[4/5] DB 복원..."
docker exec -i "$PG_CONTAINER" pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists < "$WORK/db.dump"

echo "[5/5] 전체 스택 기동..."
docker compose up -d --build

echo
echo "완료. 검증:"
echo "  ./verify_server.sh all"
echo "  (로컬 PC) verify_client.ps1 -RemoteHost <대상 도메인/IP> -SshUser <user>"
