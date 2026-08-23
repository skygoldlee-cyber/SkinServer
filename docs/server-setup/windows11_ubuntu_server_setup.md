# 한눈에 보기 — "내 데스크톱 안에 작은 리눅스 집을 짓는 이야기"

> 이 문서 전체를 명령어 없이 먼저 그림으로 이해하기 위한 **개요**입니다.
> 아래 이야기의 각 단계 끝에 붙은 (○장)은 뒤이어 나오는 상세 가이드의 해당 장으로 이어집니다.

지금 쓰는 **윈도우 11 데스크톱을 하나의 건물**이라고 생각해 보세요. 평소엔 내가 사는 집(윈도우)이지만, 그 안 한쪽에 **리눅스로 된 별채**를 지어 웹 서버를 돌리고, 멀리 있는 다른 PC에서 그 별채로 원격으로 드나들며 개발·운영하는 것이 목표입니다. 서버 프로그램은 대부분 리눅스에서 가장 매끄럽게 돌기 때문에, 윈도우를 갈아엎지 않고 리눅스 환경만 통째로 얹어주는 **WSL2**가 그 별채를 세워줍니다. (0~1장)

---

**① 별채 짓기 — WSL2 + 우분투 (2장)**
윈도우에게 "리눅스 별채 하나 지어줘"라고 부탁하면, 알아서 터를 닦고(가상화 기능을 켜고) 우분투라는 리눅스 집을 들여놓습니다. 서버로 쓸 거라 메모리·CPU를 넉넉히 배정하고, **재부팅 후에도 스스로 살림을 돌리도록**(systemd) 깨워둡니다.

**② 살림 차리기 — 기본 세팅 (3~4장)**
새집에 이사 오면 하는 일과 같습니다. 관리자 계정을 만들고, 개발 필수품(git·python 등)을 채우고, 벽시계를 서울 시간대로 맞춥니다. 시계를 맞추는 건 사소해 보여도, 나중에 문제가 생겼을 때 **일지(로그)의 시간이 정확해야** 원인을 빨리 찾기 때문이에요.

**③ 현관에 열쇠 달기 — SSH (5~7장)**
멀리 있는 노트북에서 별채로 들어갈 **문과 열쇠(SSH)**를 만듭니다. 처음엔 비밀번호로 열지만 곧 **열쇠(키) 방식**으로 바꿔 안전하게 잠급니다. 비밀번호는 계속 두들기면 뚫릴 수 있지만 열쇠는 훨씬 안전하거든요. 깃허브 계정 두 개는 열쇠고리에 **이름표를 붙여** 상황에 맞는 열쇠가 자동으로 골라지게 정리합니다.

**④ 방마다 설비 들이기 — Docker 웹 스택 (8~9장)**
서비스를 **완성된 상태로 밀봉된 상자(컨테이너)**에 담아 들여놓습니다(Docker). 내 집을 어지르지 않고, 상자만 놓으면 바로 작동하고, 필요 없으면 상자째 치우면 됩니다. 손님이 오면 **접수처(Nginx)**가 맞이해 안쪽 **일꾼(FastAPI)**에게 안내하고, 일꾼은 필요할 때 **창고(PostgreSQL)**에서 자료를 꺼냅니다. **손님 → 접수처 → 일꾼 → 창고**, 이 흐름이 웹 서비스의 뼈대입니다.

```mermaid
flowchart LR
    G["🙋 손님<br/>바깥에서 온 요청"] -->|요청| N["🏢 접수처<br/>Nginx :80"]
    N -->|안내| F["👷 일꾼<br/>FastAPI :8000"]
    F -->|자료 꺼냄| P["📦 창고<br/>PostgreSQL :5432"]
```

> 응답은 온 길을 그대로 되돌아 나갑니다: **창고 → 일꾼 → 접수처 → 손님.** 접수처(Nginx)만 바깥을 향해 문을 열고, 일꾼과 창고는 그 안쪽에서만 서로 이야기합니다.

**⑤ 손님 받기 — 바깥에서 접속 (10장)**
방은 다 꾸몄지만, 아직 바깥 사람은 못 들어옵니다. 별채가 건물 안쪽 깊숙이 있어서, 정문(윈도우)에서 별채까지 **복도를 뚫어줘야**(포트포워딩) 다른 PC가 접속할 수 있어요. 인터넷 전체 공개는 도메인과 **자물쇠(HTTPS)**가 더 필요하며, 문을 많이 열수록 도둑도 들기 쉬우니 **꼭 필요한 문만 여는 것**이 원칙입니다.

**⑥ "제대로 됐나" 확인 — 검증 (11~15장)**
단계마다 초록불(PASS)·빨간불(FAIL)을 자동으로 켜주는 **체크리스트 프로그램**을 함께 돌립니다. ⑴ 서버 안에서 보는 점검표, ⑵ 노트북에서 "저 서버에 잘 닿나" 보는 점검표, ⑶ 어디서나 반복해 돌리는 점검표 — 세 종류입니다. 빨간불이 뜨면 그 단계로 돌아가 고친 뒤 다시 확인합니다.

**⑦ 자리를 비워도 알아서 굴러가게 — 운영 (16~27장)**
핵심 원칙은 **정전(재부팅)이 나도 서버가 스스로 다시 켜져야 한다**는 것. 컴퓨터가 켜지면 별채·방·복도가 자동으로 살아나게 예약을 걸어둡니다. 여기에 창고(DB)를 **매일 밤 자동 백업**하고, 일지가 디스크를 채우지 않게 오래된 건 정리하고, 문을 계속 두들기는 수상한 손님은 **자동 차단**하고, 이상이 생기면 알려주는 **경비실(모니터링)**을 둡니다.

