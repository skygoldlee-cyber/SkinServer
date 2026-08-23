#requires -Version 5.1
<#
.SYNOPSIS
  remote.ps1 — 외부 Windows 에서 리눅스 서버를 모니터링·제어하는 통합 CLI.

.DESCRIPTION
  서버(리눅스)에서 돌고 있는 SkinLens 스택을 SSH 로 원격 운영한다.
  모니터링(읽기) 동사와 제어(쓰기) 동사를 구분하고, prod 제어에는 확인을 요구한다.

  접속 대상은 다음 우선순위로 결정된다.
    1) -Target "user@host" / -SshHost -SshUser 명시 인자
    2) deploy\env\remote.env 파일 (RemoteTarget=...)
    3) 환경변수 SL_REMOTE_TARGET
    4) ~/.ssh/config 의 Host 별칭 (-Target myserver)

  서버 측에는 이 리포가 체크아웃돼 있어야 하며, 그 위치를 RemoteDir 로 지정한다
  (기본 ~/SkinServer). remote-status.sh 가 서버측 상태 에이전트다.

.EXAMPLE
  .\remote.ps1 status                      # 한 번에 서버 상태 스냅샷
  .\remote.ps1 status -Watch               # 5초마다 갱신 (Ctrl+C 종료)
  .\remote.ps1 ps                          # 컨테이너 목록
  .\remote.ps1 logs gateway                # 게이트웨이 로그 팔로우
  .\remote.ps1 up prod                     # prod 스택 기동
  .\remote.ps1 restart worker              # 워커 재시작
  .\remote.ps1 deploy gateway ghcr.io/me/sl_gateway:abc123 -Env prod -Pull
  .\remote.ps1 doctor prod                 # 원격 자가진단
  .\remote.ps1 tunnel 8080                 # 관리콘솔 SSH 터널 (localhost:8080)
  .\remote.ps1 exec "docker stats --no-stream"
#>
[CmdletBinding()]
param(
  [Parameter(Position=0)] [string]$Command,
  [Parameter(Position=1)] [string]$Arg1,
  [Parameter(Position=2)] [string]$Arg2,

  # 접속 대상
  [string]$Target,                 # "user@host" 또는 ~/.ssh/config Host 별칭
  [string]$SshHost,
  [string]$SshUser = "ubuntu",
  [int]$SshPort = 22,
  [string]$IdentityFile,           # 키 파일 경로 (기본: ssh 기본 규칙)

  # 서버측 경로
  [string]$RemoteDir = "~/SkinServer",

  # 동사 옵션
  [string]$Env = "prod",           # up/down/ps/logs/restart/doctor 기본 환경
  [switch]$Watch,                  # status 갱신 모드
  [int]$IntervalSec = 5,           # watch 갱신 주기
  [switch]$Pull,                   # deploy 시 이미지 pull
  [switch]$Yes,                    # prod 확인 프롬프트 생략 (자동화용)

  [Parameter(ValueFromRemainingArguments=$true)] [string[]]$Rest
)

$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $Here '..\..')
$EnvDir = Join-Path $Root 'deploy\env'
$RemoteEnvFile = Join-Path $EnvDir 'remote.env'

function Write-Ok   ($m) { Write-Host "✓ $m" -ForegroundColor Green }
function Write-Warn ($m) { Write-Host "! $m" -ForegroundColor Yellow }
function Write-Fail ($m) { Write-Host "✗ $m" -ForegroundColor Red }
function Write-Info ($m) { Write-Host "· $m" -ForegroundColor DarkGray }
function Die ($m) { Write-Fail $m; exit 1 }

# ---- 접속 대상 해석 ---------------------------------------------------------
function Get-RemoteConfig {
  # remote.env (KEY=VALUE) 를 읽어 해시로 반환. 없으면 빈 해시.
  $cfg = @{}
  if (Test-Path $RemoteEnvFile) {
    foreach ($line in Get-Content $RemoteEnvFile) {
      $t = $line.Trim()
      if ($t -eq '' -or $t.StartsWith('#')) { continue }
      $i = $t.IndexOf('=')
      if ($i -lt 1) { continue }
      $cfg[$t.Substring(0,$i).Trim()] = $t.Substring($i+1).Trim()
    }
  }
  return $cfg
}

$cfg = Get-RemoteConfig

# Target 우선순위: 인자 > remote.env > 환경변수 > (SshHost/SshUser 조합)
if (-not $Target) { $Target = $cfg['RemoteTarget'] }
if (-not $Target) { $Target = $env:SL_REMOTE_TARGET }
if (-not $Target -and $SshHost) { $Target = "$SshUser@$SshHost" }
if ($cfg['RemoteDir'] -and -not $PSBoundParameters.ContainsKey('RemoteDir')) { $RemoteDir = $cfg['RemoteDir'] }
if ($cfg['SshPort'] -and -not $PSBoundParameters.ContainsKey('SshPort')) { $SshPort = [int]$cfg['SshPort'] }
if ($cfg['IdentityFile'] -and -not $IdentityFile) { $IdentityFile = $cfg['IdentityFile'] }

