# 보완 개선 노트 v3 — 3차 검토

v2는 **보안 노출과 조용한 실패**를 잡았습니다(ufw↔Docker, 포트 노출, WSL 수명주기로 인한 백업 누락,
백업 스크립트 `.env`화, `DATABASE_URL` 특수문자, fail2ban NAT). v3는 그 위에서 **구축 절차 자체의
안전성(락아웃·롤백·백업)**, **컨테이너/표면 하드닝**, **이관 컷오버의 데이터 정합성**에 초점을 둡니다.
v2가 이미 잡은 6항목은 중복하지 않고, **v2에 아직 없던 11가지**만 골랐습니다.

## 요약 (심각도 순)

| # | 심각도 | 영역 | 지금(그대로 두면) | 조치 위치 |
|---|---|---|---|---|
| 1 | **높음** | SSH 변경 안전성 | 편집·`sed` 후 검증 없이 재시작 → 오타 시 원격 락아웃, `sed`가 없는 줄은 안 바꿔 "껐다고 착각" | 5-3·5-4·6-4 |
| 2 | **높음** | 롤백 | 위험 변경 전 전체 스냅샷 수단 없음 | 15-A(신설) |
| 3 | **높음** | 백업 견고성(PIPA) | 같은 디스크·평문·시간기반 삭제만 | 18-1, `pg_backup.sh` |
| 4 | 중간 | 컨테이너 권한 | 컨테이너가 root로 실행 | 9-4, webstack Dockerfile·compose |
| 5 | 중간 | 리소스 격리 | mem/cpu 상한 없음 | 부록 compose, webstack compose |
| 6 | 중간 | Docker 데몬(native) | `daemon.json` 없음 | 8-B, 런북 §5 |
| 7 | 중간 | 웹 표면 | `server_tokens`·보안헤더·레이트리밋 없음 | 9-5, webstack nginx |
| 8 | 중간 | SSH 하드닝 | `MaxAuthTries` 등 미설정 | 5-3 |
| 9 | 중간 | 이관 컷오버 | 최종 덤프~DNS 전환 사이 쓰기 유실 가능 | 런북 §8 |
| 10 | 낮음 | 자동 업데이트·로그 | 재부팅 정책·journald 상한 미지정 | 21-1·21-2(신설) |
| 11 | 낮음 | WSL 특이 | 절전 후 시계 드리프트, `vmIdleTimeout` 암묵 | 2-1, 16-2 |

> ①②③은 사고가 나면 복구 비용이 큰 항목이라 우선 반영을 권합니다.

---

## 1. SSH 변경 안전성 — 락아웃 방지 (높음)

- **원인:** 5-3은 `sshd_config`를 편집한 뒤, 6-4는 `sed`로 `PasswordAuthentication no`를 넣은 뒤 **검증
  없이 곧바로 재시작**합니다. 오타가 있어도 재시작해 sshd가 죽으면 **원격에서 잠깁니다.** 또 6-4의
  `sed 's/^#\?PasswordAuthentication .*/.../'`는 **해당 줄이 없으면 아무것도 안 바꿔**, 패스워드 로그인이
  계속 열려 있는데 껐다고 착각하게 됩니다.
- **조치:** 표준 절차를 못박음 — **문법 검증(`sshd -t`) → 통과 시에만 재시작 → 실제 적용값(`sshd -T`)
  확인 → 기존 세션 유지한 채 새 창 접속 확인.** 6-4는 "없으면 추가·있으면 수정"(`grep -q … && sed … ||
  tee -a`) 폴백으로 바꿨습니다. 이 안전 수칙을 이관 편뿐 아니라 **본 구축 단계(5·6장)에도** 넣었습니다.

## 2. 위험 변경 전 전체 스냅샷 (높음)

- **원인:** 커널·systemd·Docker 데몬처럼 되돌리기 어려운 변경 전에 **OS 상태 전체를 되돌릴 수단**이
  없었습니다(18장 DB 백업은 데이터만).
- **조치:** **15-A 신설** — `wsl --export`로 배포판을 통째로 스냅샷, `wsl --import`로 롤백. `.tar`는 WSL
  볼륨과 **다른 물리 디스크**(D:/외장)에 두도록 안내. §16·§21처럼 데몬/커널을 건드리는 절차 앞에서 권장.

## 3. 백업의 실전 견고성 — PIPA 맥락 (높음)

