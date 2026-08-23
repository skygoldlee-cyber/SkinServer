# =============================================================
# verify_client.ps1  (모듈형)
# 로컬 Windows PC → 원격 Ubuntu(WSL2) 서버 연결 검증
#   -Check 로 항목별 부분 실행 가능
#
# 사용법:
#   # 전체 (LAN/WSL2 검증 환경 기본값)
#   powershell -ExecutionPolicy Bypass -File .\verify_client.ps1 -RemoteHost 192.168.0.50 -SshUser coteleaf
#   # SSH 접속만 (로컬 SSH 접속 설정 직후)
#   .\verify_client.ps1 -RemoteHost 192.168.0.50 -SshUser coteleaf -Check ssh
#   # HTTP 응답만 (외부 접속 구성 직후)
#   .\verify_client.ps1 -RemoteHost 192.168.0.50 -Check http
#
#   # 이관 후(외부 호스팅·HTTPS) 서버 검증: -Mode prod
#   #   → 22/80/443 만 확인하고 HTTPS(https://도메인) 로 응답을 봅니다.
#   #     8000(API)·5432(DB)는 방화벽으로 외부 차단이 '정상'이라 검사하지 않습니다.
#   .\verify_client.ps1 -RemoteHost your.domain.com -SshUser ubuntu -Mode prod
#
# -Mode:
#   lan  (기본) : WSL2/LAN 검증 환경. 22/80/8000 포트, 평문 HTTP 로 확인.
#   prod        : 외부 호스팅+HTTPS. 22/80/443 포트, https 로 확인(런북 §7 포트정책과 일치).
#
# 주의: 서버가 원격 PC의 WSL2 안에 있으면(lan), 원격 Windows 호스트에서
#       netsh portproxy 로 포트를 WSL2 로 포워딩해 두어야 통과함 (문서 10-2).
# =============================================================

param(
  [Parameter(Mandatory=$true)][string]$RemoteHost,
  [string]$SshUser  = "ubuntu",
  [int]$SshPort     = 22,
  [int]$HttpPort    = 80,
  [int]$HttpsPort   = 443,
  [int]$ApiPort     = 8000,
  [ValidateSet("lan","prod")][string]$Mode = "lan",
  [ValidateSet("all","ping","ports","ssh","http")][string]$Check = "all"
)

# Windows PowerShell 5.1 은 기본 TLS 가 낮아 Let's Encrypt(HTTPS) 연결이 실패할 수 있음 → TLS1.2 강제
try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch {}

$script:pass = 0; $script:fail = 0; $script:warn = 0
function Ok($m){ Write-Host "  [PASS] $m" -ForegroundColor Green;  $script:pass++ }
function Ng($m){ Write-Host "  [FAIL] $m" -ForegroundColor Red;    $script:fail++ }
function Wn($m){ Write-Host "  [WARN] $m" -ForegroundColor Yellow; $script:warn++ }

# --- 모듈: ping ------------------------------------------------
function Test-Ping {
  Write-Host "`n== [ping] 네트워크 도달성 =="
  if (Test-Connection -ComputerName $RemoteHost -Count 2 -Quiet) { Ok "$RemoteHost ping 응답 정상" }
  else { Wn "$RemoteHost ping 무응답 (ICMP 차단 가능 — 포트로 확인)" }
}

# --- 모듈: ports (구축 6·10장 후) ------------------------------
function Test-Ports {
  Write-Host "`n== [ports] 포트 연결 (mode=$Mode) =="
  if ($Mode -eq "prod") {
    # 이관 후: 8000(API)/5432(DB)는 외부 차단이 정상(런북 §7-1). 22/80/443 만 확인.
    $targets = @(@{n="SSH";port=$SshPort}, @{n="HTTP(→HTTPS 리다이렉트)";port=$HttpPort}, @{n="HTTPS";port=$HttpsPort})
  } else {
    $targets = @(@{n="SSH";port=$SshPort}, @{n="HTTP(Nginx)";port=$HttpPort}, @{n="API(FastAPI)";port=$ApiPort})
  }
  foreach ($p in $targets) {
    $r = Test-NetConnection -ComputerName $RemoteHost -Port $p.port -WarningAction SilentlyContinue
    if ($r.TcpTestSucceeded) { Ok "$($p.n) 포트 $($p.port) 열림" } else { Ng "$($p.n) 포트 $($p.port) 닫힘/차단" }
  }
}

# --- 모듈: ssh (구축 6장 후) -----------------------------------
function Test-Ssh {
  Write-Host "`n== [ssh] SSH 접속 =="
  $t = "$SshUser@$RemoteHost"
  $o = ssh -p $SshPort -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new $t "echo OK; uname -a" 2>&1
  if ($o -match "OK") { Ok "SSH 키 인증 성공 ($t)"; Write-Host "        $(( $o | Select-Object -Last 1 ))" }
  else { Ng "SSH 접속 실패: $o" }
}

# --- 모듈: http (구축 10장 후) ---------------------------------
function Test-Http {
  Write-Host "`n== [http] HTTP 서비스 응답 (mode=$Mode) =="
  if ($Mode -eq "prod") {
    # HTTPS 도메인 기준. http:// 는 →https 리다이렉트를 따라가 200 이면 정상. 8000 은 외부 차단이라 확인 안 함.
    $urls = @("https://${RemoteHost}", "http://${RemoteHost}")
  } else {
    $urls = @("http://${RemoteHost}:${HttpPort}", "http://${RemoteHost}:${ApiPort}/docs")
  }
  foreach ($u in $urls) {
    try { $r = Invoke-WebRequest -Uri $u -TimeoutSec 8 -UseBasicParsing; Ok "$u -> HTTP $($r.StatusCode)" }
    catch {
      $sc = $_.Exception.Response.StatusCode.value__
      if ($sc) { Ok "$u -> HTTP $sc (응답 있음)" } else { Wn "$u -> 무응답 ($($_.Exception.Message))" }
    }
  }
}

Write-Host "============================================================"
Write-Host " 원격 서버 검증 [$Check / mode=$Mode]: $RemoteHost  ($(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))"
Write-Host "============================================================"

switch ($Check) {
  "ping"  { Test-Ping }
  "ports" { Test-Ports }
  "ssh"   { Test-Ssh }
  "http"  { Test-Http }
  "all"   { Test-Ping; Test-Ports; Test-Ssh; Test-Http }
}

Write-Host "`n============================================================"
Write-Host " 결과 [$Check]: PASS $script:pass / FAIL $script:fail / WARN $script:warn"
Write-Host "============================================================"
if ($script:fail -eq 0) { exit 0 } else { exit 1 }
