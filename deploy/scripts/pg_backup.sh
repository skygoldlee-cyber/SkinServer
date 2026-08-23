#!/usr/bin/env bash
# =============================================================
# pg_backup.sh — PostgreSQL 자동 백업 (가이드 18-1장)
# 계정/DB는 하드코딩하지 않고 .env 에서 읽어옵니다(설정 변경에 강함).
#
# 사용법:
#   ./pg_backup.sh
#   PROJECT_DIR=~/projects/webstack RETAIN_DAYS=14 ./pg_backup.sh
#
# 환경변수(모두 선택):
#   PROJECT_DIR(기본 ~/projects/webstack), PG_CONTAINER(postgres),
#   BACKUP_DIR(~/backups), RETAIN_DAYS(14)
#
#   [v3] 실전 견고성(모두 선택 — 안 주면 기존 동작 그대로):
#   MIN_KEEP(3)              나이와 무관하게 최신 N개는 항상 보존(보존 하한)
#   OFFSITE_DIR(빈값)         성공한 백업을 이 경로로 복제(예: /mnt/d/wsl-backups) — 오프사이트
#   BACKUP_GPG_RCPT(빈값)     이 GPG 공개키로 암호화 후 평문 삭제(gpg 필요)
#   BACKUP_ENC_PASSFILE(빈값) openssl AES-256 패스프레이즈 파일로 암호화(gpg 미사용 시)
#                            (BACKUP_GPG_RCPT 가 설정되면 그쪽이 우선)
#   HEALTHCHECK_URL(빈값)     성공 시에만 이 URL 로 핑(데드맨 스위치; 안 오면 외부서 알림)
#
# 주의: WSL + Docker Desktop 조합에서는 idle 시 Ubuntu 배포판이 종료되어
#       cron 이 깨어나지 못할 수 있습니다. 안정적 스케줄은 Windows 작업
#       스케줄러 + wsl-backup-task.ps1 을 쓰세요(가이드 18-2-1장).
# =============================================================
set -euo pipefail
umask 077                                   # 덤프(민감 데이터)를 0600 으로 생성

PROJECT_DIR="${PROJECT_DIR:-$HOME/projects/webstack}"
PG_CONTAINER="${PG_CONTAINER:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
RETAIN_DAYS="${RETAIN_DAYS:-14}"
MIN_KEEP="${MIN_KEEP:-3}"                    # [v3] 보존 하한
OFFSITE_DIR="${OFFSITE_DIR:-}"              # [v3] 오프사이트 복제 대상
BACKUP_GPG_RCPT="${BACKUP_GPG_RCPT:-}"     # [v3] GPG 수신자
BACKUP_ENC_PASSFILE="${BACKUP_ENC_PASSFILE:-}"  # [v3] openssl 패스프레이즈 파일
HEALTHCHECK_URL="${HEALTHCHECK_URL:-}"     # [v3] 데드맨 스위치 핑
mkdir -p "$BACKUP_DIR"
STAMP=$(date +%Y%m%d_%H%M%S)

