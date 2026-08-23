#!/usr/bin/env bash
# =============================================================
# verify_server.sh  (모듈형)
# WSL2 Ubuntu 서버 환경 검증 — 각 구축 단계 직후 부분 실행 가능
#
# 사용법:
#   chmod +x verify_server.sh
#   ./verify_server.sh            # 전체(all)
#   ./verify_server.sh ssh        # SSH 서버만
#   ./verify_server.sh docker     # Docker 엔진만
#   ./verify_server.sh --help     # 모듈 목록
#
# 모듈 ↔ 구축 단계 대응:
#   base(기본설정 후) ssh(SSH설정 후) github(GitHub연결 후) docker(Docker설치 후)
#   nginx(Nginx구성 후) fastapi(FastAPI구성 후) postgres(PostgreSQL구성 후)
#   services(웹스택 3종 묶음) hardening(하드닝 9-3-1·20·v3 후) all(전체)
#
# 종료 코드: FAIL 0건이면 0, 아니면 1 (CI 연동 가능)
# =============================================================

set -uo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0; WARN=0
ok()      { echo -e "  ${GREEN}[PASS]${NC} $1"; PASS=$((PASS+1)); }
ng()      { echo -e "  ${RED}[FAIL]${NC} $1"; FAIL=$((FAIL+1)); }
warn()    { echo -e "  ${YELLOW}[WARN]${NC} $1"; WARN=$((WARN+1)); }
section() { echo -e "\n${YELLOW}== $1 ==${NC}"; }
check_cmd() {
  if command -v "$2" >/dev/null 2>&1; then
    ok "$1 설치됨 ($("$2" --version 2>&1 | head -n1))"
  else ng "$1 없음 (command: $2)"; fi
}

