# 이야기(stories) — 이야기체 개념 지도 (허브)

부품 이름 대신 **"작은 식당 주방"** 비유로 SkinLens 서버 세계를 풀어 쓴 이야기들의 허브입니다.
읽는 순서, 공용 **비유 사전**, 그리고 심화편 **로드맵**을 여기 한곳에 모았습니다.
(이야기는 **개념 지도**입니다. 실제 명령·설정·근거는 `docs/`(server-setup·architecture·operations)와 `deploy/`·`services/` 실제 파일에 있습니다.)

## 읽는 순서

파일명의 두 자리 번호(01~10)가 읽는 순서와 같습니다.

1. **「01_SkinLens 서버 이야기」** (overview) — 빈 데스크톱이 식당이 되기까지의 **전체 6막**
   (구축 → 하드닝 → 운영 → 백업 → 이관 → 배포). 큰 그림을 먼저 여기서 잡습니다.
2. 관심 단계의 **심화편**으로:
   - **「02_SkinLens 구축 이야기」** — 막 1(구축)을 단계별로 (골조·SSH·다중 계정·Docker·네트워킹·검증)
   - **「03_SkinLens 하드닝 이야기」** — 막 2(하드닝)를 단계별로 (문지기·SSH·뒷문·표면·컨테이너·골방)
   - **「04_SkinLens 운영 이야기」** — 막 3(운영)을 단계별로 (자동 개점·벽시계·쓰레기통·설비 점검·경비실)
   - **「05_SkinLens 백업 이야기」** — 막 4(백업)를 단계별로 (장부 사본·금고 잠금·오프사이트·데드맨·스냅샷·리허설)
   - **「06_SkinLens 이관 이야기」** — 막 5(이관)를 단계별로 (예고·멈춤·델타덤프·점검·전환·롤백)
   - **「07_SkinLens 배포 이야기」** — 막 6(배포)을 단계별로 (정적·서버빌드·엔진 세 여정, 스테이징/운영)
   - **「08_SkinLens 기동 이야기」** — 환경별 빌드·기동 절차(dev 조리 / staging 완제품 / prod 창고+자물쇠). 실무 명령은 `deploy/scripts/sl` 하나.

> **+ 「09_SkinLens 3-Tier 이전 이야기」** (구조 변경편) — 6막을 지난 주방을 **쇼윈도(Vercel)·데이터 창고(Supabase)·우리 주방(AI Server) 셋으로 나누는** 진행상황. 막과 직교하는 별도 축.
> **+ 「10_SkinLens 프로젝트 분석 이야기」** (3-Tier 이후 투어편) — 쇼윈도·창고·주방으로 나뉜 뒤, 손님 사진 한 장이 리포트가 되어 돌아오기까지의 **현재 운영 흐름**을 따라가는 이야기.

## 심화편 로드맵

| # | 막 | 심화편 | 세부 문서 |
|---|---|---|---|
| 01 | 전체 overview | **「서버 이야기」** | — |
| 02 | 1. 구축 | **「구축 이야기」** | `../server-setup/windows11_ubuntu_server_setup.md` |
| 03 | 2. 하드닝 | **「하드닝 이야기」** | `../server-setup/windows11_ubuntu_server_setup.md`(SSH·컨테이너·Nginx 하드닝) |
| 04 | 3. 운영 | **「운영 이야기」** | `../server-setup/windows11_ubuntu_server_setup.md`(운영·시계·로그·업데이트) |
| 05 | 4. 백업 | **「백업 이야기」** | `../../deploy/scripts/`(`pg_backup.sh`·`wsl --export`) |
| 06 | 5. 이관 | **「이관 이야기」** | `../server-setup/server_migration_runbook.md` |
| 07 | 6. 배포 | **「배포 이야기」** | `../../deploy/`·`../../.github/workflows/` |
| 08 | —. 기동 | **「기동 이야기」** | `../../deploy/scripts/sl`·`../operations/환경별_빌드_기동_절차.md` |
| 09 | —. 구조 변경 | **「3-Tier 이전 이야기」** | `../architecture/05_3Tier_이전_작업계획.md`·`04_3Tier_…설계.md`·`../operations/09_Phase1_Supabase_실행런북.md` |
| 10 | —. 3-Tier 이후 투어 | **「프로젝트 분석 이야기」** | `../ANALYSIS_REPORT_2026-08-19.md` |

