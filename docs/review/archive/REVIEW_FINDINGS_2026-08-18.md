# 코드베이스 전수 리뷰 — 개선·보완사항 정리 (2026-08-18)

> 목적: monorepo 전체(설계 문서·서비스·앱·배포·CI/테스트)를 읽고 **강점 / 발견된 이슈 / 보완 제안**을 한 장에 정리한다.
> 각 항목은 코드·설정 파일의 **실제 근거**를 링크로 달았다. 우선순위는 기존 문서 관례(P0/P1/P2)를 따른다.
>
> 리뷰 범위: `README.md`·`MIGRATION.md`·`docs/architecture/04·05`·`docs/roadmap/00`·`services/{gateway,worker,engine-*}`·`apps/webapp-next`·`deploy/{compose,caddy,env,supabase,ops-jobs}`·`.github/workflows`·`tests`·`packages/common`.

---

## 0. 한눈에 보는 판정

| 축 | 상태 | 한 줄 평가 |
|---|---|---|
| 설계·문서 | ✅ 매우 양호 | 3-Tier 설계 정본·작업계획·런북·로드맵이 코드와 정합. 문서↔코드 대응이 드물게 정확 |
| 보안(인증·RLS·격리) | ✅ 양호 | fail-fast 인증·RLS 정책·폐쇄망 엔진·presigned 재검증까지 심층 방어가 잘 배선됨 |
| 안정성(재시도·리퍼·풀링) | ✅ 양호 | SKIP LOCKED·backoff·stale reaper·데드레터·커넥션 풀·임시파일 정리까지 갖춤 |
| 3-Tier 이전 | 🟡 코드 완료 | Phase 1~4 코드 완료, 남은 것은 실배포·E2E 검증·제거 작업 |
| PIPA(캐시 정책) | 🟡 경미한 결함 | Supabase SW 패턴이 `PUT`을 못 막음(아래 P1-1) |
| 운영 배선(prod ENV) | ✅ 해결 | prod/staging gateway에 `ENV` 명시 완료(아래 P0-1) |
| 도메인(엔진) | 🟡 의도된 placeholder | OpenCV 실측·규칙 stub — 정규화 상수·실배합은 seam으로 명시됨 |
| 테스트 | 🟡 양호하나 공백 | 계약 드리프트 가드·스토리지 mock은 우수. presigned E2E·RLS 검증 테스트 없음 |

---

## 1. 강점 (유지할 것)

리뷰에서 확인된 잘 설계된 부분 — 굳이 건드리지 말고 유지한다.

1. **fail-fast 인증** — [`main.py:47`](../../services/gateway/app/main.py) `ENV=prod`에서 `AUTH_MODE!=strict`면 기동 거부. dev 모드가 운영에 새는 사고를 차단.
2. **JWT 이중 검증** — [`main.py:178`](../../services/gateway/app/main.py) `aud=authenticated` + `iss`를 `SUPABASE_URL/auth/v1`로 고정해 타 프로젝트 토큰 유입 차단.
3. **presigned 심층 방어 체인** — gateway(content-type 화이트리스트·크기 상한·15분 만료·레이트리밋, [`main.py:285`](../../services/gateway/app/main.py)) → 버킷(`file_size_limit`·MIME 제한, [`0001_rls_and_storage.sql:23`](../../deploy/supabase/policies/0001_rls_and_storage.sql)) → worker(magic-byte 재검증, [`worker.py:155`](../../services/worker/worker.py)) → 다운로드 상한 스트리밍([`storage.py:91`](../../services/worker/storage.py)). 각 층이 우회 가능성을 인지하고 다음 층에 맡기는 주석이 일관.
4. **큐 안정성** — `FOR UPDATE SKIP LOCKED` 클레임([`worker.py:100`](../../services/worker/worker.py)), 재시도+지수 backoff, stale reaper(120s), 재시도 가능/영구 오류 구분(`is_retryable`), `prescriptions` ON CONFLICT로 재처리 중복 방지([`worker.py:196`](../../services/worker/worker.py)).
5. **자원 누수 방지** — supabase 백엔드 임시파일을 `finally`에서 정리하고 `is_temp` 플래그로 local 원본 오삭제 방지([`worker.py:185`](../../services/worker/worker.py)). `read_only`+`tmpfs` 환경에서의 OOM 누수까지 주석으로 명시.
6. **계약 드리프트 가드** — 빌드 컨텍스트 분리로 각 엔진이 계약을 손으로 복사하는데, CI가 등급표·10지표 키·응답 필드 superset을 강제([`test_contract.py:41`](../../tests/common/test_contract.py)). 조용한 드리프트를 막는 실용적 장치.
7. **문서↔코드 정합** — `MIGRATION.md`의 3-Tier 대응표가 "코드 완료/외부 작업/미착수"를 정확히 구분하고, 작업계획(05)의 상태표가 실제 코드 상태와 일치.
8. **컨테이너 하드닝** — 비루트 실행([`Dockerfile:7`](../../services/gateway/Dockerfile)), `no-new-privileges`·`cap_drop: ALL`·`read_only`·메모리/CPU 상한([`compose.base.yml:55`](../../deploy/compose/compose.base.yml)) 전 서비스 적용.
9. **의존성 핀 고정** — 서비스별 `requirements.txt`를 정확한 버전으로 고정해 CD 재현성 확보([`gateway/requirements.txt`](../../services/gateway/requirements.txt)).