- **원인:** v2에서 스크립트를 `.env` 기반·원자적 커밋으로 고쳤지만, 절차 레벨에서 ⑴ 백업이 DB와 **같은
  WSL 디스크**에 있어 디스크 장애 시 동반 소실, ⑵ 피부 이미지·분석 결과 덤프가 **평문**, ⑶ 보존이
  **시간기반뿐**이라 백업이 며칠 멈추면 마지막 정상본까지 삭제, ⑷ 실패해도 **아무도 로그를 안 봄**.
- **조치:** `pg_backup.sh`에 네 가지를 **모두 선택 env로**(설정 안 하면 기존 동작 그대로) 추가 —
  `OFFSITE_DIR`(오프사이트 복제), `BACKUP_GPG_RCPT`/`BACKUP_ENC_PASSFILE`(GPG 또는 openssl AES-256 암호화
  후 평문 삭제), `MIN_KEEP`(최신 N개 무조건 보존 = 보존 하한), `HEALTHCHECK_URL`(성공 시에만 핑 =
  데드맨 스위치). 18-1 문서에 사용법과 근거를 명시.

## 4. 컨테이너 비루트 실행 (중간)

- **원인:** Dockerfile들이 기본 **root**로 실행 → 앱/엔진에 컨테이너 탈출 취약점이 있으면 root가 그대로
  노출.
- **조치:** webstack 4개 서비스(gateway·worker·engine-analysis·engine-prescription)와 9-4 예시 Dockerfile을
  **비루트 USER(uid 10001)**로 변경. compose에서 자체 빌드 서비스에 `security_opt: no-new-privileges` +
  `cap_drop: ALL` + `read_only`(+`tmpfs:/tmp`)를 더함. 8000>1024라 바인딩 capability가 필요 없어 그대로
  동작합니다. **공식 이미지(postgres·nginx·redis·adminer·uptime-kuma)**는 entrypoint/포트 바인딩이
  capability를 필요로 해 `cap_drop: ALL`은 생략하고 `no-new-privileges`만 적용.

## 5. 컨테이너 리소스 상한 (중간)

- **원인:** mem/cpu 한도가 없어 한 컨테이너가 OOM으로 폭주하면 **호스트 전체를 잠식**(GPU·ML 워크로드라
  특히).
- **조치:** 부록 compose와 webstack compose 각 서비스에 `mem_limit`/`cpus` 상한 추가. **엔진은 예시값
  (2g)이므로 실제 모델 크기에 맞춰 상향**하라고 명시.

## 6. native Docker 데몬 하드닝 (중간)

- **원인:** 이관 후(8-B) 서버에 `daemon.json`이 없어, 데몬 재시작 시 컨테이너가 함께 내려가고 로그·기본
  보안이 전역으로 잡히지 않음.
- **조치:** 8-B와 런북 §5에 `/etc/docker/daemon.json` 추가 — `live-restore`(재시작 중 컨테이너 유지),
  전역 `json-file` 로그 상한, `no-new-privileges` 기본값. Docker Desktop(8-A)은 같은 JSON을 Settings →
  Docker Engine에서 관리한다고 병기.

## 7. Nginx 표면 하드닝 (중간)

- **원인:** 기본 conf에 **버전 은닉·보안헤더·레이트리밋**이 없음.
- **조치:** 9-5에 `server_tokens off` + `X-Content-Type-Options`/`X-Frame-Options`/`Referrer-Policy` +
  `limit_req`. webstack은 표면이 3개(www/dev/api)라 **http 컨텍스트 지시어를 분리** —
  `conf.d/00-hardening.conf`(`server_tokens`·`limit_req_zone`), `snippets/security-headers.conf`(헤더)를
  각 server가 include, api에는 `limit_req zone=api burst=20 nodelay`. HSTS는 HTTPS(§22) 적용 후 주석 해제.

## 8. sshd 추가 하드닝 (중간)

- **원인:** `PermitRootLogin no`만 있고 무차별 시도·유휴 세션·불필요 포워딩이 미설정.
- **조치:** 5-3에 `MaxAuthTries 3` · `LoginGraceTime 20` · `ClientAliveInterval 300` ·
  `ClientAliveCountMax 2` · `X11Forwarding no` 추가. **`AllowTcpForwarding no`는 기본값(yes) 유지 +
  주석/경고로만** 뒀습니다 — 이 문서는 관리 포트(adminer 8080·uptime-kuma 3001·DB 5432)를 `ssh -L` 로컬
  포워딩으로만 접근하도록 설계돼 있어, 켜면 그 터널이 막히기 때문입니다. `-L` 터널을 쓰지 않는 서버에서만
  주석을 해제하세요.

## 9. 이관 컷오버의 쓰기 유실 (중간)