# ---- ssh 베이스 인자 ---------------------------------------------------------
function Get-SshArgs {
  $a = @()
  if ($SshPort -ne 22) { $a += @('-p', "$SshPort") }
  if ($IdentityFile)   { $a += @('-i', $IdentityFile) }
  # 연결 실패를 빨리 드러내고, 배너 지연을 줄인다.
  $a += @('-o','BatchMode=yes','-o','ConnectTimeout=10','-o','StrictHostKeyChecking=accept-new')
  return ,$a
}

function Test-TargetOrDie {
  if (-not $Target) {
    Write-Fail "접속 대상이 없습니다. 다음 중 하나로 지정하세요:"
    Write-Host "  1) .\remote.ps1 $Command -Target user@host"
    Write-Host "  2) $RemoteEnvFile 에 RemoteTarget=user@host"
    Write-Host "  3) `$env:SL_REMOTE_TARGET = 'user@host'"
    Write-Host "  4) ~/.ssh/config 에 Host 별칭 후 -Target 별칭"
    exit 2
  }
}

# 원격에서 bash 로 명령 실행. 실패 시 ssh 종료코드 전파.
# -Tty: 로그 팔로우 등 인터랙티브 스트림에 의사터미널 할당 (Ctrl+C/색상 정상화).
function Invoke-Remote([string]$BashLine, [switch]$Tty) {
  Test-TargetOrDie
  $sshArgs = Get-SshArgs
  if ($Tty) { $sshArgs += '-t' }
  & ssh @sshArgs $Target $BashLine
  return $LASTEXITCODE
}

# 서버측 스크립트 경로
$SlBin      = "$RemoteDir/deploy/scripts/sl"
$StatusBin  = "$RemoteDir/deploy/ops/remote-status.sh"
$DeployBin  = "$RemoteDir/deploy/scripts/deploy.sh"

function Show-Usage {
  Write-Host @'
remote.ps1 — Windows → Linux 서버 모니터링·제어

모니터링 (읽기):
  status [-Watch] [-IntervalSec N]   서버 상태 스냅샷 (단일 SSH 왕복)
  ps                                 컨테이너 목록
  logs [service]                     로그 팔로우 (생략 시 전체)
  health                             엔드포인트 헬스만 빠르게
  doctor [env]                       원격 자가진단

제어 (쓰기 — prod 는 확인):
  up [env]                           스택 기동
  down [env]                         스택 정지
  restart <service> [env]            서비스 재시작
  deploy <service> <image> [-Env X] [-Pull]
                                     개별 서비스 배포(자동 롤백)

유틸:
  tunnel <port> [remoteport]         SSH 로컬 포워딩 (관리콘솔/DB)
  exec "<bash 명령>"                 서버에서 임의 bash 한 줄 실행
  config                             현재 접속 설정 표시
  test-ssh                           SSH 연결만 확인

접속 대상: -Target user@host | deploy\env\remote.env | $env:SL_REMOTE_TARGET | ~/.ssh/config 별칭
'@
}

if (-not $Command -or $Command -in '-h','--help','help') { Show-Usage; exit 0 }