---

## 2. 발견된 이슈 (수정 권장)

우선순위: **P0**(운영 배포 전 필수) → **P1**(PIPA/정확성, 빠른 시일 내) → **P2**(정리·개선).

### P0-1. prod 배선에서 `ENV=prod`가 gateway에 설정되지 않음 — fail-fast 무력화 ✅ **해결됨 (2026-08-18)**

- **증상**: [`main.py:35`](../../services/gateway/app/main.py)는 `ENV` 기본값이 `dev`이고, [`main.py:47`](../../services/gateway/app/main.py)의 `ENV == "prod" and AUTH_MODE != "strict"` fail-fast가 있다. 그런데 [`compose.prod.yml:17`](../../deploy/compose/compose.prod.yml)은 gateway에 `AUTH_MODE: strict`만 설정하고 **`ENV: prod`를 설정하지 않는다**.
- **영향**: 두 가지 문제. (a) `AUTH_MODE`가 실수로 `strict`가 아닌 값으로 배포돼도 `ENV=dev` 기본값 때문에 fail-fast가 **발동하지 않아** dev 인증이 운영에 새어들 수 있다. (b) worker([`compose.prod.yml:26`](../../deploy/compose/compose.prod.yml))와 engine-prescription([`compose.prod.yml:39`](../../deploy/compose/compose.prod.yml))엔 `ENV: prod`가 있는데 **gateway만 빠져 있어** 불일치.
- **조치**: `compose.prod.yml`의 gateway `environment`에 `ENV: prod`를 추가한다. staging도 동일하게 `ENV: staging`을 명시해 환경 구분을 명확히 한다.
- **✅ 해결 (2026-08-18)**: [`compose.prod.yml`](../../deploy/compose/compose.prod.yml)의 gateway에 `ENV: prod` 추가, [`compose.staging.yml`](../../deploy/compose/compose.staging.yml)의 gateway에 `ENV: staging` 추가로 fail-fast 활성화 및 환경 구분 명시 완료.

### P1-1. 서비스워커 Supabase NetworkOnly 패턴이 `PUT`(presigned 업로드)을 못 막음

- **증상**: [`next.config.mjs:24`](../../apps/webapp-next/next.config.mjs)의 Supabase `NetworkOnly` 런타임 캐시는 `GET`과 `POST`만 등록돼 있다. 그런데 presigned 업로드는 브라우저가 Supabase Storage에 **`PUT`**으로 직접 전송한다([`api.ts:59`](../../apps/webapp-next/src/lib/api.ts)).
- **영향**: next-pwa/workbox의 기본 동작은 "매칭되는 라우트가 없으면 캐시하지 않고 네트워크로 통과"이므로 **실제로는 캐시되지 않는다**. 다만 `GET`/`POST`만 명시돼 있어 **의도가 불완전**하고, 향후 누군가 `NetworkFirst` 같은 기본 핸들러를 추가하거나 workbox 동작이 바뀌면 `PUT` 요청(피부 사진=민감정보)이 캐시될 위험이 있다. PIPA 원칙상 "명시적으로 NetworkOnly"가 맞다.
- **조치**: Supabase urlPattern 블록에 `PUT` 메서드 항목을 추가한다(및 완전성을 위해 `DELETE`). 동시에 `/api/*`도 현재 `GET`/`POST`만 있으므로, 만약 `/api` 프록시 경로를 쓰게 되면 동일하게 `PUT`/`DELETE`를 추가한다.

