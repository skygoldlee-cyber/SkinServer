# Windows 11 테스트 환경 구축 — 설치 완료 및 검증 가이드

> 이 문서는 SkinLens 프로젝트의 **단위 테스트, 통합 테스트, Docker Compose 기동 테스트**를 Windows 11 머신에서 수행하기 위한 환경 구축 가이드입니다.
>
> **현재 상태: 시험환경 설치 및 검증이 완료되었습니다.** 2026-08-18 기준, 모든 필수 도구가 정상 작동하며 단위 테스트 96개가 통과했습니다.

---

## 1. 설치 항목 요약

| 순서 | 항목 | 용도 | 필수 여부 | 설치 상태 | 검증 버전 |
|:---|:---|:---|:---|:---|:---|
| 1 | **Docker Desktop** | 컨테이너 빌드/실행/Compose | 필수 | ✅ 완료 | v29.7.2 |
| 2 | **Python 3.12** | 단위/통합 테스트 실행 | 필수 | ✅ 완료 | v3.12.10 |
| 3 | **Git** | 버전 관리 및 저장소 클론 | 필수 | ✅ 완료 | v2.53.0 |
| 4 | **WSL2** | Linux 컨테이너 성능 향상 (Docker 백엔드) | 권장 | ✅ 완료 | Ubuntu v2 |
| 5 | **Node.js 20+** | 프론트엔드 빌드 (webapp, webapp-next) | 선택 | ✅ 완료 | — |
| 6 | **GNU Make** | `make test`, `make itest`, `make smoke` 단축 명령 | 선택* | ✅ 완료 | v3.81 |
| 7 | **curl** | 스모크 테스트 (`make smoke`) | 선택* | ✅ 완료 | v8.21.0 |

