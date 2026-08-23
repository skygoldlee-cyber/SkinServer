# 보완 개선 노트 v2 — 패치본 재검토

이미 반영된 1차 패치본(`CHANGES.diff`)은 `.env` 안전 파싱, TTY 덤프 손상(`docker exec -t`) 제거,
HTTP 판정 정합성, `-Mode prod` 검증, TLS1.2 강제, Caddy/Nginx 80 포트 충돌 경고 등
**핵심 버그를 이미 잘 잡아** 두었습니다. shellcheck·`py_compile`도 사실상 클린입니다.

이 v2는 그 위에서 **아직 남아 있던 실전 함정 6가지**를 보완합니다. 대부분 "명령은 맞는데
WSL/Docker의 동작 특성 때문에 조용히 실패/노출되는" 종류라, 문서만 읽어서는 알기 어려운 것들입니다.

## 요약

| # | 심각도 | 영역 | 증상(그대로 두면) | 조치 위치 |
|---|---|---|---|---|
| 1 | **높음(보안)** | ufw ↔ Docker | `ufw deny 5432`를 걸어도 DB 포트가 외부에 열려 있음 | 20-2, 런북 §7-1 |
| 2 | **높음(보안)** | 포트 노출 | `fastapi:8000`·`postgres:5432`가 LAN 전체에 노출(불필요) | 9-3-1(신설), 부록 compose |
| 3 | **높음(운영)** | WSL 수명주기 | 새벽 cron 백업이 idle 종료로 **조용히 누락** | 운영 파트 상단, 18-2-1(신설) |
| 4 | 중간 | 백업 정합성 | 백업 스크립트가 `.env` 무시·하드코딩(`appuser`/`appdb`) | 18-1, `pg_backup.sh`(신설) |
| 5 | 중간 | DB 접속 | `POSTGRES_PASSWORD` 특수문자로 `DATABASE_URL` 파싱 실패 | 9-2 |
| 6 | 낮음 | fail2ban | WSL NAT에서 원본 IP가 게이트웨이로 보여 차단이 무의미/오차단 | 20-1 |

---

## 1. ufw는 Docker 발행 포트를 막지 못한다 (높음·보안)

- **원인:** native Docker는 iptables `DOCKER`/`nat` 체인에 규칙을 넣어, `-p 5432:5432`로 발행한
  포트를 **ufw의 INPUT 규칙보다 먼저** 통과시킵니다. 그래서 `ufw default deny` + `ufw deny 5432`가
  걸려 있어도 컨테이너 발행 포트는 외부에서 그대로 열립니다. 런북 §7-1은 5432/8080/3001을
  "ufw로 차단"한다고 읽힐 여지가 있었는데, 이 경로로는 실제로 안 막힙니다.
- **조치:** 확실한 차단 3가지를 명시 — ⑴ compose에서 `127.0.0.1:` 바인딩(가장 간단), ⑵ 클라우드
  보안그룹(host 밖 계층이라 우회 영향 없음), ⑶ `DOCKER-USER` 체인/`ufw-docker`. 이관 후
  **다른 망에서 `nc -vz`로 실제 차단 검증**하는 절차를 체크리스트에 추가.

## 2. 불필요한 포트를 0.0.0.0로 발행 (높음·보안)

- **원인:** 기본 compose가 `fastapi(8000)`·`postgres(5432)`를 모든 인터페이스로 발행합니다.
  이 스택에서 바깥이 닿아야 하는 건 **Nginx(:80)뿐**이고, FastAPI·PostgreSQL은 Compose 내부망에서
  컨테이너 이름으로만 통신하면 됩니다. 열린 포트 = LAN 공격 표면.
- **조치:** 9-3-1 "포트 노출 최소화" 절 신설(루프백 바인딩 방법·트레이드오프 설명), **부록 최종
  compose에 실제 적용**(nginx만 공개, 나머지는 `127.0.0.1:`). 서버 로컬 검증·SSH 터널로 접근.