### P1-2. `NEXT_PUBLIC_AI_API_BASE`와 SW `urlPattern`의 오리진 불일치

- **증상**: [`api.ts:3`](../../apps/webapp-next/src/lib/api.ts)는 `BASE = NEXT_PUBLIC_AI_API_BASE ?? "/api"`. 운영에선 `https://api.example.com` 같은 **절대 URL**이 들어간다([`.env.example:9`](../../apps/webapp-next/.env.example) 예시). 그런데 [`next.config.mjs:15`](../../apps/webapp-next/next.config.mjs)의 `/api/*` urlPattern은 **상대 경로(같은 오리진)** 만 매칭한다.
- **영향**: `NEXT_PUBLIC_AI_API_BASE`가 절대 URL이면 `/api/*` 패턴은 **한 번도 매칭되지 않는다**. 결과적으로 AI Server로의 요청은 SW 캐시 규칙을 우회한다. Supabase와 달리 AI Server엔 별도의 절대 URL NetworkOnly 규칙이 없어, 현재는 "매칭 없음 → 네트워크 통과"로 우연히 안전하지만 **명시적 보장이 아니다**.
- **조치**: 둘 중 하나로 확정한다.
  - (a) AI API도 절대 오리진으로 쓴다면: `next.config.mjs`에 `^https:\/\/api\.example\.com\/.*$` 같은 **절대 URL NetworkOnly 규칙을 명시**한다(도메인을 빌드타임 env로 주입하거나, 넓게는 `urlPattern: ({url}) => url.origin !== self.location.origin` 형태로 "교차 오리진은 전부 NetworkOnly").
  - (b) Vercel rewrites로 `/api/*`를 AI Server로 프록시한다면: 상대 패턴이 유효하므로 현행 유지 + `vercel.json`/`next.config.mjs`의 `rewrites()` 추가.
  - **권장**: (a)를 택하되, PIPA 보장을 "매칭 없음에 의존"하지 말고 **교차 오리진 NetworkOnly를 명시**한다.

### P1-3. presigned E2E·RLS 검증 테스트 부재

- **증상**: [`tests/gateway/test_storage.py`](../../tests/gateway/test_storage.py)는 Supabase 스토리지를 httpx mock으로 잘 검증하고, [`test_contract.py`](../../tests/common/test_contract.py)는 드리프트를 가드한다. 그러나 아래가 없다.
  - presign → PUT → analyze → worker fetch → done의 **E2E**(Phase 4의 "완료 조건"이 이것인데 테스트로 고정 안 됨).
  - RLS가 "사용자 A가 B의 job/사진 접근 불가"를 **SQL 정책으로 검증**하는 테스트(설계 DoD 04 §9에 명시됐으나 미구현).
- **영향**: Phase 4 완료 조건("E2E 통과")과 DoD의 RLS 검증이 **코드로 고정되지 않아**, 회귀를 CI가 못 잡는다. 특히 RLS는 "정책으로 강제"가 핵심 설계인데 검증 수단이 없다.
- **조치**:
  - `tests/integration/`에 presigned 플로우 통합 테스트 추가(실 Supabase 또는 local Supabase 대상, `pytest -m integration`).
  - RLS 검증은 Supabase SQL로 `set role authenticated; set request.jwt.claim.sub ...` 후 타 사용자 행 접근이 0건인지 확인하는 스크립트를 `tests/` 또는 `deploy/scripts/`에 추가하고 CI에 연결.

### P2-1. requirements-dev.txt가 서비스 핀과 불일치 + psycopg_pool 누락

