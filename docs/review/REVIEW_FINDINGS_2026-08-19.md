# 코드베이스 전수 리뷰 — 2차 검수 (2026-08-19)

> **후속 해결 기록**: [`RESOLUTIONS_2026-08-19.md`](./RESOLUTIONS_2026-08-19.md) — P1-1·P1-2·P2-1·P2-2·N1·N2·N4 반영 완료.
>
> 목적: 1차 리뷰([`archive/REVIEW_FINDINGS_2026-08-18.md`](./archive/REVIEW_FINDINGS_2026-08-18.md), 2026-08-18) 이후 **전 영역을 다시 읽고**
> ① 이전 지적이 해결됐는지 검증하고, ② 새로 발견한 이슈를 추가한다.
> 각 항목은 코드·설정 파일의 **실제 근거**를 링크로 단다. 우선순위는 기존 관례(P0/P1/P2)를 따른다.
>
> 리뷰 범위: `services/{gateway,worker,engine-*}` · `apps/webapp-next` · `deploy/{compose,caddy,env,supabase,db,ops-jobs}` · `.github/workflows` · `tests` · `packages/common`.

---

## 0. 한눈에 보는 판정

| 축 | 상태 | 한 줄 평가 |
|---|---|---|
| 설계·문서 | ✅ 매우 양호 | 3-Tier 설계 정본·런북·로드맵이 코드와 정합. "완료/미착수"를 정직하게 구분 |
| 보안(인증·RLS·격리) | ✅ 양호 | fail-fast 인증·JWT 이중 검증·RLS·폐쇄망 엔진·presigned 심층 방어 유지 |
| 안정성(큐·재시도·풀링) | ✅ 양호 | SKIP LOCKED·backoff·stale reaper·데드레터·풀·임시파일 정리 모두 정상 동작 |
| 3-Tier 이전 | 🟡 코드 완료 | Phase 1~4 코드 완료. 남은 것은 실배포·E2E·제거(이전과 동일) |
| PIPA(캐시 정책) | ✅ 해결(2026-08-19 후속) | **P1-1·P1-2 반영 완료** — SW PUT/DELETE + 교차 오리진 NetworkOnly 명시 |
| CI 위생 | ✅ 해결(2026-08-19 후속) | **P2-1·P2-2 반영 완료** — `requirements-dev.txt` 핀·psycopg-pool/pyjwt 추가, redis 제거 |
| 도메인(엔진) | 🟡 의도된 placeholder | 정규화 상수·실배합은 seam. 단, **config 예시가 비어있어 prod 가 사실상 부팅 불가**(신규 N3) |
| 테스트 | 🟡 양호하나 공백 | 드리프트 가드·스토리지 mock 우수. presigned E2E·RLS 검증 여전히 부재 |

---

## 1. 이전 지적 — 해결 여부 검증

