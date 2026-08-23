# =============================================================
# sl.ps1 — SkinLens 통합 기동 CLI (Windows PowerShell)
#
#   bash판 deploy/scripts/sl 과 같은 동사를 제공한다.
#   WSL 없이 네이티브 Windows + Docker Desktop 환경에서 사용.
#
# 사용:
#   .\sl.ps1 up dev | .\sl.ps1 up staging | .\sl.ps1 up prod
#   .\sl.ps1 down <env>
#   .\sl.ps1 logs <env> [service]
#   .\sl.ps1 ps <env>
#   .\sl.ps1 doctor <env>
#   .\sl.ps1 init <env>
#   .\sl.ps1 deploy <service> <image> [--env staging|prod] [--pull]
#
# env 생략 시: 실행 중인 컨테이너로 추론하고, 못 하면 묻는다.
# =============================================================
[CmdletBinding()]
param(
    [Parameter(Position=0)] [string]$Command,
    [Parameter(Position=1)] [string]$Env,
    [Parameter(Position=2)] [string]$Arg2,
    [Parameter(ValueFromRemainingArguments=$true)] [string[]]$Rest
)

$ErrorActionPreference = 'Stop'
$Here       = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root       = Resolve-Path (Join-Path $Here '..\..')
$ComposeDir = Join-Path $Root 'deploy\compose'
$EnvDir     = Join-Path $Root 'deploy\env'

function Write-Ok   ($m) { Write-Host "✓ $m" -ForegroundColor Green }
function Write-Warn ($m) { Write-Host "! $m" -ForegroundColor Yellow }
function Write-Fail ($m) { Write-Host "✗ $m" -ForegroundColor Red }
function Write-Info ($m) { Write-Host "· $m" -ForegroundColor DarkGray }
function Die ($m) { Write-Fail $m; exit 1 }

# ---- compose 조합 -----------------------------------------------------------
function Build-ComposeArgs([string]$e) {
    $args = @('--env-file', (Join-Path $EnvDir '.env'),
              '-f', (Join-Path $ComposeDir 'compose.base.yml'))
    switch ($e) {
        'dev' {
            $args += @('-f', (Join-Path $ComposeDir 'compose.dev.yml'))
        }
        'staging' {
            if (-not (Test-Path (Join-Path $EnvDir '.env.images'))) {
                Die "missing deploy\env\.env.images — '.\sl.ps1 init staging' 또는 예시 복사"
            }
            $args += @('--env-file', (Join-Path $EnvDir '.env.images'),
                       '-f', (Join-Path $ComposeDir 'compose.staging.yml'))
        }
        { $_ -in 'prod','production' } {
            if (-not (Test-Path (Join-Path $EnvDir '.env.images'))) {
                Die "missing deploy\env\.env.images — '.\sl.ps1 init prod' 또는 예시 복사"
            }
            $args += @('--env-file', (Join-Path $EnvDir '.env.images'),
                       '-f', (Join-Path $ComposeDir 'compose.prod.yml'))
            $tls = Join-Path $ComposeDir 'compose.tls.yml'
            if (Test-Path $tls) { $args += @('-f', $tls) }
        }
        default { Die "unknown env: $e (dev|staging|prod)" }
    }
    $gpu = Join-Path $ComposeDir 'compose.gpu.yml'
    if (Test-Path $gpu) { $args += @('-f', $gpu) }
    return ,$args
}

# ---- 환경 추론 --------------------------------------------------------------
function Infer-Env {
    $cid = (docker ps -q --filter name=sl_gateway 2>$null | Select-Object -First 1)
    if ($cid) {
        $envLines = docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' $cid 2>$null
        if ($envLines -match '^ENV=prod')    { return 'prod' }
        if ($envLines -match '^ENV=staging') { return 'staging' }
        if ($envLines -match '^DEV_DEBUG=1') { return 'dev' }
        return 'dev'
    }
    return $null
}

function Require-Env([string]$e) {
    if ($e) {
        if ($e -notin 'dev','staging','prod','production') { Die "unknown env: $e (dev|staging|prod)" }
        if ($e -eq 'production') { return 'prod' }
        return $e
    }
    $inferred = Infer-Env
    if ($inferred) { Write-Info "env 추론: $inferred (실행 중인 컨테이너 기준)"; return $inferred }
    $pick = Read-Host "환경을 고르세요 (dev/staging/prod)"
    if ($pick -in 'dev','staging','prod') { return $pick }
    Die "env 를 지정하세요: .\sl.ps1 $Command <dev|staging|prod>"
}