- **증상**: [`requirements-dev.txt`](../../requirements-dev.txt)는 버전 미핀이고 `psycopg-pool`·`pyjwt`가 없다. 그런데 [`gateway/app/main.py:18`](../../services/gateway/app/main.py)는 `psycopg_pool`을, [`main.py:16`](../../services/gateway/app/main.py)은 `jwt`(PyJWT)를 import한다.
- **영향**: `tests.yml` CI는 `pip install -r requirements-dev.txt`만 하는데, 현재 단위 테스트가 gateway `main.py`를 import하지 않아 우연히 통과한다. 향후 gateway 라우트 단위 테스트를 추가하면 **`ImportError`로 CI가 깨진다**. 또 미핀이라 상류 breaking change로 CI가 조용히 깨질 수 있다.
- **조치**: `requirements-dev.txt`에 `psycopg[binary,pool]`·`psycopg-pool`·`pyjwt`를 추가하고, 서비스와 동일 버전으로 핀(또는 최소 하한 명시)한다.

### P2-2. `redis` 의존성이 gateway requirements에 선반영

- **증상**: [`gateway/requirements.txt:8`](../../services/gateway/requirements.txt)에 `redis==5.2.1`이 있지만, 코드 어디에도 `import redis`가 없고(큐는 Postgres SKIP LOCKED), 주석도 "Phase 3 도입 시 추가"라고 돼 있다. [`compose.base.yml:145`](../../deploy/compose/compose.base.yml)의 redis 서비스도 주석 처리됨.
- **영향**: 쓰지 않는 의존성이 이미지에 포함돼 빌드 시간·공격 표멧만 늘린다. "주석과 달리 이미 설치돼 있다"는 점에서 문서/코드 불일치.
- **조치**: Phase 3 도입 전까지 `redis`를 requirements에서 제거한다. (presign 레이트리밋이 다중 레플리카로 가면 Redis로 이관한다는 주석([`main.py:75`](../../services/gateway/app/main.py))은 유지.)

### P2-3. `docs/**` 남부 링크가 옛 경로(`01_…`, `05_…`)를 참조

- **증상**: [`README.md:146`](../../README.md)과 [`MIGRATION.md:89`](../../MIGRATION.md) 모두 "docs 안 상호 링크가 재배치 이전 경로로 돼 있다"고 스스로 명시.
- **영향**: 신규 합류자가 깨진 링크를 따라가다 혼란. 문서 신뢰도 저하.
- **조치**: `MIGRATION.md`의 대응표를 기준으로 일괄 치환하는 스크립트(또는 수동 패스)를 한 번 돌린다. 우선순위는 자주 읽는 `architecture/`·`operations/`부터.

### P2-4. 제거 예정 자산의 실제 제거 미완료 (3-Tier 잔여)

- **증상**: `MIGRATION.md` "제거 대상"이 아직 리포에 남아 있다.
  - `deploy/nginx/` 전체(책임 이주 확정 전이라 보류 중 — [`05 §2`](../../architecture/05_3Tier_이전_작업계획.md)에 이주처 표 있음).
  - `apps/webapp/`(Vite 레거시), `apps/homepage/`, `apps/devpage/`.
  - `deploy/ops-jobs/`의 `retention.py`·`log-scrub.py`는 이미 Supabase 대상으로 보이나([`retention.py:31`](../../deploy/ops-jobs/retention.py) `SUPABASE_URL` 사용), 작업계획(Phase 6.1~6.4)은 "미착수"로 표기 — **문서 상태와 코드가 어긋남**.
- **영향**: "무엇이 진짜 현행인지" 파악 비용. 특히 ops-jobs는 코드는 Supabase인데 문서상 미착수라 혼란.
- **조치**: Phase 5(CD 분리)·Phase 6(관측/DR) 착수 시점에, (a) nginx 책임 이주 확정 후 `deploy/nginx/` 제거, (b) Vercel 검증 후 구 `apps/webapp` 제거, (c) ops-jobs가 이미 Supabase 대상이면 **작업계획 상태표를 갱신**해 문서-코드 정합을 맞춘다.