- **원인:** 런북 §8이 "최종 델타 덤프 → DNS 전환" 순이라, 그 사이 소스로 들어온 쓰기는 유실.
- **조치:** 컷오버 직전 **소스를 읽기 전용/점검 모드로 전환(쓰기 중지) → 최종 덤프 → 대상 반영 → 검증 →
  DNS 전환** 순으로 재정렬. **짧은 다운타임(쓰기 불가 구간)을 감수하는 대신 데이터 정합성을 얻는**
  트레이드오프임을 명시하고, 무중단이 필수면 논리 복제 검토를 언급.

## 10. 자동 업데이트·로그 정책 (낮음)

- **원인:** §21이 `unattended-upgrades`를 켜지만 **재부팅 정책이 기본값(false)**이라 커널·라이브러리 갱신
  반영이 애매하고, native에서 자동 재부팅이 켜지면 새벽에 서비스가 끊길 수 있음. WSL+systemd의 journald가
  무한정 커질 수 있음.
- **조치:** **21-1 신설** — `Automatic-Reboot`/`Automatic-Reboot-Time`을 명시(WSL은 끄기 권장, native는
  트래픽 적은 시간대 지정). **21-2 신설** — `journald` `SystemMaxUse=200M` 상한.

## 11. WSL 절전 후 시계 드리프트 (낮음)

- **원인:** 호스트가 절전/최대절전에서 깨어난 뒤 WSL VM 시계가 뒤처져 **TLS·JWT·apt·로그 시각**이 틀어질
  수 있음. `vmIdleTimeout`도 v2에선 문장으로만 언급.
- **조치:** 2-1 `.wslconfig`에 `vmIdleTimeout=60000`을 값으로 명시(정책 문서화)하고 드리프트 주의를 추가.
  16-2 부팅 스크립트에 `hwclock -s`로 강제 동기화를 넣어 부팅/복귀 시 보정.

---

## 변경/추가 파일

- **수정:** `windows11_ubuntu_server_setup.md`
  (2-1, 5-3, 5-4, 6-4, 8-B, 9-4, 9-5, 15-A 신설, 16-2, 18-1, 21-1·21-2 신설, 부록 compose, 부록 B 체크리스트)
- **수정:** `server_migration_runbook.md` (§5 daemon.json, §8 컷오버 재정렬)
- **수정:** `pg_backup.sh` (오프사이트·암호화·보존 하한·데드맨 스위치 — 전부 선택 env)
- **수정(webstack):** `docker-compose.yml`(9서비스 하드닝·리소스 상한),
  `gateway/worker/engine-analysis/engine-prescription`의 `Dockerfile`(비루트),
  `nginx/conf.d/api.conf`·`dev.conf`·`www.conf`(헤더·레이트리밋 연결)
- **신설(webstack):** `nginx/conf.d/00-hardening.conf`(server_tokens·레이트리밋 존),
  `nginx/snippets/security-headers.conf`(공통 보안헤더)
- **신설:** `CHANGES_v3.diff`(이 3차 패치의 통합 diff), `보완개선_v3_노트.md`(이 문서)

v2에서 이미 옳게 동작하던 `verify_server.sh`·`verify_client.ps1`·`test_environment.py`·`migrate_*.sh`·
`wsl-backup-task.ps1`는 그대로 두었습니다(불필요한 변경 회피).

## 반영 후 빠른 검증

```bash
# SSH: 실제 적용값 확인 (파일이 아니라 sshd 가 읽은 값)
$ sudo sshd -t && sudo sshd -T | grep -iE '^(passwordauthentication|permitrootlogin|maxauthtries)'

# 컨테이너 하드닝·리소스 상한 반영 확인
$ docker inspect sl_gateway --format '{{.HostConfig.SecurityOpt}} {{.HostConfig.CapDrop}} {{.HostConfig.Memory}}'

# Nginx 설정 문법 (컨테이너 안에서)
$ docker exec sl_nginx nginx -t

# 백업: 오프사이트+암호화+핑까지 한 번 돌려보기 (열리는지 리허설은 18-3)
$ OFFSITE_DIR=/mnt/d/wsl-backups BACKUP_GPG_RCPT=backup@yourco MIN_KEEP=3 \
  HEALTHCHECK_URL=https://hc-ping.com/xxxx  ~/scripts/pg_backup.sh && ls -lh ~/backups /mnt/d/wsl-backups

# native 데몬 하드닝 확인
$ docker info --format '{{.LoggingDriver}} live-restore={{.LiveRestoreEnabled}}'

# 스냅샷(위험 변경 전) — Windows
PS> wsl --export Ubuntu-24.04 D:\wsl-backups\ubuntu_$(Get-Date -Format yyyyMMdd).tar
```