| # | 항목 | 상태 | 근거 |
|---|---|---|---|
| P0-1 | prod/staging gateway `ENV` 명시 | ✅ **해결** | [`compose.prod.yml:17`](../../deploy/compose/compose.prod.yml) `ENV: prod`, [`compose.staging.yml:14`](../../deploy/compose/compose.staging.yml) `ENV: staging` |
| P1-1 | SW Supabase `PUT` NetworkOnly 누락 | ✅ **해결(후속)** | [`next.config.mjs`](../../apps/webapp-next/next.config.mjs) — `/api`·`*.supabase.co` 양쪽에 PUT/DELETE NetworkOnly 추가 |
| P1-2 | `NEXT_PUBLIC_AI_API_BASE` 절대 URL 과 SW `/api` 상대 패턴 불일치 | ✅ **해결(후속)** | [`next.config.mjs`](../../apps/webapp-next/next.config.mjs) — `url.pathname.startsWith("/api/")` 함수 패턴으로 교차 오리진 NetworkOnly 추가 |
| P1-3 | presigned E2E·RLS 검증 테스트 부재 | 🔴 **미해결** | `tests/integration/` 에 presigned 플로우·RLS SQL 검증 없음 ([`test_pipeline.py`](../../tests/integration/test_pipeline.py) 는 multipart 경로만) |
| P2-1 | `requirements-dev.txt` 불일치·미핀·psycopg_pool 누락 | ✅ **해결(후속)** | [`requirements-dev.txt`](../../requirements-dev.txt) — 전 의존 핀 고정 + `psycopg-pool==3.2.4`·`pyjwt==2.10.1` 추가 |
| P2-2 | `redis` 의존 선반영 | ✅ **해결(후속)** | [`gateway/requirements.txt`](../../services/gateway/requirements.txt) — 미사용 `redis==5.2.1` 제거(큐는 Postgres SKIP LOCKED) |
| P2-3 | docs 옛 경로 링크 | 🟡 진행 중 | [`README.md:152`](../../README.md) 가 자체적으로 인지. 일괄 치환 미실행 |
| P2-4 | 제거 예정 자산(nginx·webapp·homepage·devpage) | 🟡 부분 | 여전히 리포에 존재. ops-jobs 는 Supabase 대상으로 동작하나 작업계획 상태표는 "미착수" |

> **요약**: P0-1·P1-1·P1-2·P2-1·P2-2 해결. 남은 것은 presigned E2E·RLS 검증 공백(P1-3) 과 P2-3·P2-4 정리다.

---

## 2. 신규 발견 이슈 (이번 리뷰에서 추가)

### N1. (P2) `presign` ↔ `analyze` job_id 분리 — 고아 업로드 추적 불가 — ✅ **해결(2026-08-19 후속)**
- **증상**: [`main.py:316`](../../services/gateway/app/main.py) presign 이 `job_id`(A) 를 만들어 `image_key` 에 박지만, [`main.py:362`](../../services/gateway/app/main.py) `/analyze` 는 **새 `job_id`(B)** 를 발급해 잡을 등록한다. 응답의 `job_id` 는 B.
- **영향**: 스토리지의 객체 키(A) 와 DB 잡(B) 이 서로 다른 UUID 를 쓴다. "업로드는 됐는데 잡이 없는" 고아 객체를 조인으로 찾을 방법이 없고, retention 잡([`retention.py`](../../deploy/ops-jobs/retention.py)) 도 `image_key` 로만 추적해 A↔B 불일치를 메우지 못한다. 장애 분석·정합성 감사가 어려워진다.
- **조치(반영 완료)**: presign 이 발급한 `job_id` 를 `/analyze` 가 재사용하도록 반영. `/analyze` 는 `image_key` 두 번째 조각의 `job_id` 를 잡 id 로 쓰고, 클라이언트가 `job_id` 를 명시하면 키와 일치하는지 검증해 키-잡 결합을 강제한다([`main.py`](../../services/gateway/app/main.py)). 웹앱 `analyze()` 도 presign 의 `job_id` 를 그대로 되돌려 본낸다([`api.ts`](../../apps/webapp-next/src/lib/api.ts)). 기존 `image_key` 소유권 검사로 보안 회귀는 없다.

### N2. (P2) `authHeaders()` 가 세션 없으면 무인증 헤더로 진행 — 실패가 늦게 표면화 — ✅ **해결(2026-08-19 후속)**
- **증상**: [`api.ts:26-30`](../../apps/webapp-next/src/lib/api.ts) 는 토큰이 없으면 빈 헤더 `{}` 를 반환한다. `analyze()`([`api.ts:46`](../../apps/webapp-next/src/lib/api.ts))·`getJob()` 모두 이를 그대로 쓴다.
- **영향**: 세션 만료/로그아웃 상태에서 호출하면 401 이 되는데, 원인이 "토큰 없음"인지 "서버 거부"인지 구분이 안 돼 UX/디버깅이 나빠진다. 엄밀한 버그는 아니나 방어적 코딩 관점에서 개선 여지.
- **조치(반영 완료)**: 토큰 부재 시 즉시 명확한 에러를 던지도록 반영. `authHeaders()` 가 세션 토큰이 없으면 `AuthRequiredError("로그인이 필요합니다")` 를 throw 해 실패를 빠르게 표면화한다([`api.ts`](../../apps/webapp-next/src/lib/api.ts)).