**⑧ 진짜 셋집으로 이사 — Vercel + Render + Supabase 3-Tier 이관**
내 데스크톱은 개발·연습용으로 훌륭하지만, 24시간 안정적으로 서비스하려면 **Vercel, Render, Supabase**와 같은 관리형 서비스를 이용하는 것이 낫습니다. 기존의 물리 서버(VPS)를 직접 대여해 OS, Nginx, 방화벽 등을 직접 관리하는 방식 대신, 프론트엔드는 **Vercel**, 백엔드는 **Render**, 데이터베이스와 스토리지는 **Supabase**로 분산하여 운영하는 3-Tier 아키텍처로 이전하는 것을 권장합니다. 이 경우 고정 IP 주소를 직접 확보하거나 복잡한 포트포워딩, 수동 SSL 설정을 할 필요가 없으며, Git push만으로 안전하고 빠르게 자동 배포됩니다.
자세한 구성은 [Vercel + Render 기반 웹서비스 도메인 및 IP 구성 가이드](file:///c:/Project/SkinServer/docs/server-setup/Vercel_Render_기반_웹서비스_도메인_IP_구성_가이드_수정본.md)와 [SkinLens 3-Tier 마이그레이션 계획서](file:///c:/Project/SkinServer/SkinLens_3Tier_Migration.md)를 참조하십시오. (※ 특수 목적으로 자체 VPS 서버를 운영해야 하는 경우에 한해 레거시 이관 런북을 참조합니다.)


---

**한 줄 요약**
윈도우 안에 리눅스 별채를 짓고 → 열쇠를 달고 → 서비스 방을 꾸미고 → 손님을 받고 → 잘 됐는지 확인하고 → 알아서 굴러가게 만들고 → 나중엔 진짜 셋집으로 이사한다.

아래부터는 이 이야기의 각 단계를 **실제 명령·설정으로 구현하는 상세 가이드**입니다.

---

# Windows 11 데스크톱에 Ubuntu 서버 환경 구축 (상세판)

Windows 11 데스크톱(원격 PC)을 **WSL2 기반 Ubuntu 서버**로 만들고, 로컬 PC에서 SSH로 접속해 개발·운영하는 전 과정을 명령·설정 파일 단위로 정리한 문서입니다. 마지막에 각 단계를 코드로 검증하는 절차와 스크립트가 포함됩니다.

- 서버(원격): Windows 11 + WSL2 + Ubuntu 24.04 + Docker(Nginx / FastAPI / PostgreSQL)
- 클라이언트(로컬): 내 PC에서 SSH·HTTP로 원격 서버에 접속
- 계정: GitHub 다중 계정(coteleafdev / skygoldlee-cyber) SSH 키 분리

> 표기 규칙: `PS>` = Windows PowerShell(관리자), `$` = Ubuntu 셸, `local$` = 로컬 PC 셸.

---

## 0. 사전 준비 (필수 확인)

구축 전에 다음을 확인합니다.

- **Windows 11 버전**: `winver` 실행 → 22H2 이상 권장(미러 네트워킹 등 최신 기능 사용).
- **가상화 활성화**: 작업 관리자 → 성능 → CPU → "가상화: 사용"인지 확인. 사용 안 함이면 BIOS/UEFI에서 Intel VT-x 또는 AMD-V(SVM)를 켭니다.
- **관리자 권한**: WSL 설치·포트포워딩·방화벽 설정에 필요.
- **디스크 여유**: WSL 배포판 + Docker 이미지로 최소 20GB 이상 권장.

---

## 1. 전체 아키텍처

```text
[로컬 PC]  ──SSH(22)/HTTP(80)──▶  [원격 Windows 11 데스크톱]
                                        │
                                        ├── VS Code (WSL 원격)
                                        ├── Docker Desktop
                                        │
                                        └── WSL2
                                             └── Ubuntu 24.04
                                                  ├── SSH 서버(sshd)
                                                  ├── Git / GitHub(다중 계정)
                                                  ├── Python
                                                  └── Docker
                                                       ├── Nginx     (:80)
                                                       ├── FastAPI   (:8000)
                                                       └── PostgreSQL(:5432)
```

요청 흐름:

```text
인터넷/LAN → (Windows 호스트 포트) → WSL2 → Nginx(:80) → FastAPI(:8000) → PostgreSQL(:5432)
```

---

## 2. WSL2 설치

Windows에서 **PowerShell을 관리자 권한**으로 실행합니다.

```powershell
PS> wsl --install
```

이 명령은 "가상 머신 플랫폼 / WSL" 기능 활성화 + WSL2 + 기본 Ubuntu 설치까지 한 번에 처리합니다. 끝나면 **PC를 재부팅**합니다.

재부팅 후 최신화 및 기본 버전 고정:

```powershell
PS> wsl --update
PS> wsl --set-default-version 2
```

설치 가능한 배포판 목록에서 원하는 버전을 지정 설치할 수도 있습니다(예: 24.04).

```powershell
PS> wsl --list --online
PS> wsl --install -d Ubuntu-24.04
```

설치된 배포판과 WSL 버전 확인:

```powershell
PS> wsl -l -v
```

정상이면 다음과 비슷하게 표시됩니다(VERSION이 반드시 `2`).

```text
  NAME              STATE           VERSION
* Ubuntu-24.04      Running         2
```

### 2-1. `.wslconfig` (전역 리소스·네트워킹)

Windows 사용자 폴더(`C:\Users\<사용자>\.wslconfig`)에 생성합니다. 서버 용도이므로 리소스를 넉넉히 배정합니다.

```ini
[wsl2]
memory=8GB
processors=4
swap=2GB

# (v3) 유휴 종료 시각을 명시적으로 정합니다.
#  - 값(밀리초)만큼 상주 프로세스가 없으면 배포판이 종료됩니다(기본 60000).
#  - 백업 등 시간 기반 작업이 idle 종료로 누락되는 문제(운영 파트 상단·18-2-1장)와
#    직결되므로, 정책을 문서에 남기는 의미로 값을 박아 둡니다. 상시 가동이 필요하면 -1.
vmIdleTimeout=60000

# Windows 11 22H2+ : 미러 네트워킹
#  - WSL의 IP가 Windows 호스트와 동일해져 포트포워딩(10-2장)이 불필요해집니다.
#  - LAN/외부 노출이 쉬워지지만, 방화벽 설정은 여전히 필요합니다.
networkingMode=mirrored
```

> 미러 모드가 부담스러우면 이 줄을 빼고 기본(NAT) + 포트포워딩(10-2장) 방식을 씁니다. 아래 문서는 두 경우를 모두 다룹니다.

> ⚠ **(v3) 절전·최대절전 후 시계 드리프트.** 호스트 PC가 sleep/hibernate에서 깨어나면 WSL2 VM의 시계가 실제 시각보다 뒤처지는 알려진 현상이 있습니다. 이 상태로는 **TLS 인증서 검증·JWT 만료·apt 서명·로그 타임스탬프**가 어긋납니다. 증상(예: `date`가 실제와 다름, 갑작스런 인증서 오류)이 보이면 WSL 안에서 `sudo hwclock -s`로 강제 동기화합니다. 데스크톱을 자주 재우는 환경이면 부팅 스크립트(16-2장)에 이 동기화를 넣어 두는 것을 권합니다.

### 2-2. 적용

`.wslconfig`나 `/etc/wsl.conf`(다음 장)를 바꾼 뒤에는 WSL을 완전히 종료했다 다시 켜야 반영됩니다.

```powershell
PS> wsl --shutdown
```

---

## 3. Ubuntu 초기 설정

### 3-1. 최초 사용자 생성

시작 메뉴에서 **Ubuntu**를 실행합니다. 최초 1회 UNIX 사용자/비밀번호를 만듭니다(이 계정이 sudo 권한을 가집니다).

```text
Enter new UNIX username: coteleaf
New password:            (입력 시 화면에 표시되지 않는 것이 정상)
```

### 3-2. systemd 활성화 (`/etc/wsl.conf`)

SSH·Docker 서비스를 `systemctl`로 관리하려면 systemd를 켜는 것이 편합니다.

```bash
$ sudo tee /etc/wsl.conf >/dev/null <<'EOF'
[boot]
systemd=true

[network]
generateHosts=true
generateResolvConf=true

[user]
default=coteleaf
EOF
```

적용을 위해 PowerShell에서 `wsl --shutdown` 후 Ubuntu를 다시 실행합니다. 확인:

```bash
$ systemctl is-system-running     # running 또는 degraded 면 systemd 동작 중
```

### 3-3. 패키지 최신화 및 기본 도구

```bash
$ sudo apt update
$ sudo apt upgrade -y
$ sudo apt install -y git curl wget build-essential ca-certificates gnupg lsb-release \
                      software-properties-common unzip net-tools
```

설치 확인:

```bash
$ git --version
$ gcc --version
$ python3 --version
```

### 3-4. 시간대·로케일 (로그 시간 정확도)

```bash
$ sudo timedatectl set-timezone Asia/Seoul     # systemd 활성화 시
$ sudo apt install -y language-pack-ko
$ sudo update-locale LANG=ko_KR.UTF-8
```

여기까지 완료하면 **WSL2 기반 Ubuntu 서버의 뼈대**가 만들어집니다. → 검증: `./verify_server.sh base`

---

## 4. Python 개발 환경

시스템 파이썬을 직접 오염시키지 않도록 **가상환경(venv)** 사용을 기본으로 합니다.

```bash
$ sudo apt install -y python3-venv python3-pip python3-dev

# 프로젝트별 가상환경 예시
$ mkdir -p ~/projects && cd ~/projects
$ python3 -m venv .venv
$ source .venv/bin/activate
(.venv) $ pip install --upgrade pip
(.venv) $ python -V
```

> 여러 파이썬 버전이 필요하면 `pyenv` 도입을 검토합니다(선택). Docker로 서비스를 돌릴 경우 런타임은 컨테이너 안에서 관리되므로, 호스트 venv는 주로 로컬 개발·스크립트용입니다.

---

## 5. SSH 서버 설정

로컬 PC에서 원격 서버로 접속하기 위한 핵심 단계입니다.

### 5-1. 설치

```bash
$ sudo apt install -y openssh-server
```

### 5-2. 포트 충돌 확인 (중요)

Windows 자체 OpenSSH 서버가 22번을 이미 쓰고 있으면 WSL sshd와 충돌할 수 있습니다. Windows PowerShell(관리자)에서 확인:

```powershell
PS> Get-Service sshd -ErrorAction SilentlyContinue
PS> netstat -ano | findstr ":22 "
```

- Windows sshd가 22를 점유 중이면 → WSL sshd는 **다른 포트(예: 2222)** 를 쓰거나, Windows sshd를 중지합니다.
- 이 문서는 WSL sshd를 **22**로 두되, 충돌 시 2222 대안을 병기합니다.

### 5-3. `/etc/ssh/sshd_config` 편집

```bash
$ sudo nano /etc/ssh/sshd_config
```

핵심 항목(없으면 추가, 있으면 수정):

```text
Port 22
# 22 충돌 시:  Port 2222

PermitRootLogin no
PubkeyAuthentication yes

# 키 등록(6장)까지는 yes 로 두고, 키 접속 확인 후 no 로 변경 권장
PasswordAuthentication yes

# 접속 허용 사용자 제한(보안)
AllowUsers coteleaf

# (v3) 추가 하드닝 — 무차별 시도·유휴 세션·불필요 포워딩 조이기
MaxAuthTries 3
LoginGraceTime 20
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
# ⚠ AllowTcpForwarding 는 기본값(yes)을 유지합니다. 이 문서는 관리 포트(adminer 8080·
#   uptime-kuma 3001·DB 5432)를 SSH 로컬 포워딩(ssh -L …, 9-3-1·부록·런북 §7-1)으로만
#   접근하도록 설계돼 있어, 아래를 켜면 그 터널이 막힙니다. 관리 접근에 -L 터널을 쓰지
#   않는 서버에서만 주석을 해제하세요.
# AllowTcpForwarding no
```

> ⚠ `AllowUsers`는 **실제 로그인 계정명과 반드시 일치**해야 합니다. 여기 값(`coteleaf`)을 그대로 둔 채 다른 계정(예: 외부 호스팅 서버의 기본 계정 `ubuntu`)으로 접속하면 **자기 자신이 차단되어 SSH 로그인이 막힙니다.** 이관 런북대로 대상 서버에 이 하드닝을 재적용할 때는 `AllowUsers ubuntu`처럼 그 서버의 계정으로 바꾸세요(여러 계정이면 공백으로 나열). 변경 후에는 **기존 세션을 유지한 채** 새 창에서 접속을 확인하고 나서 원래 세션을 닫습니다.

> ⚠ **(v3) 원격 락아웃 방지 — sshd 변경의 표준 절차.** `sshd_config`를 바꾼 뒤 곧바로 재시작하면, 오타가 있어도 검증 없이 죽어 **원격에서 잠깁니다.** 항상 **문법 검증 → (통과 시에만) 재시작 → 실제 적용값 확인** 순서로, 그리고 **기존 SSH 세션을 열어둔 채** 새 창으로 접속이 되는 것을 확인한 다음 원래 세션을 닫으세요.
>
> ```bash
> # 1) 편집 후 문법 검증 → 통과해야만 재시작
> $ sudo sshd -t && sudo systemctl restart ssh
>
> # 2) 파일이 아니라 '실제 적용된 값'을 확인 (nano 오타·중복 지시어 잡기)
> $ sudo sshd -T | grep -iE '^(passwordauthentication|permitrootlogin|allowusers|maxauthtries)'
>
> # 3) ★ 지금 이 세션은 그대로 둔 채 ★ 새 터미널에서 접속 확인
> local$ ssh coteleaf@<서버>      # 성공하면 원래 세션을 닫는다
> ```
>
> `nano`로 직접 넣기 어렵다면, "없으면 추가·있으면 수정"을 스크립트로 처리할 수 있습니다(6-4장의 `PasswordAuthentication` 예시와 동일한 패턴 — `sed`는 해당 줄이 없으면 아무것도 안 바꾸므로 append 폴백이 필요합니다).

### 5-4. 서비스 기동

systemd가 켜져 있으면:

```bash
$ sudo systemctl enable --now ssh
$ sudo sshd -t && sudo systemctl restart ssh     # (v3) 문법 검증 통과 시에만 재시작
$ systemctl status ssh --no-pager
```

systemd를 안 쓰는 경우:

```bash
$ sudo service ssh start
```

포트 LISTEN 확인:

```bash
$ ss -tlnp | grep ':22'
```

→ 검증: `./verify_server.sh ssh`

---

## 6. 로컬 PC에서 SSH 접속

### 6-1. 로컬 PC에서 키 생성

로컬 PC(Windows PowerShell 또는 터미널)에서 실행합니다.

```powershell
local$ ssh-keygen -t ed25519 -C "local-pc" -f $env:USERPROFILE\.ssh\id_ed25519
```

(리눅스/맥 로컬이면 `ssh-keygen -t ed25519 -C "local-pc"`)

### 6-2. 공개키를 서버에 등록

간편 방법(로컬에 `ssh-copy-id`가 있으면):

```bash
local$ ssh-copy-id -p 22 coteleaf@<서버_IP>
```

수동 등록(공개키 내용을 서버 `~/.ssh/authorized_keys`에 추가):

```bash
$ mkdir -p ~/.ssh && chmod 700 ~/.ssh
$ nano ~/.ssh/authorized_keys        # 로컬의 id_ed25519.pub 내용 붙여넣기
$ chmod 600 ~/.ssh/authorized_keys
```

### 6-3. 로컬 `~/.ssh/config` 등록 (접속 단축)

로컬 PC의 `~/.ssh/config`(Windows는 `C:\Users\<사용자>\.ssh\config`):

```text
Host myserver
    HostName <서버_IP>
    User coteleaf
    Port 22
    IdentityFile ~/.ssh/id_ed25519
```

접속 테스트:

```bash
local$ ssh myserver
```

> 원격 서버가 WSL2 안에 있고 아직 포트포워딩(10-2장)을 안 했다면, LAN의 다른 PC에서는 이 접속이 실패합니다. **같은 Windows 호스트**에서는 `localhost`로 접속되지만, **다른 로컬 PC**에서 접속하려면 10-2장 포워딩이 선행되어야 합니다.

### 6-4. 비밀번호 로그인 차단 (키 접속 확인 후)

키 접속이 확인되면 서버에서:

```bash
# (v3) sed 는 '해당 줄이 없으면' 아무것도 안 바꿉니다 → 껐다고 착각하지 않도록
#      "있으면 수정 / 없으면 추가(append)" 로 처리하고, 검증 후 실제 값을 확인합니다.
$ if grep -qE '^\s*#?\s*PasswordAuthentication' /etc/ssh/sshd_config; then
    sudo sed -i 's/^\s*#\?\s*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
  else
    echo 'PasswordAuthentication no' | sudo tee -a /etc/ssh/sshd_config
  fi
$ sudo sshd -t && sudo systemctl restart ssh          # 문법 검증 통과 시에만 재시작
$ sudo sshd -T | grep -i '^passwordauthentication'    # 반드시 'no' 여야 함(파일 아닌 실제 적용값)
```

> ⚠ 이 변경도 **기존 세션을 유지한 채** 새 창에서 키 접속이 되는지 확인한 뒤 원래 세션을 닫으세요. `sshd -T` 출력이 `passwordauthentication no`가 아니면 아직 패스워드 로그인이 열려 있는 것입니다(다른 곳의 중복 지시어·`Match` 블록 확인).

→ 검증(로컬): `verify_client.ps1 -RemoteHost <IP> -SshUser coteleaf -Check ssh`

---

## 7. GitHub 다중 계정 SSH 설정

coteleafdev / skygoldlee-cyber 두 계정을 한 서버에서 분리해 씁니다.

### 7-1. 계정별 키 생성

```bash
$ ssh-keygen -t ed25519 -C "coteleafdev"  -f ~/.ssh/id_ed25519_coteleafdev
$ ssh-keygen -t ed25519 -C "skygoldlee"   -f ~/.ssh/id_ed25519_skygoldlee
```

### 7-2. 공개키를 각 GitHub 계정에 등록

각 공개키 내용을 복사해 해당 GitHub 계정 → Settings → SSH and GPG keys → New SSH key 에 등록합니다.

```bash
$ cat ~/.ssh/id_ed25519_coteleafdev.pub    # → coteleafdev 계정에 등록
$ cat ~/.ssh/id_ed25519_skygoldlee.pub     # → skygoldlee-cyber 계정에 등록
```

### 7-3. `~/.ssh/config` 에 Host alias 정의

```text
# coteleafdev 계정
Host github.com-coteleafdev
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_coteleafdev
    IdentitiesOnly yes

# skygoldlee-cyber 계정
Host github.com-skygoldlee
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_skygoldlee
    IdentitiesOnly yes
```

```bash
$ chmod 600 ~/.ssh/config
```

### 7-4. 인증 테스트

```bash
$ ssh -T git@github.com-coteleafdev
$ ssh -T git@github.com-skygoldlee
```

각각 `Hi coteleafdev! ...`, `Hi skygoldlee-cyber! ...` 형태로 나오면 성공입니다.

### 7-5. 계정별 clone / 커밋 아이덴티티

호스트 alias로 clone하면 자동으로 올바른 키가 선택됩니다.

```bash
# coteleafdev 저장소
$ git clone git@github.com-coteleafdev:coteleafdev/<repo>.git
$ cd <repo>
$ git config user.name  "coteleafdev"
$ git config user.email "<coteleafdev 이메일>"

# skygoldlee-cyber 저장소
$ git clone git@github.com-skygoldlee:skygoldlee-cyber/<repo>.git
```

→ 검증: `./verify_server.sh github` (단일 계정만 쓰면 `github.com` 한 줄만 PASS, 나머지는 WARN이 정상)

---

## 8. Docker 설치

두 가지 방식이 있습니다. 현재 구성(Docker Desktop + WSL2)에는 **방식 A**가 가장 간단합니다.

### 8-A. Docker Desktop + WSL2 연동 (권장)

1. Windows에 **Docker Desktop**을 설치합니다.
2. Docker Desktop → Settings → **Resources → WSL Integration** → 사용 중인 배포판(Ubuntu-24.04) 토글을 켭니다.
3. Ubuntu 셸에서 `docker` 명령이 바로 동작합니다(별도 데몬 설치·systemd 불필요).

```bash
$ docker --version
$ docker compose version
$ docker run --rm hello-world
```

### 8-B. Ubuntu 내부에 docker-ce 직접 설치 (대안)

Docker Desktop을 쓰지 않을 때(순수 WSL 또는 물리 Ubuntu 서버):

```bash
# 공식 GPG 키 & 저장소
$ sudo install -m 0755 -d /etc/apt/keyrings
$ curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
$ sudo chmod a+r /etc/apt/keyrings/docker.gpg
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

# 엔진 설치
$ sudo apt update
$ sudo apt install -y docker-ce docker-ce-cli containerd.io \
                      docker-buildx-plugin docker-compose-plugin

# sudo 없이 실행 (재로그인 또는 newgrp 필요)
$ sudo usermod -aG docker $USER
$ newgrp docker

# (v3) 데몬 하드닝 — 데몬 재시작 중에도 컨테이너 유지(live-restore) + 전역 로그 상한 + 기본 보안
$ sudo mkdir -p /etc/docker
$ sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "live-restore": true,
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" },
  "no-new-privileges": true
}
EOF

# systemd 서비스로 상시 기동 (daemon.json 을 반영하도록 restart)
$ sudo systemctl enable --now docker
$ sudo systemctl restart docker
$ docker info --format '{{.LoggingDriver}} live-restore={{.LiveRestoreEnabled}}'   # json-file live-restore=true
$ docker run --rm hello-world
```

> `live-restore`는 **Swarm 모드가 아닐 때만** 유효합니다. `no-new-privileges`는 이 데몬이 띄우는 모든 컨테이너의 기본값을 "권한 상승 불가"로 잡습니다(컨테이너별 `security_opt`와 더해집니다). 이 설정은 **native Docker(8-B)/운영 서버**용입니다 — Docker Desktop(8-A)은 데몬 설정을 Desktop UI(Settings → Docker Engine)에서 같은 JSON으로 관리합니다.

→ 검증: `./verify_server.sh docker`

---

## 9. 서비스 스택 구성 — Nginx + FastAPI + PostgreSQL

Docker Compose로 세 서비스를 한 번에 관리합니다.

### 9-1. 프로젝트 디렉터리 구조

```text
~/projects/webstack/
├── docker-compose.yml
├── .env
├── nginx/
│   └── default.conf
└── api/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        └── main.py
```

```bash
$ mkdir -p ~/projects/webstack/{nginx,api/app} && cd ~/projects/webstack
```

### 9-2. `.env` (자격 증명)

```bash
$ cat > .env << 'EOF'
POSTGRES_USER=appuser
POSTGRES_PASSWORD=change_me_to_a_strong_secret
POSTGRES_DB=appdb
EOF
```

> `.env`는 절대 GitHub에 올리지 않습니다. 저장소 루트 `.gitignore`에 `.env`를 추가하세요.

> ⚠ **비밀번호에 URL 특수문자 주의.** `DATABASE_URL`은 `postgresql://user:password@host/db` 형태의 URL이라, `POSTGRES_PASSWORD`에 `@ : / ? # % &` 같은 문자가 들어가면 URL이 잘못 파싱되어 FastAPI가 DB 접속에 실패합니다. 해결은 둘 중 하나입니다. (a) 비밀번호를 **URL-safe 문자**(영문·숫자·`-_.~`)로만 생성하거나, (b) `main.py`에서 URL을 문자열로 조립하지 말고 부품에서 안전하게 만듭니다(특수문자 자동 인코딩):
>
> ```python
> import os
> from sqlalchemy import create_engine
> from sqlalchemy.engine import URL
> url = URL.create(
>     "postgresql+psycopg2",
>     username=os.environ["POSTGRES_USER"],
>     password=os.environ["POSTGRES_PASSWORD"],   # 특수문자 자동 인코딩
>     host="postgres", port=5432,
>     database=os.environ["POSTGRES_DB"],
> )
> engine = create_engine(url, pool_pre_ping=True)
> ```
>
> (b)를 쓰면 compose의 `DATABASE_URL` 환경변수 대신 `POSTGRES_*` 값을 그대로 넘기면 됩니다.

### 9-3. `docker-compose.yml`

```yaml
services:
  postgres:
    image: postgres:16
    container_name: postgres
    env_file: .env
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  fastapi:
    build: ./api
    container_name: fastapi
    env_file: .env
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "8000:8000"

  nginx:
    image: nginx:1.27
    container_name: nginx
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "80:80"
    depends_on:
      - fastapi

volumes:
  pgdata:
```

> `$${...}`는 컨테이너 내부에서 평가되도록 Compose가 `$`를 이스케이프하는 표기입니다. `${...}`(단일 `$`)는 `.env`에서 치환됩니다. container_name을 명시해 검증 스크립트의 이름 매칭(nginx/fastapi/postgres)과 일치시켰습니다.

### 9-3-1. 포트 노출 최소화 (권장 하드닝)

위 기본 예시는 이해를 돕기 위해 `fastapi(8000)`·`postgres(5432)`를 호스트 **모든 인터페이스(0.0.0.0)** 로 발행합니다. 하지만 이 웹스택에서 **손님이 직접 닿아야 하는 서비스는 접수처(Nginx :80)뿐**입니다. FastAPI·PostgreSQL은 같은 Compose 네트워크 안에서 컨테이너 이름(`fastapi`, `postgres`)으로만 통신하면 되므로, 호스트 포트로 열어 둘 필요가 없습니다. 열어 둔 포트는 곧 **LAN 전체에 노출되는 공격 표면**입니다(같은 공유기의 다른 기기·게스트가 DB에 직접 접속 시도 가능).

권장: 관리·검증용으로 포트가 필요하면 **루프백(`127.0.0.1`)에만** 바인딩합니다. 이러면 서버 자신(localhost)에서 도는 `verify_server.sh`·`curl`은 그대로 동작하고, 외부 노출만 사라집니다.

```yaml
  fastapi:
    ports:
      - "127.0.0.1:8000:8000"   # 서버 로컬 검증용. 외부/LAN 노출 없음
  postgres:
    ports:
      - "127.0.0.1:5432:5432"   # DB GUI·psql은 SSH 터널로만 접근
```

> 이렇게 바꾸면 **다른 로컬 PC**에서 `verify_client.ps1 -Check ports`의 8000 검사와 `-Check http`의 `:8000/docs` 검사는 (의도대로) 실패합니다. LAN에서 API를 굳이 검증하고 싶지 않다면 10-2장 방화벽/포트포워딩에서도 8000을 빼세요. FastAPI 응답 확인은 서버 안에서 `verify_server.sh fastapi`로, 또는 `ssh -L 8000:localhost:8000 …` 터널로 대체합니다. 이 정책은 이관 후 운영 서버의 포트 정책(런북 §7-1)과도 일치합니다.
>
> ⚠ **native Docker(8-B/운영 서버)에서는 이 루프백 바인딩이 특히 중요합니다.** 뒤(20-2·런북 §7-1)에서 다루듯, native Docker는 발행 포트를 **ufw보다 먼저** 처리하므로 `ufw deny 5432`만으로는 컨테이너 발행 포트가 막히지 않습니다. `127.0.0.1:` 바인딩이 가장 확실한 차단입니다.

### 9-4. FastAPI 애플리케이션

`api/requirements.txt`:

```text
fastapi
uvicorn[standard]
sqlalchemy
psycopg2-binary
```

`api/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
# (v3) 비루트 실행 — 컨테이너 탈출 취약점이 있어도 host root 로 이어지지 않도록
RUN useradd -u 10001 -r -s /usr/sbin/nologin appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

> (v3) 8000처럼 **1024 이상 포트**는 비루트로도 바인딩되므로 위 패턴이 그대로 동작합니다. compose 쪽에서는 `security_opt: ["no-new-privileges:true"]`와 `cap_drop: ["ALL"]`을 더해 완성합니다(부록 최종본 참고). 03 webstack 스캐폴드의 4개 서비스(gateway·worker·engine-analysis·engine-prescription) Dockerfile은 이미 이 비루트 패턴으로 맞춰 두었습니다.

`api/app/main.py`:

```python
import os
from fastapi import FastAPI
from sqlalchemy import create_engine, text

app = FastAPI(title="Webstack API")
engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)

