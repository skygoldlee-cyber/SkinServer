# =============================================================
# wsl-backup-task.ps1 — Windows 작업 스케줄러용 백업 트리거 (가이드 18-2-1장)
#
# 목적: WSL 이 idle 로 종료돼 있어도, Windows 가 정해진 시각에 WSL 을
#       깨워(docker 준비 대기 후) pg_backup.sh 를 실행하게 한다.
#       → WSL 안 cron 의 "예약 시각에 배포판이 꺼져 있어 백업 누락" 문제 해결.
#
# 등록(관리자 PowerShell, 매일 03:00):
#   schtasks /Create /TN "WSL PG Backup" `
#     /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\ops\wsl-backup-task.ps1" `
#     /SC DAILY /ST 03:00 /RL HIGHEST /F
#
# 확인: 실행 후 WSL 에서  tail ~/backups/backup.log
# =============================================================

$ErrorActionPreference = "Stop"
$distro = "Ubuntu-24.04"     # wsl -l -v 의 NAME 과 일치시킬 것
$user   = "coteleaf"         # 백업 스크립트를 소유한 계정
$script = "~/scripts/pg_backup.sh"
$log    = "~/backups/backup.log"

# 1) 배포판을 깨우고 docker/컨테이너가 준비될 때까지 최대 60초 대기
#    (Docker Desktop 자동시작과의 경합으로 docker 가 잠깐 무응답일 수 있음)
wsl -d $distro -e sh -c "for i in `$(seq 1 30); do docker ps >/dev/null 2>&1 && break; sleep 2; done"

# 2) 로그인 셸(-lc)로 실행해 PATH·docker 컨텍스트를 정상 로드
wsl -d $distro -u $user -e bash -lc "mkdir -p ~/backups; $script >> $log 2>&1"
if ($LASTEXITCODE -ne 0) {
    Write-Error "WSL 백업 실패(exit=$LASTEXITCODE). WSL 에서 $log 확인."
    exit 1
}
Write-Host "WSL 백업 트리거 완료 ($distro). 로그: WSL:$log"