### N3. (P2) `mixes.example.json` — 실제 배합 없이 코드 슬롯만, prod 는 fail-fast 로 차단됨 (확인 완료)
- **확인 결과**: [`mixes.example.json`](../../services/engine-prescription/app/config/mixes.example.json) 은 `base_mixes: ["M01","M02"]` + 지표별 M 코드 + PCR PM 코드를 갖춰 **dev/staging 에서 `selected_mixes` 가 비지 않음**을 보장한다. 통합 테스트의 `selected_mixes >= 1` 단언([`test_pipeline.py:68-71`](../../tests/integration/test_pipeline.py))과 충돌하지 않는다.
- **실제 리스크**: 이 파일은 `_note` 가 명시하듯 "실제 배합/선택 규칙은 13품목 엑셀에서 채운다"는 placeholder 다. prod 는 [`rules.py:33-37`](../../services/engine-prescription/app/rules.py) 의 fail-fast 로 example 사용이 차단되므로, **실서비스에는 실제 `config/mixes.json` 마운트/커밋이 선행 조건**이다(기존 D4 와 동일).
- **조치**: D4(실제 배합표) 해결 시 함께 정리. 추가 조치 불필요.

### N4. (P2) 통합 테스트 `finish_ok` 미커버 — `ON CONFLICT DO NOTHING` 재처리 경로 — ✅ **해결(2026-08-19 후속)**
- **증상**: [`test_pipeline.py`](../../tests/integration/test_pipeline.py) 는 정상 1회 처리만 검증한다. [`worker.py:205-213`](../../services/worker/worker.py) 의 `ON CONFLICT (job_id) DO NOTHING`(재처리 시 중복 처방 방지) 는 **두 번 처리되는 경로**에서만 발동하는데, 이를 치는 테스트가 없다.
- **영향**: 재처리(재큐 후 재성공) 시 prescriptions 가 중복 삽입되지 않는다는 핵심 보장이 회귀 가드 없이 열여 있다.
- **조치(반영 완료)**: 통합 테스트에 `test_finish_ok_reprocess_dedup` 추가 — 같은 잡을 두 번 `finish_ok` 처리하고 prescriptions 가 1건임을 단언해 `ON CONFLICT` 중복 방지를 가드한다([`test_pipeline.py`](../../tests/integration/test_pipeline.py)).

### N5. (P2) `_presign_hits` 인메모리 레이트리밋 — 단일 레플리카 전제가 주석에만 존재
- **증상**: [`main.py:74-86`](../../services/gateway/app/main.py) 의 슬라이딩 윈도우는 프로세스 인메모리다. 주석([`main.py:75`](../../services/gateway/app/main.py))은 "1 레플리카 전제, 다중화 시 Redis 이관"이라 명시하지만, Phase 5(수평 확장)에서 레플리카를 늘리는 순간 **사용자당 상한이 레플리카 수만큼 배로 늘어난다**.
- **영향**: 지금은 문제없으나, 확장 시 조용히 상한이 무력화된다.
- **조치**: 지금 당장 고칠 필요는 없고, Phase 5 착수 시 Redis 이관을 체크리스트에 명시(이미 로드맵 [`00_PHASE_ROADMAP.md`](../roadmap/00_PHASE_ROADMAP.md) Phase 5 에 해당).

---

## 3. 강점 (유지 — 재확인됨)