---

## 3. 도메인(엔진) 관련 — 의도된 placeholder와 실제 보완 지점

아래는 **버그가 아니라 명시된 seam**이지만, 실서비스 품질로 가려면 채워야 할 곳이다. 우선순위는 도메인 정확도 관점.

| # | 위치 | 현재 | 보완 제안 |
|---|---|---|---|
| D1 | [`metrics.py:58`](../../services/engine-analysis/app/metrics.py) | 정규화 경계(`_norm`의 lo/hi)가 placeholder 상수. 주석도 "튜닝 대상" | 실측 데이터셋으로 경계 보정. 최소한 나이대·성별 분위수로 정규화 |
| D2 | [`roi.py:10`](../../services/engine-analysis/app/roi.py) | Haar cascade + 실패 시 중앙 60% 크롭 | MediaPipe/dlib 랜드마크 또는 피부 segmentation 마스크로 교체(이마·볼·턱 영역 분리 시 지표 정확도↑) |
| D3 | [`metrics.py:74`](../../services/engine-analysis/app/metrics.py) | `combination`·`sensitivity`가 고정 50.0 + `placeholder` | 설문 미제공 시에도 CV 신호(유분-건조 격차 등)로 약한 추정치를 내거나, 명시적으로 "측정 불가" 상태를 계약에 추가 |
| D4 | [`rules.py:45`](../../services/engine-prescription/app/rules.py) + [`mixes.example.json`](../../services/engine-prescription/app/config/mixes.example.json) | M01~M11/PM01~PM03 슬롯만 매핑, 실제 배합(INCI·함량) 없음. `trigger_grades`는 `보통`/`위험/심각` | 실제 13품목 배합표를 `config/mixes.json`으로 채우고, trigger 기준(등급 경계)을 도메인과 확정. prod는 example fail-fast로 막혀 있으므로 **배포 전 실제 config 필수** |
| D5 | [`model.py:32`](../../services/engine-analysis/app/model.py) | `MLScorer`가 `BaselineScorer` 상속만, 가중치 로드 TODO | GAN 복원(CodeFormer)·ML 스코어러 학습 후 `ENGINE_MODEL=ml`로 전환. `compose.gpu.yml` + 동시성=1 직렬화 유지 |
| D6 | [`survey.py:9`](../../services/engine-prescription/app/survey.py) | 민감성 계수(`70 - 15*flags - 20`) 등이 placeholder | 실제 설문 척도·가중치를 도메인과 확정해 계수 교체 |

---

## 4. 보안·PIPA 추가 제안 (방어 심화)

현재 방어선이 이미 좋지만, 아래는 낮은 비용으로 한 층 더한다.

1. **S4-1. presign 발급과 잡 생성의 결합 강화** — 현재 presign이 발급한 `job_id`와 `/analyze`가 새로 만드는 `job_id`가 다르다([`main.py:316`](../../services/gateway/app/main.py) vs [`main.py:362`](../../services/gateway/app/main.py)). presign 시점의 `job_id`를 `/analyze`가 재사용하도록 하면 "업로드는 했지만 잡이 없는" 고아 객체를 추적하기 쉬워진다. (선택 사항 — 현재도 `image_key` 소유권 검사로 악용은 차단됨.)
2. **S4-2. service role 키 최소 권한화 검토** — gateway/worker가 Supabase `service_role`(RLS 우회)를 쓴다. 설계 리스크(04 §6)에도 "최소 권한 커스텀 role 검토"가 있다. Supabase 커스텀 role + 필요한 테이블/버킷만 grant로 축소를 검토(키 유출 시 피해 반경 축소).
3. **S4-3. 감사 로그** — service role 쓰기(잡 상태 전이·결과 기록·원본 삭제)를 별도 감사 테이블/로그로 남겨, 키 유출 시 행위 추적이 가능하게 한다. `job_events`가 부분적으로 이 역할을 하지만 삭제 행위(retention)는 별도 기록이 없다.

---

## 5. CI/CD·운영 제안