> \* **Windows 네이티브 대안:** Make와 curl 없이 [`deploy/scripts/sl.ps1`](../../deploy/scripts/sl.ps1)과 PowerShell로 동일한 작업을 수행할 수 있습니다. 자세한 내용은 [3.3절](#33-개발-환경-기동-docker-compose)을 참조하세요.

---

## 1.1 검증 완료 체크리스트 (2026-08-18)

| 확인 항목 | 명령 | 결과 | 비고 |
|:---|:---|:---|:---|
| Docker | `docker --version` | ✅ Docker version 29.7.2 | |
| Docker Compose | `docker compose version` | ✅ v5.4.0 | |
| Python | `python --version` | ✅ Python 3.12.10 | |
| Git | `git --version` | ✅ git version 2.53.0.windows.1 | |
| Make | `make --version` | ✅ GNU Make 3.81 | |
| curl | `curl --version` | ✅ curl 8.21.0 | Windows 기본 포함 |
| 프로젝트 의존성 | `pip list` | ✅ fastapi, uvicorn, pytest 등 설치됨 | |
| 단위 테스트 | `python -m pytest -m "not integration"` | ✅ 96개 테스트 통과 | |
| Docker Compose 구성 | `docker compose config` | ✅ 구성 오류 없음 | `.env` 파일 생성 후 |

> **참고:** 위 검증은 `deploy/env/.env` 파일이 생성된 상태에서 수행되었습니다. Supabase 연결 정보(`DATABASE_URL`)는 예시 값(`CHANGE_ME`)으로 남아있어, 실제 컨테이너 기동 전에 실제 값으로 교체가 필요합니다.

---

## 2. 상세 설치 가이드

### 2.1 Docker Desktop

Docker Desktop은 Windows에서 Linux 컨테이너를 실행하는 핵심 도구입니다.

**다운로드:** [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)

**설치 요구사항:**
- Windows 11 64-bit: Home, Pro, Enterprise, 또는 Education
- BIOS에서 가상화 활성화 (Intel VT-x 또는 AMD-V)
- WSL 2 기능 활성화 (권장, 아래 2.2 참조)

**설치 후 확인:**

```powershell
docker --version
docker compose version
```

**Docker Desktop 설정 권장사항:**
- Settings → General → "Use the WSL 2 based engine" 체크
- Settings → Resources → WSL Integration → Ubuntu 배포판 활성화

---

### 2.2 WSL2 (Windows Subsystem for Linux 2) — 권장

WSL2는 Docker Desktop의 Linux 컨테이너 실행 성능을 크게 향상시킵니다. SkinLens의 [`sl.ps1`](../../deploy/scripts/sl.ps1) 스크립트는 WSL 없이도 동작하지만, Docker Desktop 자체는 WSL2 백엔드를 권장합니다.

**설치 방법 (PowerShell 관리자 권한):**

```powershell
wsl --install
```

이 명령은 다음을 자동으로 처리합니다:
- 가상 머신 플랫폼 활성화
- WSL 기능 활성화
- WSL2 커널 설치
- 기본 Ubuntu 배포판 설치

**설치 후 확인:**

```powershell
# 재부팅 후 실행
wsl --update
wsl --set-default-version 2
wsl --list --verbose
```

**권장 배포판:** Ubuntu 24.04 LTS

```powershell
wsl --install -d Ubuntu-24.04
```

> **참고:** WSL2 없이 Docker Desktop을 사용할 수도 있으나, 성능 및 호환성 문제로 WSL2 백엔드를 강력히 권장합니다. 단, [`sl.ps1`](../../deploy/scripts/sl.ps1)을 사용한 기동/테스트는 WSL 없이도 가능합니다.

---

### 2.3 Python 3.12

단위 테스트(`make test` → `pytest -m "not integration"`)와 통합 테스트(`make itest` → `pytest -m integration`)를 실행하기 위해 Python이 필요합니다.

**설치 방법:**

```powershell
# winget 사용 (권장)
winget install Python.Python.3.12

# 또는 수동 다운로드
# https://www.python.org/downloads/
```

**설치 후 확인:**

```powershell
python --version  # Python 3.12.x
pip --version
```

> **중요:** Windows에서는 `python` 명령이 일반적이지만, [`Makefile`](Makefile)과 일부 스크립트는 `python3`를 사용합니다. 아래 [2.3.1](#231-python3-명령-사용-방법)을 참조하여 `python3` 명령을 활성화하세요.

#### 2.3.1 `python3` 명령 사용 방법

Windows에서 `python3` 명령을 사용하는 방법은 세 가지입니다.

**방법 1: Python 설치 시 "Add python.exe to PATH"와 "py launcher" 체크 (권장)**

Python 공식 설치 프로그램에서 다음 옵션을 모두 체크합니다:
- Add python.exe to PATH
- Install launcher for all users (py launcher)

설치 후 `py -3` 또는 `python`으로 실행 가능하지만, `python3`는 기본적으로 등록되지 않습니다.

**방법 2: `python3` 별칭 등록 (PowerShell 프로필)**

```powershell
# PowerShell 프로필 열기
notepad $PROFILE

# 다음 줄 추가
Set-Alias python3 python

# 프로필 적용
. $PROFILE
```

**방법 3: Microsoft Store 별칭 사용**

Windows 11에서 `python3` 명령을 입력하면 Microsoft Store로 연결되는 경우, 이를 설치하면 `python3` 명령이 활성화됩니다. 단, 기존 Python 설치와 충돌할 수 있으므로 주의하세요.

**프로젝트 의존성 설치:**

```powershell
pip install -r requirements-dev.txt
```

**의존성 목록 (`requirements-dev.txt`):**
- `fastapi` — API 서버
- `uvicorn[standard]` — ASGI 서버
- `python-multipart` — 파일 업로드
- `pydantic` — 데이터 검증
- `numpy` — 수치 계산
- `opencv-python-headless` — 이미지 처리 (분석 엔진)
- `psycopg[binary]` — PostgreSQL 드라이버
- `httpx` — HTTP 클라이언트
- `pytest` — 테스트 프레임워크

**테스트 구성 (`pytest.ini`):**
- 테스트 경로: `tests/`
- 제외: `tests/test_environment.py` (환경 검증용으로 CI에서 제외)
- 마커: `integration` — DB/네트워크가 필요한 통합 테스트 (임시 Postgres + 엔진 서브프로세스)

---

### 2.4 Git

저장소 클론 및 버전 관리를 위해 필요합니다.

**설치 방법:**

```powershell
winget install Git.Git
```

**확인:**

```powershell
git --version
```

---

### 2.5 Node.js 20+ (선택)

프론트엔드 빌드(`apps/webapp`, `apps/webapp-next`)가 필요한 경우에만 설치합니다.

**설치 방법:**

```powershell
winget install OpenJS.NodeJS.LTS
```

**확인:**

```powershell
node --version  # v20.x.x 이상
npm --version
```

---

### 2.6 GNU Make (선택)

[`Makefile`](Makefile)에 정의된 단축 명령(`make test`, `make itest`, `make smoke`, `make dev-up` 등)을 사용하려면 Make가 필요합니다.

> **Windows 네이티브 대안:** Make 없이 PowerShell에서 [`deploy/scripts/sl.ps1`](../../deploy/scripts/sl.ps1) 스크립트를 직접 사용하거나, `pytest` 명령을 직접 실행할 수 있습니다.

**설치 방법 (택 1):**

```powershell
# 방법 1: winget
winget install GnuWin32.Make

# 방법 2: Chocolatey
choco install make

# 방법 3: WSL 내에서 사용 (권장)
wsl -d Ubuntu-24.04 -e sudo apt-get update
wsl -d Ubuntu-24.04 -e sudo apt-get install -y make
```

> **주의:** `make smoke`는 `curl`, `python3`, `seq` 등 Unix 유틸리티를 사용하므로, Windows 네이티브 Make로는 실행이 어려울 수 있습니다. 이 경우 WSL 터미널에서 `make smoke`를 실행하거나, 아래 [3.4절](#34-스모크-테스트-엔드투엔드)의 PowerShell 대안을 사용하세요.

---

### 2.7 curl (선택)

스모크 테스트(`make smoke`)에서 업로드 → job_id → 단계 타임라인을 확인하기 위해 HTTP 요청을 전송할 때 사용합니다.

**설치 방법 (택 1):**

```powershell
# 방법 1: winget
winget install cURL.cURL

# 방법 2: WSL 내에서 사용
wsl -d Ubuntu-24.04 -e sudo apt-get install -y curl
```

> **참고:** Windows 11에는 `curl.exe`가 기본 포함되어 있습니다 (`C:\Windows\System32\curl.exe`). 별도 설치 없이 사용 가능한지 먼저 확인하세요. 단, `make smoke`는 `curl`과 함께 `python3`, `seq`도 필요하므로 Windows 네이티브에서는 PowerShell 대안을 권장합니다.

---

## 3. 테스트 실행 절차

### 3.1 단위 테스트 (인프라 불필요)

```powershell
# Python 직접 실행 (Windows 네이티브)
python -m pytest -m "not integration"

# 또는 Make 사용 (WSL 또는 Make 설치 시)
make test
```

### 3.2 통합 테스트 (임시 Postgres 필요)

통합 테스트는 `tests/integration/` 디렉토리에 있으며, `conftest.py`에서 임시 Postgres 컨테이너를 자동으로 기동합니다.

```powershell
# DATABASE_URL 환경 변수가 필요하지만, conftest.py가 자동 설정하는 경우가 많음
# 수동 설정 예시:
$env:DATABASE_URL = "postgresql://user:pass@localhost:5432/testdb"
python -m pytest -m integration

# 또는 Make 사용
make itest
```

> **참고:** 통합 테스트의 정확한 DB 기동 방식은 [`tests/integration/conftest.py`](../../tests/integration/conftest.py)를 참조하세요.

### 3.3 개발 환경 기동 (Docker Compose)

#### Windows 네이티브 (PowerShell)

```powershell
# sl.ps1 사용 (WSL 불필요)
.\deploy\scripts\sl.ps1 up dev
.\deploy\scripts\sl.ps1 logs dev
.\deploy\scripts\sl.ps1 down dev

# 직접 docker compose 사용
docker compose -f deploy/compose/compose.base.yml -f deploy/compose/compose.dev.yml --env-file deploy/env/.env up -d --build
```

#### WSL 또는 Make 사용 시

```bash
# Make 래퍼 사용
make dev-up
make dev-logs
make dev-down

# 또는 bash 스크립트 직접 사용
./deploy/scripts/sl up dev
./deploy/scripts/sl logs dev
./deploy/scripts/sl down dev
```

### 3.4 스모크 테스트 (엔드투엔드)

개발 환경이 기동된 상태에서:

```bash
# Make 사용 (WSL 권장)
make smoke
```

**Windows 네이티브 PowerShell 대안:**

```powershell
# 1. 업로드
$resp = Invoke-RestMethod -Uri "http://localhost/analyze" -Method Post -Form @{ image = Get-Item "tests/fixtures/sample.jpg" } -Headers @{ Host = "api.localhost" }
$jobId = $resp.job_id
Write-Host "job_id=$jobId"

# 2. 상태 폴
$status = ""
for ($i = 0; $i -lt 30; $i++) {
    $job = Invoke-RestMethod -Uri "http://localhost/jobs/$jobId" -Headers @{ Host = "api.localhost" }
    $status = $job.status
    Write-Host "  $status"
    if ($status -eq "done") { break }
    Start-Sleep -Seconds 1
}

# 3. 단계 타임라인
$events = Invoke-RestMethod -Uri "http://localhost/jobs/$jobId/events" -Headers @{ Host = "api.localhost" }
$events.events | ForEach-Object { Write-Host "   $($_.stage)" }
```

스모크 테스트는 다음을 수행합니다:
1. `tests/fixtures/sample.jpg`를 `/analyze`로 업로드
2. `job_id`를 받아 `/jobs/{job_id}` 상태를 폴
3. 완료 시 `/jobs/{job_id}/events`에서 단계 타임라인 출력

---

## 4. 환경 검증 체크리스트

> **시험환경 설치가 완료되었습니다.** 아래 명령을 실행하여 모든 항목이 정상인지 최종 확인하세요.

| 확인 항목 | 명령 | 예상 결과 | 확인 |
|:---|:---|:---|:---|
| Docker | `docker --version` | 24.x 이상 | ☐ |
| Docker Compose | `docker compose version` | v2.x 이상 | ☐ |
| Python | `python --version` | 3.12.x | ☐ |
| Git | `git --version` | 2.x 이상 | ☐ |
| WSL2 (권장) | `wsl --list --verbose` | Ubuntu-24.04, VERSION 2 | ☐ |
| Make (선택) | `make --version` | 4.x | ☐ |
| curl (선택) | `curl --version` | 8.x | ☐ |
| 프로젝트 의존성 | `pip list \| findstr fastapi` | fastapi 설치됨 | ☐ |
| 단위 테스트 | `python -m pytest -m "not integration"` | 모든 테스트 통과 | ☐ |
| Docker 기동 | `docker compose -f deploy/compose/compose.base.yml -f deploy/compose/compose.dev.yml --env-file deploy/env/.env config` | 구성 오류 없음 | ☐ |

**빠른 검증 스크립트 (PowerShell):**

```powershell
Write-Host "=== SkinLens 시험환경 검증 ===" -ForegroundColor Cyan
Write-Host "Docker: $(docker --version)"
Write-Host "Compose: $(docker compose version)"
Write-Host "Python: $(python --version)"
Write-Host "Git: $(git --version)"
Write-Host "WSL: $(wsl --list --verbose | Out-String)"
Write-Host "Make: $(make --version | Select-Object -First 1)"
Write-Host "curl: $(curl --version | Select-Object -First 1)"
Write-Host "=== 의존성 확인 ===" -ForegroundColor Cyan
pip list | Select-String -Pattern "fastapi|uvicorn|pytest|httpx|numpy|opencv"
Write-Host "=== 단위 테스트 실행 ===" -ForegroundColor Cyan
python -m pytest -m "not integration" -q
```

---

## 5. 트러블슈팅

### 5.1 Docker Desktop이 시작되지 않음

- BIOS에서 가상화(VT-x/AMD-V)가 활성화되어 있는지 확인
- WSL2가 정상 설치되었는지 확인: `wsl --status`
- Docker Desktop 설정에서 WSL2 백엔드 사용 확인

### 5.2 `make` 명령을 찾을 수 없음

- Windows 네이티브에서는 [`deploy/scripts/sl.ps1`](../../deploy/scripts/sl.ps1)을 직접 사용
- 또는 WSL 터미널에서 `make` 실행

### 5.3 `python3` 명령을 찾을 수 없음

- [2.3.1절](#231-python3-명령-사용-방법)의 별칭 설정을 참조
- 또는 `python`으로 대체하여 실행

### 5.4 통합 테스트 DB 연결 실패

- `DATABASE_URL` 환경 변수가 올바르게 설정되었는지 확인
- 임시 Postgres 컨테이너가 실행 중인지 확인: `docker ps`
- [`tests/integration/conftest.py`](../../tests/integration/conftest.py)에서 DB 기동 방식 확인

### 5.5 `make smoke`가 Windows에서 실패함

- `make smoke`는 `curl`, `python3`, `seq`를 필요로 합니다
- Windows 네이티브에서는 [3.4절](#34-스모크-테스트-엔드투엔드)의 PowerShell 대안을 사용하세요

### 5.6 `docker`, `python`, `git`, `make` 명령을 찾을 수 없음 (PATH 미설정)

**증상:** 도구는 설치되어 있으나 명령 프롬프트에서 인식하지 못함

**원인:** 시스템 PATH 환경 변수에 해당 경로가 등록되지 않음

**해결:** `Win + R` → `sysdm.cpl` → `고급` → `환경 변수` → `Path` 편집에서 다음 경로 추가:

```
C:\Program Files\Docker\Docker\resources\bin
C:\Users\<사용자명>\AppData\Local\Programs\Python\Python312\
C:\Users\<사용자명>\AppData\Local\Programs\Python\Python312\Scripts\
C:\Program Files\Git\cmd
C:\Program Files (x86)\GnuWin32\bin
```

> **참고:** 위 경로는 2026-08-18 검증 시점의 기본 설치 경로입니다. 사용자 지정 설치 시 경로가 다를 수 있습니다.

### 5.7 `python` 실행 시 Windows Store가 열림 (0바이트 가짜 python.exe)

**증상:** `python --version` 입력 시 Microsoft Store가 열리거나 아무 출력도 없음

**원인:** `C:\Users\<사용자명>\AppData\Local\Microsoft\WindowsApps\python.exe` (0바이트 Windows Store 별칭)이 PATH에서 실제 Python보다 먼저 위치

**해결 (택 1):**

1. **Windows 설정에서 앱 실행 별칭 끄기 (권장)**
   - `설정` → `앱` → `고급 앱 설정` → `앱 실행 별칭`
   - `python.exe`, `python3.exe` → **끔**
   - **추가 조치:** 아래 2번 방법으로 파일 삭제 필요 (별칭을 꺼도 파일이 남아있을 수 있음)

2. **가짜 python.exe 파일 삭제 (가장 확실)**
   ```cmd
   del "C:\Users\<사용자명>\AppData\Local\Microsoft\WindowsApps\python.exe"
   del "C:\Users\<사용자명>\AppData\Local\Microsoft\WindowsApps\python3.exe"
   ```

3. **PATH 순서 변경**
   - `C:\Users\<사용자명>\AppData\Local\Programs\Python\Python312\`를 `WindowsApps`보다 **위**로 이동

### 5.8 `deploy/env/.env` 파일이 없음

**증상:** `docker compose config` 실행 시 `DATABASE_URL is missing a value` 오류

**원인:** `deploy/env/.env` 파일이 생성되지 않음

**해결:**
```cmd
copy "deploy\env\.env.example" "deploy\env\.env"
```

> **참고:** 생성된 `.env` 파일의 `DATABASE_URL` 등은 예시 값(`CHANGE_ME`)입니다. 실제 Supabase 프로젝트 연결 문자열로 교체 후 컨테이너를 기동하세요. 단위 테스트는 DB 없이 실행 가능합니다.

### 5.9 `opencv-python-headless` 설치 실패

- Python 버전이 3.12인지 확인
- Microsoft Visual C++ Build Tools가 필요할 수 있음 (일반적으로 wheel이 제공되므로 문제없음)

---

## 6. 관련 문서

- [`docs/operations/환경별_빌드_기동_절차.md`](../operations/환경별_빌드_기동_절차.md) — 환경별 빌드/기동 상세 절차
- [`docs/operations/서버_실행_운영_가이드.md`](../operations/서버_실행_운영_가이드.md) — 서버 실행 운영 가이드
- [`deploy/scripts/sl.ps1`](../../deploy/scripts/sl.ps1) — Windows 네이티브 기동 스크립트 (WSL 불필요)
- [`deploy/scripts/sl`](../../deploy/scripts/sl) — Bash 기동 스크립트 (WSL/Linux)
- [`Makefile`](../../Makefile) — Make 단축 명령 정의
- [`tests/integration/conftest.py`](../../tests/integration/conftest.py) — 통합 테스트 DB 기동 로직