1. **fail-fast 인증** — [`main.py:47`](../../services/gateway/app/main.py) prod 에서 `AUTH_MODE!=strict` 기동 거부.
2. **JWT 이중 검증** — [`main.py:189-193`](../../services/gateway/app/main.py) `aud` + `iss` 고정.
3. **presigned 심층 방어 체인** — gateway(content-type·크기·만료·레이트리밋) → 버킷(`file_size_limit`·MIME, [`0001_rls_and_storage.sql:23`](../../deploy/supabase/policies/0001_rls_and_storage.sql)) → worker(magic-byte, [`worker.py:52-65`](../../services/worker/worker.py)) → 스트리밍 상한([`storage.py:88-95`](../../services/worker/storage.py)).
4. **큐 안정성** — SKIP LOCKED 클레임([`worker.py:100`](../../services/worker/worker.py)), 재시도+backoff, stale reaper, `is_retryable` 구분, `ON CONFLICT` 중복 방지.
5. **자원 누수 방지** — 임시파일 `finally` 정리 + `is_temp` 구분([`worker.py:185-193`](../../services/worker/worker.py)). 실패 경로도 정리([`storage.py:96-102`](../../services/worker/storage.py)).
6. **계약 드리프트 가드** — [`test_contract.py:41-72`](../../tests/common/test_contract.py) 등급표·10지표·응답 필드 superset 을 CI 강제.
7. **컨테이너 하드닝** — 비루트([`Dockerfile:7-8`](../../services/gateway/Dockerfile)), `no-new-privileges`·`cap_drop: ALL`·`read_only`·tmpfs·리소스 상한([`compose.base.yml:55-60`](../../deploy/compose/compose.base.yml)).
8. **prod 부팅 안전장치** — 처방 엔진 `ENV=prod` example config fail-fast([`rules.py:33-37`](../../services/engine-prescription/app/rules.py)).
9. **RLS 심층 방어** — `force row level security` + 소유자 정책 + `job_events` 상위 소유권 EXISTS 바인딩([`0001_rls_and_storage.sql:91-108`](../../deploy/supabase/policies/0001_rls_and_storage.sql)).
10. **PIPA 인지 설계** — 브라우저→Supabase 직결 PUT, 토큰 메모리 only, SW NetworkOnly 의도 명시(구현 보완만 남음).

---

## 4. 도메인(엔진) — 의도된 placeholder (재확인, 변경 없음)

| # | 위치 | 현재 | 보완 지점 |
|---|---|---|---|
| D1 | [`metrics.py:11-15`](../../services/engine-analysis/app/metrics.py) | `_norm` 경계가 placeholder 상수 | 실측 데이터셋 분위수로 보정 |
| D2 | [`roi.py:10-28`](../../services/engine-analysis/app/roi.py) | Haar + 중앙 60% 폴리 | MediaPipe/dlib 랜드마크·segmentation 교체 |
| D3 | [`metrics.py:74-75`](../../services/engine-analysis/app/metrics.py) | `combination`·`sensitivity` 고정 50.0 placeholder | CV 약한 추정 또는 "측정 불가" 계약 추가 |
| D4 | [`rules.py`](../../services/engine-prescription/app/rules.py)+[`mixes.example.json`](../../services/engine-prescription/app/config/mixes.example.json) | M01~M11/PM01~PM03 슬롯만 | **실제 13품목 배합표 `config/mixes.json` 필수(prod 블로커)** |
| D5 | [`model.py:32-38`](../../services/engine-analysis/app/model.py) | `MLScorer` 가중치 TODO | GAN/ML 학습 후 `ENGINE_MODEL=ml` 전환 |
| D6 | [`survey.py:19-29`](../../services/engine-prescription/app/survey.py) | 민감성 계수 placeholder | 실제 설문 척도·가중 확정 |

---

## 5. 우선순위 실행 순서 (갱신)