1. **C5-1. 웹 테스트 부재** — `tests.yml`은 Python만. `apps/webapp-next`에 `tsc --noEmit`·`next lint`·(가능하면) 최소 렌더 테스트를 잡는 워크플로가 없다. Vercel이 빌드를 하지만, **타입/린트 오류를 PR 단계에서 잡는** 가벼운 잡 추가를 권장.
2. **C5-2. 배포 워크플로의 monorepo paths 필터 검증** — [`deploy-built-service.yml:16`](../../.github/workflows/deploy-built-service.yml)은 `paths`로 gateway/worker만 트리거하는데, `SERVICE`가 하드코딩(`gateway`)돼 있다. worker 변경 시에도 gateway 이미지를 빌드할 수 있으니, 변경 경로에 따라 `SERVICE`를 매트릭스로 분기하거나, 워크플로를 서비스별로 분리하는 게 안전하다.
3. **C5-3. Makefile smoke가 multipart 전제** — [`Makefile:32`](../../Makefile)의 `smoke`는 `curl -F image=@...`(multipart)로 `/analyze`를 호출한다. `ENABLE_LEGACY_UPLOAD=0`으로 닫는 순간 smoke가 깨진다. presigned 플로우 버전의 smoke 스크립트를 준비해 둔다.
4. **C5-4. 스키마 드리프트 테스트를 실 Supabase에도** — DoD(04 §9)에 `alembic upgrade head` + `test_schema_drift.py` 통과가 있는데, CI 통합 잡은 임시 Postgres라 **Supabase 고유 동작(확장, auth.uid() 등)을 커버하지 못한다**. staging Supabase에 대한 마이그레이션 드라이런 잡을 배포 전 게이트로 추가 고려.

---

## 6. 우선순위 실행 순서 (권장)

| 순서 | 항목 | 이유 | 공수 |
|---|---|---|---|
| 1 | **P0-1** prod `ENV=prod` 추가 | 한 줄, fail-fast 복구. 배포 전 필수 | 5분 |
| 2 | **P1-1·P1-2** SW 캐시 규칙 보완(PUT + 교차 오리진) | PIPA 직결. Vercel 배포 전에 확정 | 30분 |
| 3 | **P2-1** requirements-dev 정합 | CI 사전 파손 방지 | 10분 |
| 4 | **P2-2** redis 의존 제거 | 이미지 슬림화 | 5분 |
| 5 | **D4** 실제 믹스 config 채우기 | prod fail-fast 때문에 **배포 블로커** | 도메인 의존 |
| 6 | **P1-3** presigned E2E + RLS 검증 테스트 | Phase 4 완료 조건·DoD를 코드로 고정 | 1~2일 |
| 7 | **C5-2** 배포 워크플로 SERVICE 분기 | 잘못된 이미지 배포 방지 | 반일 |
| 8 | **P2-3·P2-4** 문서 링크 치환 + 제거 자산 정리 | 신규 합류자 온볍딩 비용 절감 | 반일~1일 |
| 9 | **D1~D6** 도메인 정확도 | 인프라와 직교, 실서비스 품질 | 지속 과제 |

---

## 7. 총평

**설계·문서·배선의 정합성이 매우 높은 코드베이스**다. 특히 ① fail-fast 인증, ② presigned 심층 방어 체인, ③ 큐 안정성(재시도·리퍼·데드레터), ④ 계약 드리프트 CI 가드는 실전 감각이 좋다. 문서가 "코드 완료/외부 작업/미착수"를 정직하게 구분하고 있어 현재 위치 파악이 쉽다.

**지금 당장 고칠 것은 사실상 P0-1(prod `ENV`) 한 건**이고, PIPA 관점에서 SW 캐시 규칙(P1-1·P1-2)을 Vercel 배포 전에 확정하면 된다. 나머지는 3-Tier 이전의 마지막 마일(실배포·E2E·제거)과 도메인 정확도(D1~D6)로, 이미 로드맵에 잡혀 있는 작업의 연장선이다.

> 다음 한 걸음은 로드맵이 가리키는 대로 **3-Tier Phase 1 실배포(Supabase 프로젝트 생성·`.env` 실값)** 이고, 그 직전에 위 §2의 P0-1·P1-1·P1-2를 반영하면 된다.