# .env 에서 계정/DB 안전 파싱 (source 금지: 값의 $·백틱·공백을 셸이 실행하지 않도록)
load_env() {
  local file="$1" line key val
  [ -f "$file" ] || { echo "ERROR: $file 없음"; exit 1; }
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

# custom 포맷(-Fc): 압축 + 선택적 복구 가능
# 주의: '-t'(TTY)는 출력의 \n 을 \r\n 으로 바꿔 바이너리 덤프를 손상시키므로 절대 쓰지 않습니다.
# 실패 시 0바이트 파일을 남기지 않도록 임시파일에 받고 성공해야만 최종 이름으로 이동합니다.
TMP="$BACKUP_DIR/.${POSTGRES_DB}_$STAMP.dump.part"
FINAL="$BACKUP_DIR/${POSTGRES_DB}_$STAMP.dump"
if docker exec "$PG_CONTAINER" pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > "$TMP"; then
  mv "$TMP" "$FINAL"
else
  rm -f "$TMP"; echo "ERROR: pg_dump 실패 (컨테이너 기동/계정 확인)"; exit 1
fi

# ---- [v3] 저장 시 암호화 (덤프에 피부 이미지·분석 결과 등 민감정보 포함) ----
# GPG(공개키) 우선, 없으면 openssl(패스프레이즈 파일). 성공 시 평문 원본을 삭제.
if [ -n "$BACKUP_GPG_RCPT" ]; then
  if gpg --batch --yes --trust-model always \
         --encrypt --recipient "$BACKUP_GPG_RCPT" --output "$FINAL.gpg" "$FINAL"; then
    rm -f "$FINAL"; FINAL="$FINAL.gpg"
  else
    echo "ERROR: gpg 암호화 실패 (수신자 키 확인: $BACKUP_GPG_RCPT)"; exit 1
  fi
elif [ -n "$BACKUP_ENC_PASSFILE" ]; then
  if [ ! -r "$BACKUP_ENC_PASSFILE" ]; then
    echo "ERROR: BACKUP_ENC_PASSFILE 읽기 불가: $BACKUP_ENC_PASSFILE"; exit 1
  fi
  if openssl enc -aes-256-cbc -pbkdf2 -salt \
         -in "$FINAL" -out "$FINAL.enc" -pass file:"$BACKUP_ENC_PASSFILE"; then
    rm -f "$FINAL"; FINAL="$FINAL.enc"
  else
    echo "ERROR: openssl 암호화 실패"; exit 1
  fi
fi

# ---- [v3] 오프사이트 복제 (같은 WSL 디스크 장애 시 동반 소실 방지) ----
if [ -n "$OFFSITE_DIR" ]; then
  if mkdir -p "$OFFSITE_DIR" 2>/dev/null && cp -f "$FINAL" "$OFFSITE_DIR/"; then
    echo "[$(date '+%F %T')] offsite copy: $OFFSITE_DIR/$(basename "$FINAL")"
  else
    # 오프사이트 실패는 로컬 백업 자체를 무효화하진 않으므로 경고만 (핑은 아래에서 성공 처리 전 판단)
    echo "WARN: 오프사이트 복제 실패: $OFFSITE_DIR (마운트/권한 확인)"
  fi
fi

# ---- [v3] 보관: RETAIN_DAYS 초과분 삭제하되, 최신 MIN_KEEP 개는 무조건 보존 ----
#      (백업이 며칠 멈춰도 마지막 정상본까지 지워지지 않도록 하한을 둔다)
#      암호화 확장자(.gpg/.enc)까지 포함해 최신순으로 훑는다.
mapfile -t _bk < <(ls -1t "$BACKUP_DIR"/${POSTGRES_DB}_*.dump* 2>/dev/null)
_i=0
for _f in "${_bk[@]}"; do
  _i=$((_i+1))
  [ "$_i" -le "$MIN_KEEP" ] && continue                       # 최신 MIN_KEEP 개 보존
  if [ -n "$(find "$_f" -mtime +"$RETAIN_DAYS" 2>/dev/null)" ]; then
    rm -f -- "$_f"; echo "[$(date '+%F %T')] pruned: $(basename "$_f")"
  fi
done

echo "[$(date '+%F %T')] backup done: $(basename "$FINAL")"

# ---- [v3] 데드맨 스위치: 여기까지 왔으면 성공 → 성공 시에만 핑 ----
#      (스크립트가 중간에 exit 하면 핑이 안 가고, 외부 서비스가 '누락'으로 알림)
if [ -n "$HEALTHCHECK_URL" ]; then
  curl -fsS -m 10 "$HEALTHCHECK_URL" >/dev/null 2>&1 \
    || echo "WARN: healthcheck 핑 실패(백업 자체는 성공): $HEALTHCHECK_URL"
fi