# ---- 동사 -------------------------------------------------------------------
switch ($Command.ToLower()) {

  'config' {
    Write-Host "== remote 설정 =="
    Write-Host ("  Target       : {0}" -f ($(if ($Target) {$Target} else {'(미설정)'})))
    Write-Host ("  SshPort      : {0}" -f $SshPort)
    Write-Host ("  IdentityFile : {0}" -f ($(if ($IdentityFile) {$IdentityFile} else {'(기본)'})))
    Write-Host ("  RemoteDir    : {0}" -f $RemoteDir)
    Write-Host ("  remote.env   : {0}" -f ($(if (Test-Path $RemoteEnvFile) {$RemoteEnvFile} else {'(없음)'})))
    exit 0
  }

  'test-ssh' {
    Test-TargetOrDie
    Write-Info "ssh 연결 확인: $Target"
    $rc = Invoke-Remote "echo connected: \$(hostname)"
    if ($rc -eq 0) { Write-Ok "SSH 연결 정상" } else { Die "SSH 연결 실패 (exit $rc)" }
    exit 0
  }

  'status' {
    $cmd = "bash $StatusBin $Env"
    if ($Watch) {
      Test-TargetOrDie
      Write-Info "상태 갱신 모드 (${IntervalSec}s, Ctrl+C 종료) — $Target"
      while ($true) {
        Clear-Host
        Write-Host "SkinLens 원격 상태 — $Target — $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Cyan
        Invoke-Remote $cmd | Out-Null
        Start-Sleep -Seconds $IntervalSec
      }
    } else {
      $rc = Invoke-Remote $cmd
      exit $rc
    }
  }

  'health' {
    # 상태 스냅샷에서 엔드포인트/헬스만 빠르게 — JSON 으로 받아 종료코드 활용
    $rc = Invoke-Remote "bash $StatusBin $Env --json"
    if ($rc -eq 0) { Write-Ok "엔드포인트 정상" } else { Die "엔드포인트 이상 (자세히: .\remote.ps1 status)" }
    exit 0
  }

  'ps' {
    $rc = Invoke-Remote "bash $SlBin ps $Env"
    exit $rc
  }

  'logs' {
    $svc = $Arg1
    $line = "bash $SlBin logs $Env"
    if ($svc) { $line += " $svc" }
    # 로그 팔로우(-f)는 인터랙티브 스트림 — TTY 할당해 Ctrl+C·색상 정상화
    $rc = Invoke-Remote $line -Tty
    exit $rc
  }

  'doctor' {
    $e = if ($Arg1) { $Arg1 } else { $Env }
    $rc = Invoke-Remote "bash $SlBin doctor $e"
    exit $rc
  }

  'up' {
    $e = if ($Arg1) { $Arg1 } else { $Env }
    if ($e -eq 'prod' -and -not $Yes) {
      $yn = Read-Host "원격 prod 스택을 기동할까요? [yes/N]"
      if ($yn -ne 'yes') { Die "취소됨" }
    }
    Write-Info "원격 기동: $e"
    $rc = Invoke-Remote "bash $SlBin up $e"
    if ($rc -eq 0) { Write-Ok "up ($e) 완료" } else { Die "up 실패 (exit $rc)" }
    exit 0
  }

  'down' {
    $e = if ($Arg1) { $Arg1 } else { $Env }
    if ($e -eq 'prod' -and -not $Yes) {
      $yn = Read-Host "원격 prod 스택을 내릴까요? [yes/N]"
      if ($yn -ne 'yes') { Die "취소됨" }
    }
    Write-Info "원격 정지: $e"
    $rc = Invoke-Remote "bash $SlBin down $e"
    if ($rc -eq 0) { Write-Ok "down ($e) 완료" } else { Die "down 실패 (exit $rc)" }
    exit 0
  }

  'restart' {
    $svc = $Arg1
    if (-not $svc) { Die 'usage: .\remote.ps1 restart <service> [env]' }
    $e = if ($Arg2) { $Arg2 } else { $Env }
    if ($e -eq 'prod' -and -not $Yes) {
      $yn = Read-Host "원격 prod 의 $svc 를 재시작할까요? [yes/N]"
      if ($yn -ne 'yes') { Die "취소됨" }
    }
    Write-Info "원격 재시작: $svc ($e)"
    # compose 파일 조합은 서버측 sl 이 알고 있으므로, 재시작도 sl 을 경유해 일관성 유지.
    # (sl 에 restart 가 없으므로 up -d --force-recreate 대신 compose restart 를 bash 로 직접 호출)
    $remoteCmd = 'cd "{0}/deploy" && docker compose --env-file env/.env restart {1}' -f $RemoteDir, $svc
    $rc = Invoke-Remote $remoteCmd
    if ($rc -eq 0) { Write-Ok "$svc 재시작 완료" } else { Die "재시작 실패 (exit $rc)" }
    exit 0
  }

  'deploy' {
    $svc = $Arg1; $img = $Arg2
    if (-not $svc -or -not $img) { Die 'usage: .\remote.ps1 deploy <service> <image> [-Env staging|prod] [-Pull]' }
    $pull = if ($Pull) { '--pull' } else { '' }
    if ($Env -eq 'prod' -and -not $Yes) {
      $yn = Read-Host "원격 prod 에 $svc ← $img 배포할까요? [yes/N]"
      if ($yn -ne 'yes') { Die "취소됨" }
    }
    Write-Info "원격 배포: $svc ← $img ($Env)"
    $rc = Invoke-Remote "bash $DeployBin --service $svc --image $img --env $Env $pull"
    if ($rc -eq 0) { Write-Ok "배포 완료: $svc = $img" } else { Die "배포 실패/롤백 (exit $rc)" }
    exit 0
  }

  'tunnel' {
    $port = $Arg1
    if (-not $port) { Die 'usage: .\remote.ps1 tunnel <localport> [remoteport]' }
    $rport = if ($Arg2) { $Arg2 } else { $port }
    Test-TargetOrDie
    Write-Ok "SSH 터널: localhost:$port → $Target`:$rport  (Ctrl+C 종료)"
    Write-Info "브라우저에서 http://localhost:$port 접속"
    $sshArgs = Get-SshArgs
    $sshArgs += @('-N','-L', "${port}:localhost:${rport}")
    & ssh @sshArgs $Target
    exit $LASTEXITCODE
  }

  'exec' {
    $line = $Arg1
    if (-not $line) { Die 'usage: .\remote.ps1 exec "<bash 명령>"' }
    $rc = Invoke-Remote $line
    exit $rc
  }

  default {
    Write-Fail "unknown command: $Command"
    Show-Usage
    exit 2
  }
}