# 공통 헬퍼 -----------------------------------------------------
_container_up() { docker ps --format '{{.Names}}' 2>/dev/null | grep -qi "$1"; }
_http_code()    { curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$1" 2>/dev/null || echo 000; }
# HTTP 판정: 000=무응답(WARN). strict=1 이면 200만 PASS, 아니면 <500 을 PASS.
# (기존 '!= 000' 방식은 502/500 도 PASS 로 처리해 pytest(<500,==200)와 어긋났음)
_http_report() {  # $1=라벨  $2=URL  [$3=strict]
  local c; c=$(_http_code "$2")
  if [ "$c" = 000 ]; then warn "$1 무응답"; return; fi
  if [ "${3:-0}" = 1 ]; then
    [ "$c" = 200 ] && ok "$1 HTTP $c" || ng "$1 HTTP $c (200 아님)"
  else
    [ "$c" -lt 500 ] && ok "$1 HTTP $c" || ng "$1 HTTP $c (5xx)"
  fi
}

# --- 모듈: base (구축 3장 후) ----------------------------------
check_base() {
  section "[base] OS / 개발도구 / Python"
  [ -f /etc/os-release ] && ok "OS: $(. /etc/os-release; echo "$PRETTY_NAME")" || ng "/etc/os-release 없음"
  uname -r | grep -qiE 'microsoft|wsl' && ok "WSL 커널: $(uname -r)" \
    || warn "WSL 시그니처 미검출 ($(uname -r))"
  check_cmd git git;  check_cmd curl curl;  check_cmd wget wget
  check_cmd make make; check_cmd gcc gcc
  check_cmd python3 python3; check_cmd pip3 pip3
}

# --- 모듈: ssh (구축 5장 후) -----------------------------------
check_ssh() {
  section "[ssh] SSH 서버"
  if pgrep -x sshd >/dev/null 2>&1; then ok "sshd 프로세스 실행 중"
  elif systemctl is-active ssh >/dev/null 2>&1; then ok "ssh 서비스 active (systemd)"
  else ng "sshd 미실행 — 'sudo service ssh start' 또는 systemd 활성화"; fi
  ss -tlnp 2>/dev/null | grep -q ':22 ' && ok "22번 포트 LISTEN" || warn "22번 포트 미검출"
}

# --- 모듈: github (구축 7장 후) --------------------------------
check_github() {
  section "[github] GitHub SSH 인증 (계정별)"
  for host in github.com-coteleafdev github.com-skygoldlee github.com; do
    out=$(ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8 -T "git@$host" 2>&1 || true)
    if echo "$out" | grep -qi "successfully authenticated"; then
      who=$(echo "$out" | grep -oiE "Hi [^!]+" | head -n1)
      ok "$host 인증 성공 (${who:-계정확인})"
    else warn "$host 인증 실패/미설정 — ~/.ssh/config alias 확인"; fi
  done
}

# --- 모듈: docker (구축 8장 후) --------------------------------
check_docker() {
  section "[docker] Docker 엔진"
  if command -v docker >/dev/null 2>&1; then
    ok "docker 설치됨 ($(docker --version))"
    docker info >/dev/null 2>&1 && ok "docker 데몬 정상" \
      || ng "docker 데몬 무응답 — Docker Desktop의 WSL 연동 확인"
    docker compose version >/dev/null 2>&1 && ok "docker compose 사용 가능" \
      || warn "docker compose 플러그인 미검출"
  else ng "docker 없음"; fi
}

# --- 모듈: nginx (구축 9장 후) ---------------------------------
check_nginx() {
  section "[nginx] Nginx"
  _container_up nginx && ok "nginx 컨테이너 실행 중" || warn "nginx 컨테이너 미검출 (명명 규칙 다르면 무시)"
  _http_report "Nginx(80)" http://localhost:80
}

# --- 모듈: fastapi (구축 9장 후) -------------------------------
check_fastapi() {
  section "[fastapi] FastAPI"
  _container_up fastapi && ok "fastapi 컨테이너 실행 중" || warn "fastapi 컨테이너 미검출"
  _http_report "FastAPI(8000/docs)" http://localhost:8000/docs 1
}

# --- 모듈: postgres (구축 9장 후) ------------------------------
check_postgres() {
  section "[postgres] PostgreSQL"
  _container_up postgres && ok "postgres 컨테이너 실행 중" || warn "postgres 컨테이너 미검출"
  if command -v pg_isready >/dev/null 2>&1; then
    pg_isready -h localhost -p 5432 >/dev/null 2>&1 && ok "PostgreSQL(5432) 정상" || warn "PostgreSQL(5432) 무응답"
  elif (echo > /dev/tcp/localhost/5432) >/dev/null 2>&1; then ok "PostgreSQL(5432) 포트 오픈"
  else warn "PostgreSQL(5432) 확인 불가 (pg_isready 미설치 & 포트 닫힘)"; fi
}

# --- 모듈: hardening (하드닝 9-3-1·20 · v3 컨테이너 하드닝 후) ----
# 서버측에서 검증 가능한 하드닝만 확인합니다.
# 외부 실차단(다른 PC→서버)은 로컬에서 verify_client.ps1 -Check ports 로 확인하세요.
check_hardening() {
  section "[hardening] SSH·포트 노출·컨테이너 하드닝"

  # 1) sshd 실제 적용값 (편집만 하고 reload 안 한 경우를 잡음)
  if command -v sshd >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    local sshd_out; sshd_out=$(sudo sshd -T 2>/dev/null)
    if [ -n "$sshd_out" ]; then
      echo "$sshd_out" | grep -qi '^passwordauthentication no' \
        && ok "SSH 비밀번호 로그인 차단(passwordauthentication no)" \
        || ng "passwordauthentication 이 no 아님 — 편집 후 reload 확인(5-3·6-4)"
      echo "$sshd_out" | grep -qi '^permitrootlogin no' \
        && ok "root 로그인 차단(permitrootlogin no)" \
        || warn "permitrootlogin 이 no 아님(정책 확인)"
      local mat; mat=$(echo "$sshd_out" | awk '/^maxauthtries/{print $2}')
      if [ -n "${mat:-}" ] && [ "$mat" -le 4 ] 2>/dev/null; then ok "MaxAuthTries=$mat (<=4)"
      else warn "MaxAuthTries=${mat:-미설정} (권장 <=4)"; fi
    else warn "sshd -T 출력 없음(권한/패키지 확인)"; fi
  else warn "sshd -T 확인 스킵(sudo 무권한 또는 sshd 없음)"; fi

  # 2) fail2ban (WSL NAT에선 의도적 미사용일 수 있음 → WARN)
  if systemctl is-active fail2ban >/dev/null 2>&1; then ok "fail2ban active"
  elif command -v fail2ban-client >/dev/null 2>&1; then warn "fail2ban 설치됨·비활성(WSL NAT면 의도적일 수 있음, v2 §6)"
  else warn "fail2ban 미설치(WSL NAT면 Windows 방화벽으로 대체)"; fi

  if ! command -v docker >/dev/null 2>&1; then warn "docker 없음 → 포트·컨테이너 검사 스킵"; return; fi

  # 3) 민감 포트가 0.0.0.0 으로 발행됐는지 (ufw 우회 함정의 서버측 탐지: 20-2·9-3-1)
  local ports exposed=0 p; ports=$(docker ps --format '{{.Ports}}' 2>/dev/null)
  for p in 5432 8000 8080 3001; do
    if echo "$ports" | grep -qE "0\.0\.0\.0:${p}->|(\[::\]|:::):${p}->"; then
      ng "포트 ${p} 가 0.0.0.0 로 노출 → 127.0.0.1 바인딩/보안그룹 필요(9-3-1·20-2)"; exposed=1
    fi
  done
  [ "$exposed" -eq 0 ] && ok "민감 포트(5432/8000/8080/3001) 0.0.0.0 발행 없음"
  echo "     ↳ 외부 실차단은 다른 PC에서: verify_client.ps1 -Check ports  (또는 nc -vz <서버> 5432 8080 3001 → 실패=정상)"

  # 4) 컨테이너 하드닝: no-new-privileges·mem 상한·비루트
  local names n secopt mem usr flags hardened=0 total=0
  names=$(docker ps --format '{{.Names}}' 2>/dev/null)
  for n in $names; do
    total=$((total+1)); flags=""
    secopt=$(docker inspect "$n" --format '{{join .HostConfig.SecurityOpt ","}}' 2>/dev/null)
    mem=$(docker inspect "$n" --format '{{.HostConfig.Memory}}' 2>/dev/null)
    usr=$(docker inspect "$n" --format '{{.Config.User}}' 2>/dev/null)
    echo "$secopt" | grep -q 'no-new-privileges' && { flags="${flags}nnp "; hardened=$((hardened+1)); }
    { [ -n "${mem:-}" ] && [ "$mem" != 0 ]; } 2>/dev/null && flags="${flags}mem"
    { [ -n "${usr:-}" ] && [ "$usr" != 0 ] && [ "$usr" != root ]; } && flags="${flags} nonroot"
    if echo "$flags" | grep -q nnp; then ok "컨테이너 $n: ${flags}"; else warn "컨테이너 $n: no-new-privileges 미검출(${flags:-none})"; fi
  done
  if [ "$total" -gt 0 ] && [ "$hardened" -eq 0 ]; then ng "실행 중 컨테이너 no-new-privileges 적용 0건 → 컨테이너 하드닝 미반영(9-4)"; fi
}

usage() {
  cat <<EOF
사용법: $0 [모듈]

  base      OS/WSL·개발도구·Python     (기본 설정 완료 후)
  ssh       SSH 서버                    (SSH 설정 완료 후)
  github    GitHub SSH 인증(계정별)     (GitHub 연결 완료 후)
  docker    Docker 엔진·Compose        (Docker 설치 완료 후)
  nginx     Nginx 컨테이너·응답         (Nginx 구성 완료 후)
  fastapi   FastAPI 컨테이너·응답       (FastAPI 구성 완료 후)
  postgres  PostgreSQL                  (PostgreSQL 구성 완료 후)
  services  nginx + fastapi + postgres 묶음
  hardening SSH·포트 노출·컨테이너 하드닝 (하드닝 9-3-1·20·v3 적용 후)
  all       전체 (기본값)
EOF
}

main() {
  local t="${1:-all}"
  echo "============================================================"
  echo " 서버 검증 [$t] : $(date '+%Y-%m-%d %H:%M:%S')"
  echo "============================================================"
  case "$t" in
    base)     check_base ;;
    ssh)      check_ssh ;;
    github)   check_github ;;
    docker)   check_docker ;;
    nginx)    check_nginx ;;
    fastapi)  check_fastapi ;;
    postgres) check_postgres ;;
    services) check_nginx; check_fastapi; check_postgres ;;
    hardening) check_hardening ;;
    all)      check_base; check_ssh; check_github; check_docker; check_nginx; check_fastapi; check_postgres ;;
    -h|--help|help) usage; exit 0 ;;
    *) echo "알 수 없는 모듈: '$t'"; echo; usage; exit 2 ;;
  esac
  echo -e "\n============================================================"
  echo -e " 결과 [$t]:  ${GREEN}PASS ${PASS}${NC} / ${RED}FAIL ${FAIL}${NC} / ${YELLOW}WARN ${WARN}${NC}"
  echo    "============================================================"
  [ "$FAIL" -eq 0 ] && exit 0 || exit 1
}

main "$@"
