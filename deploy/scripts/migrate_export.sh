#!/usr/bin/env bash
# =============================================================
# migrate_export.sh  — 소스(WSL2 검증) 서버에서 실행
# DB 덤프 + 프로젝트 + 매니페스트를 단일 번들(tar.gz)로 생성
#
# 사용법:
#   ./migrate_export.sh
#   PROJECT_DIR=~/projects/webstack PG_CONTAINER=postgres ./migrate_export.sh
#
# 결과: ~/migration/migration_YYYYMMDD_HHMMSS.tgz
#   ⚠ 보안 위험 경고: 이 번들(.tgz)에는 .env 내의 평문 패스워드와 API 키가 포함됩니다.
#     - 파일 전송 시 반드시 SSH/SCP 등 보안 채널만 사용하십시오.
#     - 이관 작업 종료 즉시 소스 및 대상 서버 모두에서 이 번들 파일을 shred -u 등으로 파쇄 삭제하십시오.
# =============================================================
set -euo pipefail
umask 077   # 이 스크립트가 만드는 덤프·번들(.env 비밀 포함)을 0600 으로 생성

PROJECT_DIR="${PROJECT_DIR:-$HOME/projects/webstack}"
PG_CONTAINER="${PG_CONTAINER:-postgres}"
OUT_DIR="${OUT_DIR:-$HOME/migration}"
STAMP=$(date +%Y%m%d_%H%M%S)
WORK="$OUT_DIR/bundle_$STAMP"

[ -f "$PROJECT_DIR/.env" ] || { echo "ERROR: $PROJECT_DIR/.env 없음"; exit 1; }
mkdir -p "$WORK"

# .env 에서 DB 계정/이름 로드
# 주의: 'source'로 읽으면 값에 $, 백틱, 공백 등이 있을 때 셸이 이를 실행/오파싱합니다.
#       KEY=VALUE 만 안전하게 읽어들입니다(값의 앞뒤 따옴표는 제거).
load_env() {
  local file="$1" line key val
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|'#'*) continue ;; esac        # 빈 줄/주석 건너뜀
    [ "${line#*=}" = "$line" ] && continue           # '=' 없는 줄 건너뜀
    key="${line%%=*}"; val="${line#*=}"
    key="${key#"${key%%[![:space:]]*}"}"             # key 앞쪽 공백 제거
    key="${key%"${key##*[![:space:]]}"}"             # key 뒤쪽 공백 제거
    case "$key" in *[!A-Za-z0-9_]*|'') continue ;; esac  # 유효한 변수명만
    val="${val%$'\r'}"                               # CRLF 대비
    if [ "${val#\"}" != "$val" ] && [ "${val%\"}" != "$val" ]; then val="${val#\"}"; val="${val%\"}"
    elif [ "${val#\'}" != "$val" ] && [ "${val%\'}" != "$val" ]; then val="${val#\'}"; val="${val%\'}"; fi
    export "$key=$val"
  done < "$file"
}
load_env "$PROJECT_DIR/.env"
: "${POSTGRES_USER:?ERROR: .env 에 POSTGRES_USER 없음}"
: "${POSTGRES_DB:?ERROR: .env 에 POSTGRES_DB 없음}"

echo "[1/4] PostgreSQL 덤프 (custom 포맷)..."
# 주의: '-t'(TTY)는 출력의 \n 을 \r\n 으로 바꿔 -Fc 바이너리 덤프를 손상시킵니다. 절대 사용 금지.
docker exec "$PG_CONTAINER" pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > "$WORK/db.dump"

echo "[2/4] 프로젝트 아카이브 (.env 포함, 캐시 제외)..."
tar czf "$WORK/project.tgz" \
  --exclude='.venv' --exclude='.git' --exclude='backups' \
  --exclude='__pycache__' --exclude='*.pyc' \
  -C "$(dirname "$PROJECT_DIR")" "$(basename "$PROJECT_DIR")"

echo "[3/4] 매니페스트 작성..."
{
  echo "created : $(date '+%F %T')"
  echo "source  : $(uname -a)"
  echo "docker  : $(docker --version 2>/dev/null)"
  echo "compose : $(docker compose version 2>/dev/null | head -n1)"
  echo "db      : $POSTGRES_DB (user=$POSTGRES_USER)"
  echo "--- images ---"
  docker compose -f "$PROJECT_DIR/docker-compose.yml" images 2>/dev/null || true
} > "$WORK/MANIFEST.txt"

echo "[4/4] 번들 압축..."
tar czf "$OUT_DIR/migration_$STAMP.tgz" -C "$WORK" .
chmod 600 "$OUT_DIR/migration_$STAMP.tgz"   # umask 가 덮어써졌을 경우 대비(.env 비밀 포함)
rm -rf "$WORK"

echo
echo "완료: $OUT_DIR/migration_$STAMP.tgz"
echo "다음: scp \"$OUT_DIR/migration_$STAMP.tgz\" <user>@<대상서버>:~/"
echo "⚠ WARNING (보안 위험): 이 번들(.tgz)에는 .env 파일 내의 평문 패스워드 및 API 키가 포함되어 있습니다."
echo "  전송 완료 후 소스 서버와 대상 서버 양쪽에서 임시 번들 파일을 즉시 '안전 파쇄(삭제)'하세요."
echo "  [리눅스 안전 파쇄 예시]"
echo "    shred -u \"$OUT_DIR/migration_$STAMP.tgz\""
echo "  [일반 삭제 예시]"
echo "    rm -f \"$OUT_DIR/migration_$STAMP.tgz\""
