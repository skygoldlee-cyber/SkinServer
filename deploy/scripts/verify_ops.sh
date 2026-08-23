#!/usr/bin/env bash
# =============================================================
# verify_ops.sh  — 운영 정기/재부팅 후 점검 (가이드 §21 13항목 자동화)
#
# 보안 항목(sshd 적용값·컨테이너 하드닝·포트 노출)은 verify_server.sh hardening 이
# 담당하므로, 이 스크립트는 운영 건강도(복구·백업 신선도·리소스·네트워크·갱신)에
# 집중하고 마지막에 하드닝 재검증을 안내/위임합니다.
#
# 사용법:
#   chmod +x verify_ops.sh
#   ./verify_ops.sh                 # 전체
#   ./verify_ops.sh --with-hardening # 끝에 verify_server.sh hardening 도 실행
#
# 환경변수(기본값):
#   BACKUP_DIR=~/backups  OFFSITE_DIR=/mnt/d/wsl-backups
#   FRESH_DAYS=2  DISK_WARN=80  DISK_FAIL=90
#
# 종료 코드: FAIL 0건이면 0, 아니면 1 (cron/스케줄러 연동 가능)
# =============================================================

set -uo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0; WARN=0
ok()      { echo -e "  ${GREEN}[PASS]${NC} $1"; PASS=$((PASS+1)); }
ng()      { echo -e "  ${RED}[FAIL]${NC} $1"; FAIL=$((FAIL+1)); }
warn()    { echo -e "  ${YELLOW}[WARN]${NC} $1"; WARN=$((WARN+1)); }
info()    { echo -e "     ↳ $1"; }
section() { echo -e "\n${YELLOW}== $1 ==${NC}"; }

BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
OFFSITE_DIR="${OFFSITE_DIR:-/mnt/d/wsl-backups}"
FRESH_DAYS="${FRESH_DAYS:-2}"
DISK_WARN="${DISK_WARN:-80}"
DISK_FAIL="${DISK_FAIL:-90}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- 1) 컨테이너·복구 -----------------------------------------
check_recovery() {
  section "[recovery] 컨테이너 상태·재시작 정책"
  if ! command -v docker >/dev/null 2>&1; then warn "docker 없음 → 스킵"; return; fi
  local names n st rp up=0 total=0
  names=$(docker ps -a --format '{{.Names}}' 2>/dev/null)
  for n in $names; do
    total=$((total+1))
    st=$(docker inspect "$n" --format '{{.State.Status}}' 2>/dev/null)
    rp=$(docker inspect "$n" --format '{{.HostConfig.RestartPolicy.Name}}' 2>/dev/null)
    if [ "$st" = running ]; then up=$((up+1)); fi
    case "$rp" in
      unless-stopped|always) : ;;
      *) warn "컨테이너 $n: restart=$rp (unless-stopped/always 권장)";;
    esac
  done
  if [ "$total" -eq 0 ]; then warn "실행/정의된 컨테이너 없음"
  elif [ "$up" -eq "$total" ]; then ok "컨테이너 $up/$total Up"
  else ng "컨테이너 $up/$total 만 Up — 재부팅 자동복구 확인(16장)"; fi
  info "심층 확인: ./verify_server.sh all  +  로컬 verify_client.ps1"
}