@app.get("/")
def root():
    return {"status": "ok", "service": "fastapi"}

@app.get("/health/db")
def health_db():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"db": "ok"}
```

### 9-5. Nginx 리버스 프록시

`nginx/default.conf`:

```nginx
# (v3) http 컨텍스트 하드닝 — 버전 은닉 + API 레이트리밋 존 정의
server_tokens off;
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

server {
    listen 80;
    server_name _;

    # (v3) 보안 헤더 (HTTPS 적용 후 HSTS 주석 해제)
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;
    # add_header Strict-Transport-Security "max-age=31536000" always;

    location / {
        limit_req zone=api burst=20 nodelay;   # (v3) 폭주·스크래핑 완화
        proxy_pass         http://fastapi:8000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

> `proxy_pass`의 `fastapi`는 Compose 서비스명입니다. 같은 네트워크 안에서 컨테이너 이름으로 통신합니다.
>
> (v3) `server_tokens off`와 `limit_req_zone`은 **http 컨텍스트**(server 블록 바깥)에 있어야 합니다. 위처럼 파일 상단에 두면 이 파일이 `conf.d/`로 include될 때 http 컨텍스트로 들어갑니다. 03 webstack 스캐폴드는 표면이 www/dev/api 3개라, 같은 내용을 `conf.d/00-hardening.conf`(존·`server_tokens`)와 `snippets/security-headers.conf`(헤더)로 분리해 각 server가 공유하도록 해 두었습니다.

### 9-6. 스택 기동 및 확인

```bash
$ cd ~/projects/webstack
$ docker compose up -d --build
$ docker compose ps
$ docker compose logs -f fastapi     # 로그 확인 (Ctrl+C로 빠져나옴)
```

로컬(서버 내부)에서 응답 확인:

```bash
$ curl -s http://localhost/            # Nginx → FastAPI
$ curl -s http://localhost/health/db   # FastAPI → PostgreSQL
$ curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8000/docs
```

→ 검증: `./verify_server.sh services` (nginx+fastapi+postgres 한꺼번에)

정지·재시작:

```bash
$ docker compose stop        # 중지(데이터 유지)
$ docker compose down        # 컨테이너 제거(볼륨 pgdata는 유지)
$ docker compose down -v     # 볼륨까지 삭제(데이터 초기화 — 주의)
```

---

## 10. 외부에서 접속 가능한 서버 구성

### 10-1. 접근 범위 3단계

```text
① 같은 Windows 호스트 안       : localhost 로 바로 접근 (추가 설정 불필요)
② 같은 LAN의 다른 로컬 PC      : Windows 호스트 IP + 포트포워딩/방화벽 (10-2)
③ 인터넷(외부)                 : 공유기 포트포워딩 + DDNS + HTTPS + 보안 강화 (10-3)
```

### 10-2. WSL2 포트 포워딩 (기본 NAT 모드)

WSL2가 기본 NAT면 내부 IP를 쓰므로, 원격 Windows 호스트에서 포트를 WSL2로 넘겨줘야 LAN의 다른 PC가 접근할 수 있습니다. 원격 Windows **관리자 PowerShell**:

```powershell
# WSL2 IP 확인
PS> wsl hostname -I        # 예: 172.24.x.x

# 호스트 포트 → WSL2 포트 포워딩 (SSH 22, HTTP 80, API 8000)
PS> netsh interface portproxy add v4tov4 listenport=22   listenaddress=0.0.0.0 connectport=22   connectaddress=<WSL2_IP>
PS> netsh interface portproxy add v4tov4 listenport=80   listenaddress=0.0.0.0 connectport=80   connectaddress=<WSL2_IP>
PS> netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=<WSL2_IP>

# 등록 확인
PS> netsh interface portproxy show v4tov4

# 방화벽 인바운드 허용
PS> New-NetFirewallRule -DisplayName "WSL2 ports" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 22,80,8000
```

> WSL2 IP는 재부팅 시 바뀔 수 있습니다. 매번 갱신이 번거로우면 (a) `.wslconfig`에 `networkingMode=mirrored`를 켜 포트포워딩 자체를 없애거나, (b) 부팅 시 위 IP를 다시 읽어 portproxy를 갱신하는 스크립트를 작업 스케줄러에 등록합니다.

포워딩 제거(포트 변경/정리 시):

```powershell
PS> netsh interface portproxy delete v4tov4 listenport=80 listenaddress=0.0.0.0
```

### 10-3. 미러 네트워킹 모드 (대안, Win11 22H2+)

`.wslconfig`에 `networkingMode=mirrored`를 넣고 `wsl --shutdown` 후 재기동하면, WSL 서비스가 Windows 호스트 IP로 그대로 노출되어 **portproxy가 불필요**합니다. 이 경우에도 방화벽 인바운드 허용은 필요합니다.

### 10-4. 인터넷 노출 (선택, 보안 주의)

진짜 외부 공개가 필요할 때만:

- 공유기에서 WAN 포트 → 원격 Windows 호스트 IP:80(또는 443) 포트포워딩
- 고정 IP가 없으면 DDNS(무료 DDNS 서비스, 공유기 내장 DDNS) 사용
- **HTTPS 필수**: Nginx에 Let's Encrypt 인증서 적용(예: certbot 컨테이너 또는 Caddy로 대체)
- **보안 강화**: SSH는 키 인증 전용(비밀번호 차단, 6-4장) + 비표준 포트 + `fail2ban`, 최신 보안 업데이트 유지

> 인터넷 노출은 공격 표면이 크게 늘어납니다. 필요 최소한의 포트만 열고, 관리 포트(22/5432 등)는 외부에 직접 열지 않는 것을 강력히 권장합니다.

---

# 환경 검증 (구축 확인)

검증은 **두 지점**에서, 그리고 **각 구축 단계 직후 부분 실행 + 마지막 전체 실행**으로 진행합니다.

- **서버 측** `verify_server.sh` : 구성 요소 설치·기동 확인 (서버에서 실행)
- **로컬 측** `verify_client.ps1` : 내 PC에서 서버 도달성 확인 (로컬 PC에서 실행)
- **공통** `test_environment.py` (pytest) : 같은 기준을 로컬·서버 어디서나 반복/CI 실행

판정: `PASS`(정상) / `FAIL`(반드시 조치) / `WARN`(구성에 따라 무시 가능).
첨부 파일: `verify_server.sh`, `verify_client.ps1`, `test_environment.py`

## 11. 단계별 검증 절차 (Mermaid)

각 구축 단계를 마치는 즉시 해당 모듈만 부분 검증하고, `PASS`면 다음 단계로, `FAIL`이면 그 단계로 되돌아가 조치 후 재검증합니다.

```mermaid
flowchart TD
    Start([구축 시작]) --> S1["3장. Ubuntu 기본 설정"]
    S1 --> V1{{"서버: ./verify_server.sh base"}}
    V1 -- FAIL --> S1
    V1 -- PASS --> S5["5장. SSH 서버 설정"]

    S5 --> V5{{"서버: ./verify_server.sh ssh"}}
    V5 -- FAIL --> S5
    V5 -- PASS --> S6["6장. 로컬→서버 SSH 접속 + 포트포워딩(10-2)"]

    S6 --> V6{{"로컬: verify_client.ps1 -Check ssh"}}
    V6 -- FAIL --> S6
    V6 -- PASS --> S7["7장. GitHub SSH 키·프로젝트 연결"]

    S7 --> V7{{"서버: ./verify_server.sh github"}}
    V7 -- FAIL --> S7
    V7 -- PASS --> S8["8장. Docker 설치"]

    S8 --> V8{{"서버: ./verify_server.sh docker"}}
    V8 -- FAIL --> S8
    V8 -- PASS --> S9["9장. Nginx+FastAPI+PostgreSQL 스택"]

    S9 --> V9{{"서버: ./verify_server.sh services"}}
    V9 -- FAIL --> S9
    V9 -- PASS --> S10["10장. 외부 접속 구성 + 포트포워딩"]

    S10 --> V10{{"로컬: verify_client.ps1 (전체)"}}
    V10 -- FAIL --> S10
    V10 -- PASS --> VF{{"공통: pytest test_environment.py"}}

    VF -- FAIL --> Fix["실패 항목의 구축 단계로 복귀 후 해당 모듈 재검증"]
    VF -- PASS --> S20["20장. 하드닝(SSH·포트·컨테이너)"]

    S20 --> V20{{"서버: ./verify_server.sh hardening<br/>(+ 다른 PC: verify_client -Check ports)"}}
    V20 -- FAIL --> S20
    V20 -- PASS --> S18["18장. 백업 구성"]

    S18 --> V18{{"복구 리허설: 18-3 임시 DB 복원 성공"}}
    V18 -- FAIL --> S18
    V18 -- PASS --> S16["16장. 부팅 자동 기동 · 운영"]

    S16 --> V16{{"재부팅 후: verify_server all + verify_client<br/>(§21 운영 점검 13항목)"}}
    V16 -- FAIL --> S16
    V16 -- PASS --> Done([구축·하드닝·운영 검증 완료])
```

## 12. 서버 측 검증 — `verify_server.sh` (모듈형)

원격 서버(WSL2 Ubuntu) 안에서 실행합니다. 인자 없이 실행하면 전체(`all`), 모듈명을 주면 그 항목만 검사합니다.

```bash
$ chmod +x verify_server.sh
$ ./verify_server.sh            # 전체
$ ./verify_server.sh ssh        # SSH 서버만
$ ./verify_server.sh docker     # Docker 엔진만
$ ./verify_server.sh --help     # 모듈 목록
```

| 완료한 구축 단계 | 실행 명령 | 검사 내용 |
|---|---|---|
| 3장 기본 설정 | `./verify_server.sh base` | OS/WSL 커널, git/curl/wget/gcc/make, Python3/pip3 |
| 5장 SSH | `./verify_server.sh ssh` | sshd 실행, 22번 포트 LISTEN |
| 7장 GitHub | `./verify_server.sh github` | 계정별(coteleafdev/skygoldlee) SSH 인증 |
| 8장 Docker | `./verify_server.sh docker` | docker 데몬, docker compose |
| 9장 Nginx | `./verify_server.sh nginx` | nginx 컨테이너, :80 응답 |
| 9장 FastAPI | `./verify_server.sh fastapi` | fastapi 컨테이너, :8000/docs 응답 |
| 9장 PostgreSQL | `./verify_server.sh postgres` | postgres 컨테이너, :5432 |
| 9장 스택 묶음 | `./verify_server.sh services` | nginx+fastapi+postgres |
| 전체 | `./verify_server.sh all` | 위 모두 |

## 13. 로컬 PC 측 검증 — `verify_client.ps1` (모듈형)

내 PC(Windows)에서 실행해 원격 서버 도달성을 확인합니다. `-Check`로 항목을 좁힐 수 있습니다.

```powershell
# 전체
local$ powershell -ExecutionPolicy Bypass -File .\verify_client.ps1 -RemoteHost 192.168.0.50 -SshUser coteleaf
# SSH 접속만 (6장 직후)
local$ .\verify_client.ps1 -RemoteHost 192.168.0.50 -SshUser coteleaf -Check ssh
# HTTP 응답만 (10장 직후)
local$ .\verify_client.ps1 -RemoteHost 192.168.0.50 -Check http

# 이관 후(외부 호스팅·HTTPS) 서버 검증: -Mode prod (22/80/443 + https, 8000/5432 검사 제외)
local$ .\verify_client.ps1 -RemoteHost your.domain.com -SshUser ubuntu -Mode prod
```

| 완료한 구축 단계 | 실행 명령 | 검사 내용 |
|---|---|---|
| 6장 로컬 SSH 접속 | `-Check ssh` | SSH 키 로그인 |
| 6·10장 포트 개방 | `-Check ports` | 22/80/8000 TCP |
| 10장 외부 접속 | `-Check http` | Nginx/FastAPI HTTP 응답 |
| 네트워크 확인 | `-Check ping` | ICMP 도달성 |
| 전체 | `-Check all` (기본) | 위 모두 |

## 14. Python 통합 검증 — `test_environment.py` (부분 실행 지원)

같은 기준을 로컬·서버 어디서나 반복 실행하거나 CI(GitHub Actions 등)에 물릴 때 사용합니다. `-k`로 항목만 골라 실행합니다.

```bash
$ pip install pytest requests

# 전체 (localhost = 서버 자체)
$ pytest test_environment.py -v
# 로컬 → 원격 (SSH_USER 지정 시 SSH 로그인도 검사)
$ TARGET_HOST=192.168.0.50 SSH_USER=coteleaf pytest test_environment.py -v

# 부분 실행
$ pytest -k ssh        -v     # SSH 포트 + 로그인
$ pytest -k nginx      -v     # Nginx 포트 + 응답
$ pytest -k fastapi    -v     # FastAPI 포트 + /docs
$ pytest -k postgresql -v     # PostgreSQL 포트
```

Windows PowerShell:

```powershell
local$ $env:TARGET_HOST="192.168.0.50"; $env:SSH_USER="coteleaf"; pytest test_environment.py -v
```

## 15. 전체 검증 실행 순서 요약

```text
[각 단계 직후 — 부분 검증]
  3장 후  →  서버: ./verify_server.sh base
  5장 후  →  서버: ./verify_server.sh ssh
  6장 후  →  로컬: verify_client.ps1 -Check ssh   (+ 10-2 포트포워딩)
  7장 후  →  서버: ./verify_server.sh github
  8장 후  →  서버: ./verify_server.sh docker
  9장 후  →  서버: ./verify_server.sh services
  10장 후 →  로컬: verify_client.ps1 -Check http

[전체 마감 — 통합 검증]
  서버:  ./verify_server.sh all
  로컬:  verify_client.ps1 -RemoteHost <IP> -SshUser <user>
  공통:  pytest test_environment.py -v   (필요 시 TARGET_HOST 지정)

[하드닝·백업·운영 — 게이트(구축 마감 후 이어서)]
  20장 후 →  서버: ./verify_server.sh hardening   (+ 다른 PC: verify_client.ps1 -Check ports)
  18장 후 →  서버: 복구 리허설(18-3 임시 DB 복원 성공)
  16장 후 →  서버/로컬: ./verify_server.sh all + verify_client.ps1  (재부팅 자동복구)
  운영 정기 → verify_ops.sh  (§21 13항목 자동 점검)
```

- 모든 항목이 `PASS`(또는 구성상 무시 가능한 `WARN`만)이면 환경 구축이 검증된 것입니다.
- `FAIL`이 나오면 대응하는 구축 장(章)으로 돌아가 조치 후 해당 모듈만 재검증합니다.

---

# 운영 · 보안 · 배포 · 확장

구축·검증이 끝난 서버를 **계속 굴리기 위한** 파트입니다.

```text
A. 운영 안정성   16. 부팅 자동 기동   17. portproxy 자동 갱신   18. DB 백업·복구   19. 로그·헬스·모니터링
B. 보안          20. SSH 강화         21. 자동 보안 업데이트     22. HTTPS/TLS
C. 개발·배포     23. CI/CD            24. DB 마이그레이션·GUI    25. Makefile·템플릿
D. 확장          26. GPU 패스스루      27. 멀티 프로젝트 라우팅
부록. 운영 반영 최종 docker-compose.yml
```

> 핵심 원칙: **원격 PC가 재부팅되어도 서버가 스스로 살아나야 한다.** 지금 상태로는 재부팅 시 WSL·컨테이너·sshd·portproxy가 모두 내려갑니다. 16~17장이 이를 해결합니다.

> ⚠ **WSL 수명주기(반드시 이해).** WSL2 배포판은 **안에 실행 중인 프로세스가 없으면 약 60초 뒤 자동으로 종료**됩니다(`vmIdleTimeout`). 그런데 **Docker Desktop을 쓰면 컨테이너는 별도의 `docker-desktop` 배포판에서 돌기 때문에, 우리 `Ubuntu-24.04` 배포판은 그 컨테이너들이 떠 있어도 계속 살아 있지 않습니다.** 그 결과, Ubuntu 안에 설치한 **cron(18장 백업)·fail2ban(20장)·unattended-upgrades(21장)의 systemd 타이머**는 아무도 로그인하지 않고 Ubuntu에 상주 프로세스가 없으면 **예약 시각에 깨어나지 못해 조용히 건너뜁니다.** 대응:
>
> - **가장 확실한 방법**은 시간 기반 작업(백업·업데이트)을 **Windows 작업 스케줄러**로 트리거해 `wsl -d Ubuntu-24.04 …`로 그때그때 배포판을 깨우는 것입니다(18-2장 대안, 첨부 `wsl-backup-task.ps1`).
> - Ubuntu를 항상 띄워 두고 싶다면, 배포판 안에 **가벼운 상주 프로세스**(예: `systemd`가 관리하는 서비스, 또는 부팅 스크립트에서 `wsl … -e sh -c "tail -f /dev/null &"` 같은 keep-alive)를 두거나, `.wslconfig`에 `[wsl2] vmIdleTimeout=-1`(무한)을 설정합니다. 다만 상시 가동은 그만큼 리소스를 계속 점유합니다.
> - **native Docker(8-B) 조합**에서는 컨테이너가 곧 Ubuntu 배포판 안에서 돌므로 이 문제가 없습니다. 외부 운영 서버로 이관하는 경우(런북)나 **Vercel + Render + Supabase 관리형 인프라**로 이전한 환경에서도 상시 구동 및 관리가 보장되므로 애초에 해당 없음입니다.

## 15-A. (v3) 위험 변경 전 전체 스냅샷 (WSL 롤백 안전판)

커널·systemd·Docker 데몬(8-B·§16·§21)처럼 **되돌리기 어려운 변경 전에는**, WSL 배포판을 통째로 내보내 두면 한 줄로 롤백할 수 있습니다. 개별 백업(18장 DB)과 달리 **OS 상태 전체**를 저장하는 안전판입니다.

```powershell
# 스냅샷(내보내기) — Windows(관리자 아님도 가능), 배포판은 잠깐 멈췄다 재개됨
PS> mkdir D:\wsl-backups 2>$null
PS> wsl --export Ubuntu-24.04 D:\wsl-backups\ubuntu_$(Get-Date -Format yyyyMMdd_HHmmss).tar

# 되돌리기(복원) — 별도 이름으로 가져와 확인 후 전환
PS> wsl --import Ubuntu-24.04-restore D:\wsl\restore D:\wsl-backups\ubuntu_YYYYMMDD_HHMMSS.tar
#   확인 후 원본을 대체하려면: 원본 unregister → restore 를 재-import 하거나 그대로 사용
```

> `.tar`는 배포판 전체라 수 GB가 될 수 있으니 **호스트의 다른 디스크(D:)** 나 외장에 두세요(WSL 볼륨과 같은 물리 디스크에 두면 디스크 장애 시 동반 소실). 큰 변경 직전에 1개만 떠 두어도 롤백 비용이 크게 줄어듭니다. 이 스냅샷은 §16(부팅 자동화)·§21(자동 업데이트)처럼 **데몬/커널을 건드리는 절차 앞**에서 특히 유용합니다.

## 16. 부팅 자동 기동

재부팅 후 사람이 로그인하지 않아도 서비스가 뜨도록 세 겹으로 잡습니다.

### 16-1. Docker Desktop 자동 시작 + 컨테이너 재시작 정책

- Docker Desktop → Settings → General → **"Start Docker Desktop when you log in"** 체크.
- Compose의 각 서비스에 재시작 정책을 추가합니다(9-3장 파일 수정, 최종본은 부록 참고).

```yaml
    restart: unless-stopped
```

이러면 컨테이너가 죽거나 데몬이 재시작돼도 자동 복구됩니다(`docker compose down`으로 명시적으로 내린 경우는 제외).

### 16-2. WSL·sshd 부팅 + portproxy 갱신 스크립트

원격 Windows에 아래 스크립트를 저장합니다(예: `C:\ops\wsl-server-boot.ps1`). WSL을 깨우고(→ systemd가 sshd 기동), 현재 WSL IP로 portproxy를 다시 설정합니다.

```powershell
# wsl-server-boot.ps1  — 부팅 시 1회 실행
$distro = "Ubuntu-24.04"
$ports  = @(22, 80, 8000)

# 1) WSL 부팅 (systemd 활성화 시 enable 된 ssh가 함께 뜸)
#    (v3) 절전/최대절전 복귀 후 시계 드리프트 보정: hwclock -s 로 하드웨어 시계와 재동기화
wsl -d $distro -u root -e sh -c "hwclock -s 2>/dev/null; service ssh start 2>/dev/null; true" | Out-Null

# 2) 현재 WSL2 IP
$ip = (wsl -d $distro hostname -I).Trim().Split(" ")[0]
if (-not $ip) { Write-Error "WSL IP 확인 실패"; exit 1 }

# 3) portproxy 재설정 (미러 네트워킹 모드면 이 블록 불필요)
foreach ($p in $ports) {
  netsh interface portproxy delete v4tov4 listenport=$p listenaddress=0.0.0.0 2>$null | Out-Null
  netsh interface portproxy add    v4tov4 listenport=$p listenaddress=0.0.0.0 connectport=$p connectaddress=$ip
}
netsh interface portproxy show v4tov4
```

### 16-3. 작업 스케줄러 등록

관리자 PowerShell에서 로그온 시(또는 시스템 시작 시) 실행되도록 등록합니다.

```powershell
PS> schtasks /Create /TN "WSL Server Boot" `
      /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\ops\wsl-server-boot.ps1" `
      /SC ONLOGON /RL HIGHEST /F
```

> 로그인 없이 상시 운영하려면 Windows 자체를 자동 로그인 설정하거나, `/SC ONSTART`로 바꿉니다. 다만 ONSTART는 Docker Desktop(사용자 세션 필요)보다 먼저 실행될 수 있으니, 네이티브 docker(8-B) 조합에서 더 안정적입니다.

## 17. portproxy 자동 갱신 (요약)

16-2 스크립트가 WSL2 IP 변동 문제를 매 부팅마다 해결합니다. 부팅 외에 수동 갱신이 필요할 때:

```powershell
PS> powershell -ExecutionPolicy Bypass -File C:\ops\wsl-server-boot.ps1
```

미러 네트워킹(`networkingMode=mirrored`)을 쓰면 IP가 Windows와 동일해 portproxy 자체가 필요 없어지므로, 재부팅 대응이 가장 단순합니다.

## 18. PostgreSQL 백업·복구 자동화

### 18-1. 백업 스크립트

Ubuntu에 `~/scripts/pg_backup.sh`:

첨부 `pg_backup.sh`를 그대로 쓰면 됩니다. **DB 계정·이름은 하드코딩하지 않고 `.env`에서 읽어** 오탈자·설정 변경에 강합니다(migrate 스크립트와 동일한 안전 파서 사용).

```bash
#!/usr/bin/env bash
set -euo pipefail
umask 077                                   # 덤프(민감 데이터)를 0600 으로 생성

PROJECT_DIR="${PROJECT_DIR:-$HOME/projects/webstack}"
PG_CONTAINER="${PG_CONTAINER:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
RETAIN_DAYS="${RETAIN_DAYS:-14}"
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
if docker exec "$PG_CONTAINER" pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > "$TMP"; then
  mv "$TMP" "$BACKUP_DIR/${POSTGRES_DB}_$STAMP.dump"
else
  rm -f "$TMP"; echo "ERROR: pg_dump 실패 (컨테이너 기동/계정 확인)"; exit 1
fi

# 보관기간 초과분 삭제
find "$BACKUP_DIR" -name "${POSTGRES_DB}_*.dump" -mtime +"$RETAIN_DAYS" -delete
echo "[$(date '+%F %T')] backup done: ${POSTGRES_DB}_$STAMP.dump"
```

> 원래 예시는 `appuser`/`appdb`를 하드코딩해, `.env` 값을 바꾸면 백업이 조용히 엉뚱한(또는 없는) DB를 덤프할 위험이 있었습니다. 위 버전은 `.env`를 단일 진실원본으로 삼고, **덤프가 성공해야만 최종 파일로 커밋**해 0바이트 백업이 남지 않게 합니다.

> ⚠ **(v3) 실전 견고성 4가지 — PIPA 맥락(피부 이미지·분석 결과 포함 덤프)에서 특히 중요.** 첨부 `pg_backup.sh`는 아래를 **모두 환경변수로 켜는 선택 기능**으로 넣어 두었습니다(설정 안 하면 기존 동작 그대로).
>
> 1. **오프사이트 복제** — 백업이 DB와 **같은 WSL 디스크**에만 있으면 디스크 장애 시 동반 소실됩니다. `OFFSITE_DIR=/mnt/d/wsl-backups`처럼 Windows 쪽(또는 외장)으로 복사본을 하나 더 둡니다.
> 2. **저장 시 암호화** — 덤프는 평문입니다. `BACKUP_GPG_RCPT=backup@yourco`(공개키) 또는 `BACKUP_ENC_PASSFILE=~/.pgenc`(openssl AES-256)로 **암호화 후 원본 평문 삭제**합니다.
> 3. **최소 보존 하한** — 시간기반 삭제(`-mtime`)만 두면 백업이 며칠 멈춘 사이 마지막 정상본까지 지워집니다. `MIN_KEEP=3`으로 **최근 N개는 나이와 무관하게 남깁니다.**
> 4. **데드맨 스위치** — 실패해도 아무도 로그를 안 봅니다. `HEALTHCHECK_URL=https://hc-ping.com/<uuid>`를 주면 **성공했을 때만 핑**을 보내고, 핑이 안 오면 외부 서비스가 알림을 줍니다(18-2-1의 idle 누락과 짝을 이룸).
>
> ```bash
> # 예: cron/작업 스케줄러가 넘길 환경변수 (하나도 안 줘도 동작)
> OFFSITE_DIR=/mnt/d/wsl-backups \
> BACKUP_GPG_RCPT=backup@yourco \
> MIN_KEEP=3 \
> HEALTHCHECK_URL=https://hc-ping.com/xxxxxxxx \
> ~/scripts/pg_backup.sh
> ```

```bash
$ chmod +x ~/scripts/pg_backup.sh
$ ~/scripts/pg_backup.sh        # 수동 실행 테스트
```

### 18-2. 정기 실행 (cron)

```bash
$ sudo systemctl enable --now cron
$ crontab -e
```

```text
# 매일 03:00 백업 (WSL이 떠 있는 동안만 동작)
0 3 * * * /home/coteleaf/scripts/pg_backup.sh >> /home/coteleaf/backups/backup.log 2>&1
```

> ⚠ **WSL에서 cron만 믿으면 백업이 안 될 수 있습니다.** 위 "WSL 수명주기" 경고대로, 새벽 03:00에 Ubuntu 배포판이 idle로 종료돼 있으면 cron 자체가 깨어나지 못해 백업이 **조용히 누락**됩니다. (Docker Desktop 조합에서 특히 그렇습니다 — 컨테이너는 `docker-desktop` 배포판에 있어 Ubuntu를 깨워 두지 않습니다.)

### 18-2-1. (권장) Windows 작업 스케줄러로 백업 트리거

시간이 되면 **Windows가 WSL을 깨워** 백업을 돌리게 하면 idle 종료와 무관하게 안정적입니다. 첨부 `wsl-backup-task.ps1`를 `C:\ops\`에 두고 등록합니다.

```powershell
# wsl-backup-task.ps1 — Windows가 WSL을 깨워 컨테이너 확인 후 백업 실행
$distro = "Ubuntu-24.04"
# 1) 배포판을 깨우고 docker/컨테이너가 준비될 때까지 잠깐 대기(Desktop 자동시작과 경합 방지)
wsl -d $distro -e sh -c "for i in `$(seq 1 30); do docker ps >/dev/null 2>&1 && break; sleep 2; done"
# 2) 로그인 셸로 실행해 PATH·docker 컨텍스트를 정상 로드
wsl -d $distro -u coteleaf -e bash -lc "~/scripts/pg_backup.sh >> ~/backups/backup.log 2>&1"
```

```powershell
# 매일 03:00 실행 등록 (관리자 PowerShell)
PS> schtasks /Create /TN "WSL PG Backup" `
      /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\ops\wsl-backup-task.ps1" `
      /SC DAILY /ST 03:00 /RL HIGHEST /F
```

> 이렇게 하면 cron 등록(18-2)은 생략하거나, "WSL이 이미 떠 있을 때"용 보조로만 남겨도 됩니다. **백업은 만든 뒤 반드시 복구 리허설(18-3)로 실제 복원 가능함을 확인**해야 진짜 백업입니다 — 열리지 않는 덤프는 백업이 아닙니다.

### 18-3. 복구 및 리허설

```bash
# 특정 백업으로 복구 (스키마/데이터 정리 후 복원)
$ docker exec -i postgres pg_restore -U appuser -d appdb --clean --if-exists < ~/backups/appdb_YYYYMMDD_HHMMSS.dump

# 복구 리허설: 임시 DB에 복원해 무결성만 확인
$ docker exec -it postgres createdb -U appuser restore_test
$ docker exec -i  postgres pg_restore -U appuser -d restore_test < ~/backups/appdb_XXXX.dump
$ docker exec -it postgres dropdb   -U appuser restore_test
```

> 볼륨 자체 백업이 필요하면 `pgdata` 볼륨을 tar로 떠둘 수 있습니다: `docker run --rm -v webstack_pgdata:/v -v $PWD:/b alpine tar czf /b/pgdata.tgz -C /v .`

## 19. 로그 로테이션 · 헬스체크 · 모니터링

### 19-1. 로그 로테이션 (디스크 폭주 방지)

각 서비스에 로깅 옵션을 추가합니다(부록 최종본에 반영).

```yaml
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

### 19-2. 헬스체크 확대

postgres 외 fastapi·nginx에도 헬스체크를 넣어 자동 복구·상태 판별을 돕습니다.

```yaml
  fastapi:
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/').status==200 else 1)\""]
      interval: 15s
      timeout: 5s
      retries: 5
```

### 19-3. 업타임 모니터링 (Uptime Kuma)

브라우저 대시보드로 각 엔드포인트를 감시하고, 다운 시 알림(텔레그램/이메일/웹훅)을 받습니다.

```yaml
  uptime-kuma:
    image: louislam/uptime-kuma:1
    container_name: uptime-kuma
    volumes:
      - uptime-kuma:/app/data
    ports:
      - "3001:3001"
    restart: unless-stopped
```

`http://<서버>:3001` 접속 → 모니터 추가(`http://nginx`, `http://fastapi:8000/`, TCP `postgres:5432`).

---

## 20. SSH 강화 (fail2ban · ufw · 비표준 포트)

### 20-1. fail2ban (무차별 로그인 차단)

```bash
$ sudo apt install -y fail2ban
$ sudo tee /etc/fail2ban/jail.local >/dev/null <<'EOF'
[sshd]
enabled  = true
port     = 22
maxretry = 5
findtime = 10m
bantime  = 1h
EOF
$ sudo systemctl enable --now fail2ban
$ sudo fail2ban-client status sshd
```

> ⚠ **WSL NAT 모드에서 fail2ban의 원본 IP 주의.** 기본 NAT + portproxy 경로에서는 sshd가 보는 접속 원본이 **공격자 IP가 아니라 Windows 호스트/WSL 게이트웨이 IP**로 보일 수 있습니다. 이 경우 fail2ban이 게이트웨이를 차단해 **정상 접속까지 막거나, 반대로 실효 없는 차단**이 됩니다. 미러 네트워킹(`networkingMode=mirrored`, 2-1장)이나 native 서버에서는 원본 IP가 보존되어 정상 동작합니다. WSL NAT에서 무차별 로그인 방어가 정말 필요하면 **Windows 방화벽 쪽에서** 관리 포트를 최소화/제한하는 편이 더 확실합니다.

### 20-2. ufw (2차 방어선)

```bash
$ sudo apt install -y ufw
$ sudo ufw default deny incoming
$ sudo ufw default allow outgoing
$ sudo ufw allow 22/tcp
$ sudo ufw allow 80/tcp
$ sudo ufw enable
$ sudo ufw status verbose
```

> WSL2에서는 실제 외부 경계가 **Windows 방화벽 + portproxy**입니다. ufw는 컨테이너/내부 트래픽에 대한 2차 방어로 보고, 1차는 Windows 쪽에서 최소 포트만 여는 것을 원칙으로 하세요.
>
> ⚠ **중요 — ufw는 Docker 발행 포트를 막지 못합니다.** native Docker(8-B/운영 서버)는 iptables의 `DOCKER`/`nat` 체인에 규칙을 넣어, `-p 5432:5432`처럼 발행한 컨테이너 포트를 **ufw의 INPUT 규칙보다 먼저** 통과시킵니다. 따라서 `ufw deny 5432`를 걸어도 해당 포트는 외부에서 그대로 열려 있습니다. 확실한 차단은 다음 중 하나입니다. ⑴ compose에서 **`127.0.0.1:`로만 바인딩**(9-3-1장, 가장 간단·확실), ⑵ 클라우드 **보안그룹**으로 host 밖에서 차단(런북 §7-1), ⑶ `DOCKER-USER` 체인에 직접 규칙 추가 또는 `ufw-docker` 사용. 운영 서버의 DB·관리 포트(5432/8080/3001)는 **반드시 이 중 하나로** 막으세요 — ufw 규칙만으로는 뚫려 있습니다.

### 20-3. 비표준 포트

`/etc/ssh/sshd_config`의 `Port`를 예: `2222`로 바꾸고, portproxy(16-2)의 `$ports`와 로컬 `~/.ssh/config`의 `Port`도 함께 변경합니다. 봇 스캔 노이즈를 크게 줄입니다.

## 21. 자동 보안 업데이트 (unattended-upgrades)

```bash
$ sudo apt install -y unattended-upgrades
$ sudo dpkg-reconfigure -plow unattended-upgrades      # 대화형: Yes
```

`/etc/apt/apt.conf.d/20auto-upgrades` 확인/작성:

```text
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
```

동작 확인(모의 실행):

```bash
$ sudo unattended-upgrade --dry-run --debug
```

> systemd의 `apt-daily.timer`가 트리거하므로, WSL이 상시 떠 있는(16장) 환경에서 정상 동작합니다. 다만 이는 **userland 패키지(라이브러리·데몬)** 갱신입니다. WSL2 커널은 apt가 아니라 Windows 쪽(`microsoft-standard-WSL2`, `wsl --update`)에서 오므로, 여기서 커널이 바뀌지는 않습니다. 중요한 라이브러리 패치 후에는 관련 컨테이너/서비스 재기동(필요 시 `wsl --shutdown`)으로 반영을 확실히 하세요. 커널 자체 업데이트는 별도로 `wsl --update`를 씁니다.

### 21-1. (v3) 재부팅 정책 명시

`unattended-upgrades`의 재부팅 기본값은 꺼짐(`false`)입니다. 그대로 두면 커널·라이브러리 갱신 후 반영이 애매하고, 반대로 **native 운영 서버에서 무심코 켜면 새벽에 서비스가 끊깁니다.** 정책을 명시적으로 정하세요.

```bash
$ sudo sed -i \
  -e 's#^//\?Unattended-Upgrade::Automatic-Reboot .*#Unattended-Upgrade::Automatic-Reboot "false";#' \
  -e 's#^//\?Unattended-Upgrade::Automatic-Reboot-Time .*#Unattended-Upgrade::Automatic-Reboot-Time "04:00";#' \
  /etc/apt/apt.conf.d/50unattended-upgrades
$ grep -E 'Automatic-Reboot' /etc/apt/apt.conf.d/50unattended-upgrades
```

> - **WSL(본 가이드 주 시나리오):** 자동 재부팅은 **끄기(`false`)** 를 권합니다. 커널은 어차피 apt가 아니라 `wsl --update`에서 오고, 재부팅이 필요한 라이브러리 갱신은 위 "WSL 수명주기"상 사람이 `wsl --shutdown`으로 반영하는 편이 예측 가능합니다.
> - **native 운영 서버(런북):** 자동 재부팅이 필요하면 **트래픽이 적은 시간(예: `04:00`)** 으로 못박으세요. 재부팅이 서비스 중단을 뜻하므로, 무인 재부팅을 켤지 여부 자체를 운영 정책으로 결정합니다.

### 21-2. (v3) journald 로그 상한

WSL+systemd에서 journald가 무한정 커질 수 있습니다. 디스크 폭주를 막게 상한을 둡니다(도커 로그는 이미 19장/`daemon.json`에서 `max-size`로 제한).

```bash
$ sudo sed -i 's/^#\?SystemMaxUse=.*/SystemMaxUse=200M/' /etc/systemd/journald.conf
$ grep -q '^SystemMaxUse=' /etc/systemd/journald.conf || echo 'SystemMaxUse=200M' | sudo tee -a /etc/systemd/journald.conf
$ sudo systemctl restart systemd-journald
$ journalctl --disk-usage
```

## 22. HTTPS / TLS

공개 도메인과 80/443 외부 도달이 전제입니다(10-4장). 가장 간단한 방법은 **Caddy**(자동 인증서 발급·갱신)입니다.

### 22-A. Caddy로 프런트 교체 (권장)

`caddy/Caddyfile`:

```text
your.domain.com {
    reverse_proxy fastapi:8000
}
```

Compose 서비스(nginx 대신, 또는 앞단에):

```yaml
  caddy:
    image: caddy:2
    container_name: caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - fastapi
    restart: unless-stopped
```

도메인만 맞으면 Let's Encrypt 인증서를 자동 발급·갱신합니다.

> ⚠ **프런트 프록시는 하나만.** 부록의 최종 `docker-compose.yml`에는 `nginx` 서비스가 `80:80`을 물고 있습니다. 여기에 Caddy(`80:80`/`443:443`)를 그대로 추가하면 **80 포트 충돌**로 한쪽이 기동에 실패합니다. Caddy를 프런트로 쓰기로 했다면 부록 compose에서 **`nginx` 서비스를 제거**(Caddy가 `fastapi:8000`으로 직접 리버스 프록시)하거나, Nginx를 유지하려면 Caddy 없이 22-B(certbot)로 가세요. 멀티 프로젝트(27장)에서 Nginx를 내부 라우터로 남기고 싶다면 Nginx의 `ports`에서 `80:80`을 빼 **외부 노출은 Caddy만** 담당하게 합니다.

### 22-B. Nginx + certbot (대안)

기존 Nginx를 유지하려면 certbot으로 인증서를 발급하고 443 server 블록에 적용합니다. Caddy보다 설정이 많으므로, 위 Caddy를 우선 검토하고 세부가 필요하면 별도로 구성합니다.

---

## 23. CI/CD — GitHub Actions

푸시하면 자동으로 빌드·테스트 후 서버에 배포합니다. **서버 도달 방식**에 따라 두 패턴이 있습니다.

### 23-1. self-hosted runner (LAN 서버에 권장)

서버가 인터넷에 노출돼 있지 않으면, 서버 자체를 러너로 등록하는 방식이 안전합니다. GitHub 저장소 → Settings → Actions → Runners → New self-hosted runner 안내대로 Ubuntu에 러너를 설치합니다.

`.github/workflows/deploy.yml`:

```yaml
name: deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r api/requirements.txt pytest
      - run: pytest -q            # 앱 단위 테스트

  deploy:
    needs: test
    runs-on: self-hosted         # 서버에 등록한 러너에서 실행
    steps:
      - uses: actions/checkout@v4
      - run: docker compose up -d --build
      - run: ./verify_server.sh services
```

### 23-2. SSH 배포 (인터넷 도달 서버)

서버가 외부에서 SSH로 닿을 때. 저장소 Secrets에 `SSH_HOST`, `SSH_USER`, `SSH_KEY`(개인키)를 등록합니다.

```yaml
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: SSH & deploy
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd ~/projects/webstack
            git pull
            docker compose up -d --build
```

> LAN 전용 서버에 23-2를 쓰려면 인터넷 노출(10-4)이 필요합니다. 노출을 늘리기 싫으면 23-1(self-hosted)이 정석입니다.

## 24. DB 마이그레이션(Alembic) + GUI(adminer)

### 24-1. Alembic (스키마 버전관리)

`api/requirements.txt`에 `alembic` 추가 후:

```bash
$ cd ~/projects/webstack/api
$ alembic init alembic
```

`alembic/env.py`에서 URL을 환경변수로 연결:

```python
import os
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
```

마이그레이션 생성·적용(컨테이너 안에서 실행):

```bash
$ docker compose exec fastapi alembic revision --autogenerate -m "init"
$ docker compose exec fastapi alembic upgrade head
```

### 24-2. adminer (브라우저 DB 콘솔)

```yaml
  adminer:
    image: adminer
    container_name: adminer
    ports:
      - "8080:8080"
    depends_on:
      - postgres
    restart: unless-stopped
```

`http://<서버>:8080` → System: PostgreSQL, Server: `postgres`, 계정은 `.env` 값.

> adminer/uptime-kuma 같은 관리 포트(8080/3001)는 **외부에 직접 열지 말고** LAN·VPN·SSH 터널로만 접근하는 것을 권장합니다.

## 25. Makefile + 표준 템플릿

### 25-1. Makefile (반복 명령 단축)

프로젝트 루트 `Makefile` (들여쓰기는 **반드시 탭**):

```make
.PHONY: up down logs ps backup restore test verify

up:      ; docker compose up -d --build
down:    ; docker compose down
logs:    ; docker compose logs -f
ps:      ; docker compose ps
backup:  ; ~/scripts/pg_backup.sh
test:    ; pytest test_environment.py -v
verify:  ; ./verify_server.sh all
```

```bash
$ make up
$ make verify
```

### 25-2. `.gitignore`

```text
.env
.venv/
__pycache__/
*.pyc
backups/
caddy_data/
```

### 25-3. `.dockerignore` (빌드 컨텍스트 축소)

```text
.git
.venv
__pycache__
*.pyc
backups
.env
```

---

## 26. GPU(CUDA) 패스스루

이 박스에서 영상 분석·딥러닝 학습/추론을 돌릴 경우, WSL2는 Windows NVIDIA 드라이버 기반 CUDA를 지원합니다.

### 26-1. 전제 및 주의

- **Windows에 최신 NVIDIA 드라이버**만 설치합니다.
- **WSL 내부(Ubuntu)에는 리눅스 NVIDIA 드라이버를 설치하지 않습니다.** (CUDA 툴킷 라이브러리는 가능하나 드라이버는 금지 — 충돌 원인)

인식 확인:

```bash
$ nvidia-smi          # WSL Ubuntu에서 GPU가 보이면 OK
```

### 26-2. NVIDIA Container Toolkit (컨테이너에서 GPU 사용)

```bash
$ curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /etc/apt/keyrings/nvidia-container-toolkit-keyring.gpg
$ curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/etc/apt/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
$ sudo apt update && sudo apt install -y nvidia-container-toolkit
$ sudo nvidia-ctk runtime configure --runtime=docker
# 네이티브 docker면: sudo systemctl restart docker  (Docker Desktop이면 자동)

# 검증
$ docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

### 26-3. Compose에서 GPU 할당

```yaml
  fastapi:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

> 최신 Compose에서는 서비스에 `gpus: all` 한 줄로도 지정할 수 있습니다.

## 27. 멀티 프로젝트 라우팅

한 서버에서 여러 스택을 운영할 때, 프런트 프록시 하나가 도메인별로 각 프로젝트로 분기합니다.

### 27-1. 공유 네트워크

```bash
$ docker network create web
```

각 프로젝트 compose에서 이 네트워크를 external로 참여시키고, 프런트 프록시가 컨테이너 이름으로 프록시합니다.

### 27-2. 도메인 기반 분기 (Nginx 예)

```nginx
server {
    listen 80;
    server_name app1.example.com;
    location / { proxy_pass http://app1_fastapi:8000; }
}
server {
    listen 80;
    server_name app2.example.com;
    location / { proxy_pass http://app2_fastapi:8000; }
}
```

- 도메인이 없으면 로컬 `hosts` 파일(`app1.local` 등)로 테스트하거나, **경로 기반**(`/app1`, `/app2`) 또는 **포트 기반** 분리를 씁니다.
- Caddy를 프런트로 쓰면 도메인별 HTTPS까지 자동 처리되어 멀티 프로젝트에 특히 편합니다.

---

## 부록. 운영 반영 최종 `docker-compose.yml`

16·19·24장을 반영한 상태입니다(재시작 정책·로그 로테이션·헬스체크·adminer·uptime-kuma 포함). GPU가 필요하면 26-3 블록을 `fastapi`에 추가합니다.

> **(v3) 컨테이너 하드닝 반영.** 자체 빌드 서비스(`fastapi`)에는 `security_opt: ["no-new-privileges:true"]` + `cap_drop: ["ALL"]`을, 공식 이미지(`postgres`·`nginx`·`adminer`·`uptime-kuma`)에는 `no-new-privileges`만 적용했습니다(공식 이미지의 entrypoint·포트 바인딩이 capability를 필요로 해 `cap_drop: ALL`은 생략). 아울러 각 서비스에 **메모리/CPU 상한**을 두어, 한 컨테이너의 OOM/폭주가 host 전체를 잠식하지 못하게 했습니다 — 값은 예시이므로 **ML·엔진 워크로드는 실제 모델 크기에 맞춰 상향**하세요. `fastapi`의 Dockerfile은 9-4장처럼 **비루트 USER**로 실행하는 것을 전제로 합니다.

> 이 최종본은 **9-3-1 하드닝(포트 노출 최소화)을 적용**했습니다: 손님이 직접 닿아야 하는 `nginx(:80)`만 `0.0.0.0`으로 열고, `fastapi`·`postgres`·`adminer`·`uptime-kuma`는 **`127.0.0.1`에만** 바인딩합니다. 이들 관리·내부 포트는 서버 로컬 검증과 **SSH 터널**(`ssh -L 8080:localhost:8080 …`)로만 접근합니다. native Docker에서 ufw가 발행 포트를 막지 못하는 문제(20-2)를 근본적으로 회피합니다. LAN의 다른 PC에서 API/DB를 직접 검증해야 하는 개발 편의가 필요하면 해당 포트만 `0.0.0.0`으로 되돌리되, 그 노출 위험을 감수하는 선택임을 인지하세요.

```yaml
services:
  postgres:
    image: postgres:16
    container_name: postgres
    env_file: .env
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432"   # 하드닝: 루프백 전용 (SSH 터널/서버 로컬만)
    security_opt: ["no-new-privileges:true"]   # (v3) 공식 이미지: cap_drop ALL 은 entrypoint 를 깨뜨릴 수 있어 생략
    mem_limit: 1g                              # (v3)
    cpus: "1.0"                                # (v3)
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "3" }
    restart: unless-stopped

  fastapi:
    build: ./api
    container_name: fastapi
    env_file: .env
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "127.0.0.1:8000:8000"   # 하드닝: 루프백 전용 (Nginx가 컨테이너망으로 프록시)
    security_opt: ["no-new-privileges:true"]   # (v3) 권한 상승 차단 (Dockerfile 은 비루트 USER)
    cap_drop: ["ALL"]                          # (v3) 불필요 capability 제거 (8000>1024, 바인딩 cap 불필요)
    mem_limit: 1g                              # (v3) OOM 폭주가 host 를 잠식하지 않도록 (ML 워크로드는 상향)
    cpus: "1.5"                                # (v3)
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/').status==200 else 1)\""]
      interval: 15s
      timeout: 5s
      retries: 5
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "3" }
    restart: unless-stopped

  nginx:
    image: nginx:1.27
    container_name: nginx
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "80:80"
    depends_on:
      - fastapi
    security_opt: ["no-new-privileges:true"]   # (v3) 공식 이미지(80 바인딩에 cap 필요) → cap_drop ALL 은 생략
    mem_limit: 256m                            # (v3)
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "3" }
    restart: unless-stopped

  adminer:
    image: adminer
    container_name: adminer
    ports:
      - "127.0.0.1:8080:8080"   # 하드닝: 루프백 전용 (SSH 터널로만 접근)
    depends_on:
      - postgres
    security_opt: ["no-new-privileges:true"]   # (v3)
    mem_limit: 256m                            # (v3)
    restart: unless-stopped

  uptime-kuma:
    image: louislam/uptime-kuma:1
    container_name: uptime-kuma
    volumes:
      - uptime-kuma:/app/data
    ports:
      - "127.0.0.1:3001:3001"   # 하드닝: 루프백 전용 (SSH 터널로만 접근)
    security_opt: ["no-new-privileges:true"]   # (v3)
    mem_limit: 512m                            # (v3)
    restart: unless-stopped

volumes:
  pgdata:
  uptime-kuma:
```

## 부록 B. 운영 점검 체크리스트

정기적으로(또는 재부팅 후) 아래를 확인합니다. 아래 목록은 `verify_ops.sh` 로 자동 점검할 수 있고(복구·백업 신선도·리소스·갱신), 보안 항목까지 함께 보려면 `./verify_ops.sh --with-hardening` 또는 `./verify_server.sh hardening` 을 씁니다.

```text
[ ] 재부팅 후 자동 복구        : ./verify_server.sh all  +  로컬 verify_client.ps1 통과
[ ] portproxy 최신 IP 반영      : netsh interface portproxy show v4tov4
[ ] 백업 생성 여부              : ls -lh ~/backups  (최근 파일 존재)
[ ] 복구 리허설(월 1회 권장)     : 18-3 임시 DB 복원 성공
[ ] 컨테이너 상태·재시작 정책    : docker compose ps  (Up, restart=unless-stopped)
[ ] 디스크 여유                 : df -h  /  docker system df
[ ] fail2ban 동작               : sudo fail2ban-client status sshd
[ ] 보안 업데이트 적용           : sudo unattended-upgrade --dry-run
[ ] 인증서 만료(HTTPS 사용 시)   : Caddy 자동 / certbot는 갱신 확인
[ ] 백업이 실제로 돌았는지        : tail ~/backups/backup.log  (WSL idle로 누락되지 않았는지, 18-2-1)
[ ] DB·관리 포트 외부 비노출      : (다른 PC에서) nc -vz <서버> 5432 8080 3001 → 모두 실패(차단)해야 정상
[ ] (v3) 위험 변경 전 스냅샷      : D:\wsl-backups 에 최근 ubuntu_*.tar 존재 (15-A)
[ ] (v3) 백업 오프사이트·암호화    : ls /mnt/d/wsl-backups/*.gpg (또는 *.enc) — 최근 파일 존재 (18-1)
[ ] (v3) sshd 실제 적용값 확인     : sudo sshd -T | grep -E 'passwordauthentication|permitrootlogin|maxauthtries'
[ ] (v3) 컨테이너 하드닝 반영      : docker inspect <svc> --format '{{.HostConfig.SecurityOpt}} {{.HostConfig.Memory}}'
```