> 지금은 **구축·하드닝·운영·백업·이관·배포** 6막 전체에 대한 심화편 문서가 완비되어 있습니다.
> 여기에 **구조 변경편**(3-Tier 이전)과 **이후 투어편**(프로젝트 분석)이 추가됐습니다.
> 3-Tier 구조 선택의 근거(장단점 비교)는 이야기가 아니라 분석 문서로, `../architecture/SkinLens_서버구축_아키텍처_장단점_비교.md`에 있습니다.

## 공용 비유 사전

여러 편이 공유하는 매핑입니다. 각 문서는 **자기가 새로 도입하는 비유만** 자기 표에 두고, 나머지는 여기를 참조합니다.
첫 등장 시에는 **"비유(부품)"** 형태로 병기합니다(예: 주방장(gateway), 이미지 창고(GHCR)).

### 묶음·집 — 서버가 깔리는 바닥

| 비유 | 실제 부품 |
|---|---|
| 빈 데스크톱 / 빈 땅 | Windows 11 호스트 |
| 리눅스 집·주방 | WSL2 Ubuntu |
| 평수·화구 배정 | `.wslconfig` (메모리 8GB·CPU 4·swap 2GB) |
| 손님 없으면 불 끄는 타이머 | `vmIdleTimeout` |
| 규격 조리대 / 주방 배치도 | Docker / `deploy/compose/compose.base.yml` |

### 접객·주방

| 비유 | 실제 부품 |
|---|---|
| 안내 데스크 | nginx(엣지) |
| 홈페이지 손님 / 개발자페이지 손님 / 앱 손님 | 공개 사이트 / 남동·데모 / Flutter(API) |
| 주방장 | gateway(FastAPI) — 주문 접수·번호표 발급 |
| 리포트 담당 | worker — 뒤에서 엔진 호출·리포트 생성 |
| 빠른 대기줄·호출 신호 | redis(캐시·큐, Phase 3 예정) |
| 접수 대장 | Job Queue(Postgres 기반) |

### 창문 없는 골방(엔진) — 폐쇄망

| 비유 | 실제 부품 |
|---|---|
| 창문 없는 골방 | `enginenet`(internal) — egress 차단 |
| **분석 요리사** | engine-analysis (피부 분석·측정지표·점수) |
| **처방 요리사(독립 주문도 받음)** | engine-prescription — 분석의 하위가 아니라 **독립 진입점**(분석/설문/PCR 중 ≥1이면 동작) |

### 창고·냉장고 (⚠ 접두어 고정 — 셋을 구분)

| 비유 | 실제 부품 | 무엇 |
|---|---|---|
| **이미지 창고** | GHCR(컨테이너 레지스트리) | 완제품 엔진 **이미지** 보관 |
| **데이터 창고(납품처)** | Supabase(Postgres·Storage) | 실운영 **장부·원본**. 백업·PITR도 여기 담당 |
| **임시 냉장고** | 로컬 db(postgres 컨테이너) | **스테이징 전용** 연습용. `staging` 프로파일에서만 켜짐 |

> 셋 다 "창고"라 부륩면 헷갈립니다. **이미지는 이미지 창고(GHCR)**, **실데이터는 데이터 창고=납품처(Supabase)**,
> **연습용 로컬 db는 임시 냉장고**로 접두어를 고정합니다.

### 보안·백업

| 비유 | 실제 부품 |
|---|---|
| 지문 열쇠 문 | SSH 키 인증(비밀번호 로그인 잠금) |
| 문지기 / 노크 차단 | 방화벽(ufw) / fail2ban |
| 직원 전용 뒷문 | 관리 포트(adminer·uptime-kuma·db)를 SSH 터널로만 |
| 경비실 CCTV | uptime-kuma |
| 데몬 관리 규칙 | `daemon.json`(재시작 유지·로그 상한) |
| 매일 장부 사본 / 주방 통째 스냅샷 | `pg_backup.sh` / `wsl --export` |

### 배포 캐스트