# ---- doctor -----------------------------------------------------------------
$script:DoctorFail = $false
function Chk-Ok   ($m)        { Write-Ok $m }
function Chk-Warn ($m, $fix)  { Write-Warn $m; if ($fix) { Write-Info "  → $fix" } }
function Chk-Fail ($m, $fix)  { $script:DoctorFail = $true; Write-Fail $m; if ($fix) { Write-Host "  → 고치는 법: $fix" -ForegroundColor Yellow } }

function Get-EnvValue([string]$key) {
    $envFile = Join-Path $EnvDir '.env'
    if (-not (Test-Path $envFile)) { return '' }
    $line = Select-String -Path $envFile -Pattern "^$key=" | Select-Object -First 1
    if ($line) { return ($line.Line -split '=', 2)[1] }
    return ''
}

function Invoke-Doctor([string]$e) {
    Write-Host "== sl doctor ($e) =="

    # 1) docker / compose v2
    if (Get-Command docker -ErrorAction SilentlyContinue) { Chk-Ok "docker 설치됨" } else { Chk-Fail "docker 없음" "https://docs.docker.com/get-docker/" }
    try { docker compose version | Out-Null; Chk-Ok "compose v2 사용 가능" } catch { Chk-Fail "compose v2 없음" "Docker Desktop 최신화" }

    # 2) .env 존재
    if (Test-Path (Join-Path $EnvDir '.env')) { Chk-Ok ".env 존재" } else { Chk-Fail ".env 없음" ".\sl.ps1 init $e" }

    # 3) DATABASE_URL
    $dburl = Get-EnvValue 'DATABASE_URL'
    if (-not $dburl) { Chk-Fail "DATABASE_URL 미설정" "deploy\env\.env 편집 — Supabase 대시보드 → Settings → Database" }
    elseif ($dburl -match 'CHANGE_ME|<.*>') { Chk-Fail "DATABASE_URL 이 템플릿 그대로" ".env 의 DATABASE_URL 을 실제 Supabase 연결 문자열로 교체" }
    else { Chk-Ok "DATABASE_URL 설정됨" }

    # 4) .env.images
    if ($e -ne 'dev') {
        if (Test-Path (Join-Path $EnvDir '.env.images')) { Chk-Ok ".env.images 존재" } else { Chk-Fail ".env.images 없음" "copy deploy\env\.env.images.example deploy\env\.env.images" }
    }

    # 5) strict → JWT 시크릿
    $authmode = Get-EnvValue 'AUTH_MODE'
    if ($e -ne 'dev' -and -not $authmode) { $authmode = 'strict' }
    if ($authmode -eq 'strict') {
        $jwt = (Get-EnvValue 'SUPABASE_JWT_SECRET') + (Get-EnvValue 'JWT_SECRET')
        if (-not $jwt) { Chk-Fail "JWT 시크릿 없음 (strict 모드)" ".env 에 SUPABASE_JWT_SECRET 설정 — Supabase 대시보드 → Settings → API" }
        else { Chk-Ok "JWT 시크릿 설정됨" }
    }

    # 6) GHCR 로그인 (prod)
    if ($e -eq 'prod') {
        $cfg = Join-Path $HOME '.docker\config.json'
        if ((Test-Path $cfg) -and (Select-String -Path $cfg -Pattern 'ghcr.io' -Quiet)) { Chk-Ok "GHCR 로그인 상태" }
        else { Chk-Warn "GHCR 로그인 안 보임 (공개 이미지면 무시 가능)" "비공개면: docker login ghcr.io" }
    }

    # 7) hosts (dev)
    if ($e -eq 'dev') {
        $hosts = "$env:SystemRoot\System32\drivers\etc\hosts"
        if ((Test-Path $hosts) -and (Select-String -Path $hosts -Pattern 'api\.localhost' -Quiet)) { Chk-Ok "hosts 에 *.localhost 등록됨" }
        else { Chk-Warn "hosts 에 api.localhost 없음" "관리자 권한으로 $hosts 에 추가: 127.0.0.1 www.localhost api.localhost dev.localhost" }
    }

    Write-Host
    if ($script:DoctorFail) { Write-Fail "doctor: 실패 항목 있음 — 위 '고치는 법'을 먼저 처리하세요."; exit 1 }
    Write-Ok "doctor: 이 환경은 기동 가능해 보입니다. → .\sl.ps1 up $e"
}