## 3. WSL idle 종료로 cron 백업 누락 (높음·운영)

- **원인:** WSL2 배포판은 안에 프로세스가 없으면 ~60초 뒤 자동 종료됩니다. Docker Desktop을 쓰면
  컨테이너는 `docker-desktop` 배포판에 있어 **우리 Ubuntu 배포판을 깨워 두지 않습니다.** 결과적으로
  새벽 03:00에 Ubuntu가 꺼져 있으면 cron·fail2ban·unattended-upgrades 타이머가 깨어나지 못합니다.
- **조치:** 운영 파트 상단에 "WSL 수명주기" 경고 신설. 시간 기반 작업(백업)은 **Windows 작업
  스케줄러가 WSL을 깨워** 실행하도록 18-2-1 신설 + `wsl-backup-task.ps1` 첨부. native/이관 서버는
  systemd 상시 동작이라 해당 없음을 명시.

## 4. 백업 스크립트의 자격증명 하드코딩 (중간)

- **원인:** 18-1 예시가 `pg_dump -U appuser ... appdb`로 하드코딩 → `.env`를 바꾸면 백업이 조용히
  엉뚱한/없는 DB를 덤프.
- **조치:** migrate 스크립트와 동일한 안전 파서로 **`.env`에서 계정/DB를 읽도록** 변경하고,
  **덤프 성공 시에만 최종 파일로 커밋**(0바이트 백업 방지). 독립 파일 `pg_backup.sh`로도 제공.

## 5. 비밀번호 특수문자로 DATABASE_URL 깨짐 (중간)

- **원인:** `postgresql://user:pass@host/db` URL 특성상 `POSTGRES_PASSWORD`에 `@ : / ? # %` 등이
  들어가면 파싱이 깨져 DB 접속 실패.
- **조치:** 9-2에 경고 + 해법 두 가지(URL-safe 문자만 사용 / `sqlalchemy.engine.URL.create`로 부품
  조립 시 자동 인코딩) 추가.

## 6. WSL NAT에서 fail2ban 원본 IP (낮음)

- **원인:** NAT + portproxy 경로에서는 sshd가 보는 원본이 공격자 IP가 아니라 Windows/WSL 게이트웨이로
  보일 수 있어, 게이트웨이를 밴하거나(정상 접속 차단) 실효가 없습니다.
- **조치:** 20-1에 주의 추가 — 미러 네트워킹/native에서는 원본 IP 보존, WSL NAT에서는 Windows
  방화벽 쪽 최소화가 더 확실.

---

## 변경/추가 파일

- **수정:** `windows11_ubuntu_server_setup.md` (9-2, 9-3-1 신설, 운영 파트 상단, 18-1, 18-2-1 신설,
  20-1, 20-2, 부록 compose, 부록 B 체크리스트)
- **수정:** `server_migration_runbook.md` (§7-1 Docker 우회 경고, 사후 체크리스트)
- **신설:** `pg_backup.sh` — `.env` 기반 백업(18장)
- **신설:** `wsl-backup-task.ps1` — Windows 작업 스케줄러 백업 트리거(18-2-1)

1차 패치본에서 이미 옳게 동작하던 `verify_server.sh`·`verify_client.ps1`·`test_environment.py`·
`migrate_*.sh`는 그대로 두었습니다(불필요한 변경 회피).

## 반영 후 빠른 검증

```bash
# 하드닝된 compose로 재기동 후, 서버 로컬에서는 여전히 통과해야 함
$ ./verify_server.sh services

# 다른 PC/망에서 관리·DB 포트가 '차단'되는지 확인 (전부 실패해야 정상)
$ nc -vz <서버> 5432 8080 3001

# 백업이 실제로 복원 가능한지 리허설(18-3)
$ ~/scripts/pg_backup.sh && ls -lh ~/backups
```