# --- 2) 백업 신선도 -------------------------------------------
check_backup() {
  section "[backup] 백업 신선도·오프사이트·스냅샷"
  if [ -d "$BACKUP_DIR" ]; then
    local latest; latest=$(ls -t "$BACKUP_DIR"/*.dump "$BACKUP_DIR"/*.sql* 2>/dev/null | head -n1)
    if [ -n "${latest:-}" ]; then
      if [ -n "$(find "$latest" -mtime -"$FRESH_DAYS" 2>/dev/null)" ]; then
        ok "최근 백업 $FRESH_DAYS일 내: $(basename "$latest")"
      else
        ng "최근 백업이 ${FRESH_DAYS}일보다 오래됨 → WSL idle 누락 의심(18-2-1): $(basename "$latest")"
      fi
    else warn "$BACKUP_DIR 에 덤프 없음"; fi
    # 백업 로그 상 마지막 실행 성공 여부(있으면)
    if [ -f "$BACKUP_DIR/backup.log" ]; then
      tail -n1 "$BACKUP_DIR/backup.log" | grep -qiE 'ok|success|완료|성공' \
        && ok "backup.log 마지막 항목 성공" \
        || warn "backup.log 마지막 항목이 성공 아님 — 확인 필요"
    fi
  else warn "$BACKUP_DIR 없음(운영 서버는 Supabase PITR면 정상)"; fi

  # 오프사이트·암호화 사본
  if ls "$OFFSITE_DIR"/*.gpg "$OFFSITE_DIR"/*.enc >/dev/null 2>&1; then
    ok "오프사이트·암호화 사본 존재($OFFSITE_DIR)"
  else warn "오프사이트·암호화 사본 미검출($OFFSITE_DIR/*.gpg|*.enc) — 18-1 확인"; fi

  # WSL 롤백 스냅샷
  if ls "$OFFSITE_DIR"/ubuntu_*.tar >/dev/null 2>&1; then
    ok "WSL 스냅샷 존재(15-A): $(ls -t "$OFFSITE_DIR"/ubuntu_*.tar | head -n1 | xargs basename)"
  else warn "WSL --export 스냅샷 미검출 — 위험 변경 전 생성 권장(15-A)"; fi

  warn "복구 리허설은 자동 실행하지 않음 → 월 1회 수동: 18-3(임시 DB 복원)"
}

# --- 3) 리소스·네트워크 ---------------------------------------
check_resource() {
  section "[resource] 디스크·네트워크"
  # 디스크 사용률(루트)
  local use; use=$(df -P / 2>/dev/null | awk 'NR==2{gsub("%","",$5); print $5}')
  if [ -n "${use:-}" ]; then
    if [ "$use" -ge "$DISK_FAIL" ]; then ng "루트 디스크 사용률 ${use}% (>=${DISK_FAIL}%)"
    elif [ "$use" -ge "$DISK_WARN" ]; then warn "루트 디스크 사용률 ${use}% (>=${DISK_WARN}%)"
    else ok "루트 디스크 사용률 ${use}%"; fi
  else warn "디스크 사용률 확인 불가"; fi
  command -v docker >/dev/null 2>&1 && info "도커 사용량: $(docker system df --format '{{.Type}} {{.Size}}' 2>/dev/null | tr '\n' ' ')"

  # portproxy(Windows) — 미러 모드면 불필요
  if command -v netsh.exe >/dev/null 2>&1; then
    local rules; rules=$(netsh.exe interface portproxy show v4tov4 2>/dev/null | grep -cE '^[0-9]')
    if [ "${rules:-0}" -gt 0 ]; then ok "portproxy 규칙 ${rules}건 존재(NAT 모드)"
    else warn "portproxy 규칙 없음(미러 모드면 정상, NAT면 16-2로 갱신)"; fi
  else info "netsh 미가용(WSL 밖에서 확인) — 미러 모드면 무관"; fi
}

# --- 4) 갱신·서비스 -------------------------------------------
check_update() {
  section "[update] 보안 업데이트·fail2ban·인증서"
  if sudo -n true 2>/dev/null && command -v unattended-upgrade >/dev/null 2>&1; then
    local n; n=$(sudo unattended-upgrade --dry-run 2>/dev/null | grep -c 'Inst ' || true)
    info "보류 중 보안 업데이트(추정) ${n:-?}건 — 재부팅 정책은 21-1"
  else warn "unattended-upgrade dry-run 스킵(sudo 무권한/미설치)"; fi

  if command -v fail2ban-client >/dev/null 2>&1; then
    sudo -n fail2ban-client status sshd >/dev/null 2>&1 && ok "fail2ban sshd jail 동작" \
      || warn "fail2ban sshd 상태 확인 불가(WSL NAT면 의도적일 수 있음)"
  else warn "fail2ban 미설치"; fi

  if command -v certbot >/dev/null 2>&1; then
    certbot certificates 2>/dev/null | grep -qi 'VALID' && ok "certbot 인증서 유효" || warn "certbot 인증서 상태 확인"
  else info "certbot 미사용(Caddy 자동 갱신이거나 HTTPS 미적용이면 무관)"; fi
}

# --- 보안 재검증 위임 -----------------------------------------
run_hardening() {
  section "[delegate] 보안 하드닝 재검증"
  if [ -x "$SCRIPT_DIR/verify_server.sh" ]; then
    "$SCRIPT_DIR/verify_server.sh" hardening
  else
    warn "verify_server.sh 없음 → 수동: ./verify_server.sh hardening (+ 다른 PC verify_client -Check ports)"
  fi
}

main() {
  local with_hard=0
  [ "${1:-}" = "--with-hardening" ] && with_hard=1
  echo "============================================================"
  echo " 운영 점검 verify_ops : $(date '+%Y-%m-%d %H:%M:%S')"
  echo "============================================================"
  check_recovery
  check_backup
  check_resource
  check_update
  [ "$with_hard" -eq 1 ] && run_hardening
  echo -e "\n============================================================"
  echo -e " 결과:  ${GREEN}PASS ${PASS}${NC} / ${RED}FAIL ${FAIL}${NC} / ${YELLOW}WARN ${WARN}${NC}"
  echo    " (보안 항목 전체 재검증: ./verify_ops.sh --with-hardening 또는 ./verify_server.sh hardening)"
  echo    "============================================================"
  [ "$FAIL" -eq 0 ] && exit 0 || exit 1
}

main "$@"