# ---- init -------------------------------------------------------------------
function Invoke-Init([string]$e) {
    Write-Host "== sl init ($e) =="

    $envFile = Join-Path $EnvDir '.env'
    if (-not (Test-Path $envFile)) {
        $tmpl = Join-Path $EnvDir '.env.example'
        if ($e -eq 'dev'  -and (Test-Path (Join-Path $EnvDir '.env.dev.example')))  { $tmpl = Join-Path $EnvDir '.env.dev.example' }
        if ($e -eq 'prod' -and (Test-Path (Join-Path $EnvDir '.env.prod.example'))) { $tmpl = Join-Path $EnvDir '.env.prod.example' }
        Copy-Item $tmpl $envFile
        Write-Ok ".env 생성 (← $(Split-Path $tmpl -Leaf))"
    } else { Write-Info ".env 이미 존재 — 건드리지 않음" }

    $imgFile = Join-Path $EnvDir '.env.images'
    if (-not (Test-Path $imgFile)) {
        Copy-Item (Join-Path $EnvDir '.env.images.example') $imgFile
        Write-Ok ".env.images 생성"
    } else { Write-Info ".env.images 이미 존재 — 건드리지 않음" }

    # 필수 값 안내 (PowerShell 대화형 채우기는 최소한으로 — 편집 링크 안내 중심)
    if (Select-String -Path $envFile -Pattern 'CHANGE_ME|<.*>' -Quiet) {
        Write-Warn ".env 에 템플릿 값이 남아 있습니다 — 아래 항목을 채우세요:"
        Write-Host "  notepad $envFile" -ForegroundColor Cyan
        Write-Info "필요 값: DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_JWT_SECRET"
        Write-Info "Supabase 대시보드 → Settings → Database / API 에서 복사"
    }

    if ($e -eq 'dev') {
        Write-Host
        Write-Info "로컬 브라우저 접속용 hosts 등록 (관리자 권한 필요):"
        Write-Host "  127.0.0.1  www.localhost api.localhost dev.localhost" -ForegroundColor Cyan
        Write-Info "  파일: $env:SystemRoot\System32\drivers\etc\hosts"
    }

    Write-Host
    try { Invoke-Doctor $e } catch { }
}

# ---- 명령 -------------------------------------------------------------------
switch ($Command) {
    'up' {
        $e = Require-Env $Env
        if ($e -eq 'prod') { try { Invoke-Doctor $e } catch { Die "doctor 실패 — 원인을 먼저 처리하세요" } }
        $cargs = Build-ComposeArgs $e
        if ($e -eq 'dev') { docker compose @cargs up -d --build }
        else              { docker compose @cargs up -d }
        if ($LASTEXITCODE -ne 0) { Die "up 실패 (exit $LASTEXITCODE)" }
        Write-Ok "up ($e) 완료 — 상태: .\sl.ps1 ps $e"
    }
    'down' {
        $e = Require-Env $Env
        if ($e -eq 'prod') {
            $yn = Read-Host "정말 prod 를 내릴까요? [yes/N]"
            if ($yn -ne 'yes') { Die "취소됨" }
        }
        $cargs = Build-ComposeArgs $e
        docker compose @cargs down
        Write-Ok "down ($e) 완료"
    }
    'logs' {
        $e = Require-Env $Env
        $cargs = Build-ComposeArgs $e
        if ($Arg2) { docker compose @cargs logs -f --tail=100 $Arg2 }
        else       { docker compose @cargs logs -f --tail=100 }
    }
    'ps' {
        $e = Require-Env $Env
        $cargs = Build-ComposeArgs $e
        docker compose @cargs ps
    }
    'doctor' { $e = Require-Env $Env; Invoke-Doctor $e }
    'init'   { $e = Require-Env $Env; Invoke-Init $e }
    'deploy' {
        if (-not $Env -or -not $Arg2) { Die "usage: .\sl.ps1 deploy <service> <image> [--env staging|prod] [--pull]" }
        & (Join-Path $Here 'deploy.sh') --service $Env --image $Arg2 @Rest
        if ($LASTEXITCODE -ne 0) { Die "deploy 실패 (exit $LASTEXITCODE)" }
    }
    default {
        Get-Content $MyInvocation.MyCommand.Path | Select-Object -Skip 1 -First 18
        exit 0
    }
}