| 비유 | 실제 부품 |
|---|---|
| 우편함 | GitHub 계정(다중: `coteleafdev`·`skygoldlee-cyber`) |
| 공방 | monorepo의 서비스별 경로(`services/`·`apps/`, 경로 필터로 구분) |
| 집사 | self-hosted 러너(주방 상주·아웃바운드 폴닝) |
| 중앙 공장 | GitHub-hosted 러너(무거운 엔진을 대신 구움) |
| 지배인 | `deploy.sh`(헬스체크 게이트·롤백) |
| 시식 검사관 | 컨테이너 healthcheck |
| 주방 화이트보드 한 줄 | `.env.images`(현재 버전 기록 → 즉시 롤백) |
| 총지배인 | `deploy/scripts/sl` — 어느 주방이든 같은 동사(`up/down/logs/ps/doctor/init/deploy`)로 지시 |
| 집에서 거는 무전기 | 원격 모니터링·제어 — Windows `deploy/scripts/remote.ps1`(또는 `remote.cmd`)가 SSH 로 서버 `deploy/ops/remote-status.sh`(읽기)·`sl`/`deploy.sh`(쓰기)를 호출. prod 쓰기는 확인, 배포는 자동 롤백 |

### 환경

| 비유 | 실제 부품 |
|---|---|
| 연습 주방 | 스테이징(WSL) — `staging` 프로파일, **임시 냉장고** 사용 |
| 영업점 | 운영(VPS) — **데이터 창고(Supabase)** 사용, 로컬 db 미기동 |

## 세부 문서 위치 (현행 monorepo 구조)

이야기가 가리키는 실제 문서·코드의 **현재 경로**입니다(예전 번호 폴터 → 현재 위치).
경로는 이 파일(`docs/stories/`) 기준 상대경로입니다.

| 이야기 속 표기(옛) | 현재 위치 |
|---|---|
| `04_이야기/` | `docs/stories/` (이 폴터) |
| `01_서버구축…` 가이드 | `../server-setup/windows11_ubuntu_server_setup.md`, `../server-setup/server_migration_runbook.md` |
| `01`의 검증·백업·이관 스크립트 | `../../deploy/scripts/` (`verify_server.sh`·`verify_client.ps1`·`pg_backup.sh`·`wsl-backup-task.ps1`·`migrate_*.sh`·`deploy.sh`), 통합검증은 `../../tests/test_environment.py` |
| `02_적합성검토` (부록 B·C) | `../architecture/SkinLens_서버구성_적합성_검토.md` |
| `03_webstack_스캐폴드` | 실물로 전개됨 → `../../deploy/compose/`·`../../deploy/nginx/`·`../../services/`·`../../apps/` |
| `05_CD_배포` | `../../deploy/scripts/deploy.sh`·`../../deploy/compose/`·`../../deploy/env/.env.images`·`../../.github/workflows/`, 후속 잡은 `../../deploy/ops-jobs/` |
| `08_최종리뷰` (감사) | `../architecture/`(`01_…최종리뷰`·`02_PATCH_NOTES_P0_P1`·`03_DB_MIGRATION_ROLLBACK`), 후속 로드맵은 `../roadmap/04_후속보완_로드맵.md` |
| 체크리스트·학습 로드맵 | `../operations/06_운영·배포_체크리스트.md`·`../operations/07_학습_로드맵.md` |
| 원격 모니터링·제어 (무전기) | `../operations/11_원격_모니터링_제어.md`, `../../deploy/scripts/remote.ps1`·`remote.cmd`, `../../deploy/ops/remote-status.sh`, `../../deploy/env/remote.env.example` |

---

## 고객 안내 자료 (PPTX) — `assets/`

외부(고객·발주처)에게 구조 변경을 설명할 때 쓰는 슬라이드 자료입니다.

| 파일 | 용도 |
|---|---|
| `assets/SkinLens_3Tier_이전_고객안내.pptx` | 3-Tier(Vercel·Supabase·AI Server) 이전 안내 |
| `assets/SkinLens_서버통합_고객안내.pptx` | 서버 통합 구성 안내 |

> 두 자료 모두 **개념 안내용**이며, 실제 진행 상태·근거는 `docs/architecture/`·`docs/operations/`·`docs/roadmap/`의 해당 문서를 기준으로 합니다.
> 3-Tier 이전 이야기 본문의 삽화(`assets/SkinLens_3Tier_이전_이야기.png`·`.svg`)도 이 폴터에 있습니다.

---

> 이야기들의 변경 내역(v2·v3·v3.1·v4·v5)은 [`../changelog/stories_변경요약.md`](../changelog/stories_변경요약.md)를 보세요.