> ✅ **2026-08-19 후속 반영**: P1-1·P1-2·P2-1·P2-2·N1·N2·N4 는 코드 반영 완료(아래 "해결" 표기). 남은 항목만 순서를 유지한다.

| 순서 | 항목 | 이유 | 공수 |
|---|---|---|---|
| ~~1~~ | ✅ **P1-1·P1-2** SW 캐시 규칙(PUT/DELETE + 교차 오리진 NetworkOnly) | PIPA 직결. Vercel 배포 전 필수 — **해결** | 30분 |
| ~~2~~ | ✅ **P2-1** `requirements-dev.txt` 정합(psycopg-pool·pyjwt 추가 + 핀) | CI 사전 파손 방지 — **해결** | 10분 |
| ~~3~~ | ✅ **P2-2** `redis` 의존 제거 | 이미지 슬림화 — **해결** | 5분 |
| 4 | **D4** 실제 믹스 config 채우기 | prod fail-fast **배포 블로커** | 도메인 의존 |
| 5 | **P1-3** presigned E2E + RLS 검증 테스트 | Phase 4 완료 조건·DoD 코드 고정 | 1~2일 |
| ~~6~~ | ✅ **N4** `finish_ok` 재처리 통합 테스트 | `ON CONFLICT` 중복 방지 회귀 가드 — **해결** | 반일 |
| ~~7~~ | ✅ **N1** presign/analyze job_id 결합 | 고아 업로드 추적성 — **해결** | 반일 |
| 8 | **C5-2**(이전) 배포 워크플로 SERVICE 분기 | 잘못된 이미지 배포 방지 | 반일 |
| 9 | **N3·N5** + P2-3·P2-4 | UX·정리·확장 대비 (N2 해결) | 지속 |

---

## 6. 총평

1차 리뷰 이후 **P0-1(prod ENV) 이 해결**돼 운영 부팅 안전장치는 복구됐다. **2026-08-19 후속 커밋에서 PIPA 캐시 규칙(P1-1·P1-2)·CI 위생(P2-1·P2-2) 그리고 신규 P2 중 N1·N2·N4 까지 모두 반영 완료**됐다. 단위 테스트 96건 통과·TypeScript 컴파일 클린으로 검증했다.

- **PIPA**: SW 가 `/api`·`*.supabase.co` 양쪽의 PUT/DELETE 와 교차 오리진 `/api/*` 를 NetworkOnly 로 명시 차단([`next.config.mjs`](../../apps/webapp-next/next.config.mjs)).
- **CI 위생**: `requirements-dev.txt` 전 의존 핀 + `psycopg-pool`·`pyjwt` 추가, gateway 미사용 `redis` 제거.
- **N1**: `/analyze` 가 `image_key` 의 `job_id` 를 재사용하고 명시 `job_id` 는 키와 일치 검증 — 키-잡 결합으로 고아 업로드 추적성 확보.
- **N2**: `authHeaders()` 가 토큰 부재 시 `AuthRequiredError` 를 즉시 throw.
- **N4**: `test_finish_ok_reprocess_dedup` 통합 테스트로 `ON CONFLICT` 중복 방지 가드.

새로 발견한 이슈 중 남은 것은 N3(의도된 placeholder, 추가 조치 불필요)와 N5(Phase 5 확장 시 Redis 이관 — 로드맵 항목) 뿐이다.

**지금 당장의 실행 항목은 변함없이**: 3-Tier Phase 1 실배포(Supabase 프로젝트 생성·`.env` 실값)가 최우선이다. P1-1·P1-2·P2-1·P2-2 는 이미 반영됐으므로 배포 전 차단 요소는 아니다. 남은 코드 작업은 **P1-3(presigned E2E·RLS 검증)** 이며, **C5-2(배포 워크플로 SERVICE 분기)는 matrix + paths-filter 로 해결됨**. 도메인(D4 실제 믹스표)은 prod fail-fast 때문에 배포 블로커이므로 병행 착수가 필요하다.
