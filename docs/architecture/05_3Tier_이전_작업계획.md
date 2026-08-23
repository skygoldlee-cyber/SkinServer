# 3-Tier(Vercel·Supabase·AI Server) 이전 작업계획

> 대상 문서: [`04_3Tier_Vercel_Supabase_AIServer_설계.md`](./04_3Tier_Vercel_Supabase_AIServer_설계.md)
> 목적: 현재 monorepo(nginx 엣지 + 로컬/자체호스팅 DB 혼용)를
> **Vercel(웹) + Supabase(데이터) + AI Server(엔진)** 구조로 이전하기 위해
> **무엇을, 어느 파일을, 어떤 순서로** 수정해야 하는지 실행 단위로 정리한다.
>
> 이 문서는 "작업계획"이다. 실제 코드 수정은 별도 패치/PR로 내린다.

---

## 0.5 구현 상태 스냅샷 (2026-08-18 기준)

> 각 작업 항목에 상태 마커를 부여했다. ✅ 코드 완료 · 🟡 코드 완료/배포·검증 미완 · ⬜ 미착수
> **핵심 결론: Phase 1~4의 "코드 수정"은 거의 완료됐고, 남은 것은 Supabase·Vercel 실배포/외부 연동과 E2E 검증이다.**

| Phase | 코드 상태 | 남은 것 |
|---|---|---|
| **1 — Supabase 정렬** | 🟡 코드 완료 | Supabase 프로젝트 생성·마이그레이션·RLS 적용·`.env` 실값 전환(외부 작업) |
| **2 — 웹 포팅** | 🟡 코드 완료 | Vercel 프로젝트 연결·환경변수·PWA 검증·구 `apps/webapp` 제거 |
| **3 — AI Server 슬림화** | ✅ 거의 완료 | 배포 스크립트 웹 서비스 정리(3.8) |
| **4 — presigned 전환** | 🟡 코드 완료 | E2E 검증 → `ENABLE_LEGACY_UPLOAD=0` |
| **5 — CD 분리** | ⬜ 미착수 | 웹 워크플로 제거·deploy.sh 정리·배포 순서 런북 |
| **6 — 관측/DR 이관** | 🟡 코드 Supabase 전환 완료 | cron 배선·실제 복구 리허설 1회 실행(운영) |

**다음 한 걸음(가장 먼저)**: Phase 1 실배포 — Supabase 프로젝트 생성과 실제 연결. 이것 없이는 로컬 개발도 동작하지 않는다.

---

## 0. 한눈에 보는 갭 분석

| 축 | 설계(04) 목표 | 현재 코드 상태 | 갭 |
|---|---|---|---|
| 웹 표면 | Next.js PWA on Vercel | Vite SPA + nginx 정적 서빙([`apps/webapp`](../../apps/webapp)) | 프레임워크 이전 + 호스팅 이전 |
| 엣지 | Vercel(웹) + Caddy(AI Server 443) | nginx 80 + Caddy TLS(예정)([`compose.base.yml`](../../deploy/compose/compose.base.yml)) | nginx 정적 3종 제거, Caddy는 AI Server만 |
| 데이터 | 전 환경 Supabase | dev/staging=로컬 pg, prod=Supabase(예정) | 로컬 pg 제거, Supabase 프로젝트 정렬 |
| 스토리지 | Supabase Storage(presigned) | 로컬 볼륨 `storage:` + [`storage.py`](../../services/gateway/app/storage.py) seam | SupabaseStorage 실구현 + presigned 플로우 |
| 인증 | 브라우저→Supabase 직결, AI Server는 JWT 검증만 | 동일([`main.py`](../../services/gateway/app/main.py)) | CORS 추가 필요(오리진 분리) |
| 게이트웨이 | 얇은 BFF(잡 생성/조회) | 풀 업로드 + 잡 관리([`main.py`](../../services/gateway/app/main.py)) | `/analyze`를 presigned 방식으로 축소 |
| CI/CD | 웹=Vercel 자동, AI Server=GH Actions | GH Actions → self-hosted → deploy.sh | 웹 배포 분리, AI Server만 배포 스크립트 유지 |

---

## 1. Phase별 작업 분해

### Phase 1 — Supabase 정렬 (선행)

**목표**: dev/staging/prod 모두 Supabase 프로젝트로 통일, 로컬 postgres 제거.

| # | 작업 | 대상 파일 | 비고 | 상태 |
|---|------|-----------|------|------|
| 1.1 | Supabase 프로젝트 생성(`skinlens-dev`/`skinlens-prod`) | (외부) Supabase 콘솔 | 스키마 동일, 데이터 분리 | ⬜ 외부 작업 — [런북](../operations/09_Phase1_Supabase_실행런북.md) |
| 1.2 | DB 마이그레이션 적용 | [`deploy/db/migrations/0001_init.sql`](../../deploy/db/migrations/0001_init.sql) | Supabase SQL Editor 또는 `psql $DATABASE_URL` | ⬜ 외부 작업 |
| 1.3 | RLS/Storage 정책 적용 | [`deploy/supabase/policies/0001_rls_and_storage.sql`](../../deploy/supabase/policies/0001_rls_and_storage.sql) | `jobs`/`job_events`/`prescriptions`/`storage.objects` | ⬜ 외부 작업 |
| 1.4 | **버킷 이름을 `skin-images`로 통일 (P1, 실제 버그)** | [`services/gateway/app/storage.py`](../../services/gateway/app/storage.py) `STORAGE_BUCKET` 기본값 `uploads`→`skin-images`, [`04 §2.2`](./04_3Tier_Vercel_Supabase_AIServer_설계.md) 버킷 서술 `uploads`→`skin-images` | 소스 오브 트루스인 RLS 정책·[`retention.py`](../../deploy/ops-jobs/retention.py)·[`.env.example`](../../deploy/env/.env.example)·worker [`storage.py`](../../services/worker/storage.py)는 모두 `skin-images`. gateway만 `uploads`라 presigned가 정책 밖 버킷으로 새거나 실패함 | ✅ 완료 — [`storage.py:42`](../../services/gateway/app/storage.py) 기본값 `skin-images` |
| 1.5 | `DATABASE_URL`을 Supabase로 전환 | `deploy/env/.env` | dev/staging/prod 모두 동일 패턴 | 🟡 코드는 Supabase 필수값화 완료([`compose.base.yml`](../../deploy/compose/compose.base.yml)), **`.env` 실값 전환은 외부 작업** |
| 1.6 | 로컬 `db` 서비스 제거 | [`compose.dev.yml`](../../deploy/compose/compose.dev.yml), [`compose.staging.yml`](../../deploy/compose/compose.staging.yml) | `pgdata` 볼륨도 제거 | ✅ 완료 — [`compose.dev.yml`](../../deploy/compose/compose.dev.yml) 로컬 db 없음·Supabase 사용 |
| 1.7 | `storage.py` Supabase seam 실구현 — **두 파일 모두** | gateway [`services/gateway/app/storage.py`](../../services/gateway/app/storage.py) (`save`/`local_path`/`SupabaseStorage`), worker [`services/worker/storage.py`](../../services/worker/storage.py) (`resolve_local`/`_Supabase`) | 빌드 컨텍스트가 분리돼 별도 사본, 클래스명·메서드 계약이 다름. `supabase-py` 또는 직접 REST, presigned URL 발급/서명 URL fetch | ✅ 완료 — gateway [`SupabaseStorage`](../../services/gateway/app/storage.py) 실구현(presigned 발급/서명 URL) |
| 1.8 | `ops-jobs` 연결 문자열 교체 | [`deploy/ops-jobs/retention.py`](../../deploy/ops-jobs/retention.py), [`log-scrub.py`](../../deploy/ops-jobs/log-scrub.py) | 대상이 Supabase로 변경 | ⬜ 미착수 |

**완료 조건**: `supabase start` 없이도 로컬 개발이 Supabase dev 프로젝트로 동작.
**현재**: 코드는 Supabase 전제로 배선 완료(1.4/1.6/1.7). **실제 Supabase 프로젝트 생성·마이그레이션·RLS·`.env` 실값(1.1/1.2/1.3/1.5)이 남은 외부 작업**이다.

---

### Phase 2 — 웹 포팅 (Vite → Next.js PWA → Vercel)

**목표**: `apps/webapp`을 Next.js(App Router) + PWA로 이전하고 Vercel에 배포.

| # | 작업 | 대상 파일 | 비고 | 상태 |
|---|------|-----------|------|------|
| 2.1 | Next.js 프로젝트 신규 생성 | `apps/webapp-next/` (또는 `apps/webapp` 교체) | `npx create-next-app@latest --typescript --tailwind --app` | ✅ 완료 — [`apps/webapp-next/`](../../apps/webapp-next) 존재 |
| 2.2 | 기존 컴포넌트 이전 | [`Analyze.tsx`](../../apps/webapp-next/src/components/Analyze.tsx), [`Login.tsx`](../../apps/webapp-next/src/components/Login.tsx), [`SurveyForm.tsx`](../../apps/webapp-next/src/components/SurveyForm.tsx) | `app/` 라우터 구조로 재배치 | ✅ 완료 |
| 2.3 | API 클라이언트 이전 | [`api.ts`](../../apps/webapp-next/src/lib/api.ts), [`supabase.ts`](../../apps/webapp-next/src/lib/supabase.ts) | `VITE_*` → `NEXT_PUBLIC_*` 환경변수명 변경 | ✅ 완료 |
| 2.4 | PWA 설정 이전 | [`vite.config.ts`](../../apps/webapp/vite.config.ts) → `next.config.mjs` + `next-pwa` | 앱셸만 precache, `/api`·Supabase NetworkOnly 유지 | ✅ 완료 — [`manifest.ts`](../../apps/webapp-next/src/app/manifest.ts), `public/sw.js` 존재 |
| 2.5 | Vercel 프로젝트 연결 | (외부) Vercel 대시보드 | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_AI_API_BASE` 설정 | ⬜ 외부 작업 |
| 2.6 | 서비스워커 캐시 규칙 검증 | `next.config.mjs` | PIPA: 사진·결과·토큰 미캐시 | 🟡 코드 배선 완료, **Vercel Preview 실검증 필요** |
| 2.7 | 기존 `apps/webapp` 아카이브/삭제 | `apps/webapp/` | 이전 완료 후 제거 | ⬜ 미착수 — Vercel 검증 후 제거 |

**완료 조건**: Vercel Preview에서 PWA 설치·오프라인 앱셸 동작, `/api` 호출은 AI Server로 직결.
**현재**: 코드 이전 완료(2.1~2.4). **Vercel 연결·환경변수(2.5)와 실검증(2.6), 구앱 제거(2.7)가 남았다.**

---

### Phase 3 — AI Server 슬림화

**목표**: compose에서 nginx/정적 서비스 제거, gateway를 얇은 BFF로 축소, Caddy는 AI Server만.

| # | 작업 | 대상 파일 | 비고 | 상태 |
|---|------|-----------|------|------|
| 3.1 | **CORS 허용 오리진 추가 (Vercel Preview 언블록, P0)** | [`services/gateway/app/main.py`](../../services/gateway/app/main.py) | Vercel 도메인 명시, `CORSMiddleware` 추가. Phase 2/3 병렬 구조에서 웹이 Vercel 오리진에서 AI Server를 처음 호출하는 순간 CORS 없으면 즉시 실패 — 5줄 변경이므로 맨 앞으로 당김 | ✅ 완료 — [`main.py:141`](../../services/gateway/app/main.py) `CORSMiddleware` + `CORS_ORIGINS` |
| 3.2 | `frontnet` 네트워크 제거 | [`compose.base.yml`](../../deploy/compose/compose.base.yml) | gateway는 `appnet`+`enginenet`만 | ✅ 완료 — [`compose.base.yml:20`](../../deploy/compose/compose.base.yml) `appnet`/`enginenet`만 |
| 3.3 | `nginx`/`homepage`/`devpage`/`webapp` 서비스 제거 | [`compose.base.yml`](../../deploy/compose/compose.base.yml) | 정적 서빙은 Vercel로 이관 | ✅ 완료 — compose에 gateway/worker/engine-*만 |
| 3.4 | `storage` 볼륨 제거 | [`compose.base.yml`](../../deploy/compose/compose.base.yml) | Supabase Storage로 대체 | ✅ 완료 — `storage` 볼륨 없음 |
| 3.5 | `gateway` 환경변수 정리 | [`compose.base.yml`](../../deploy/compose/compose.base.yml), [`compose.prod.yml`](../../deploy/compose/compose.prod.yml) | `STORAGE_BACKEND=supabase`, `SUPABASE_SERVICE_ROLE_KEY` 추가 | ✅ 완료 — `STORAGE_BACKEND=supabase`·`SUPABASE_*` 배선 |
| 3.6 | **Caddy를 AI Server 전용으로 재배선 (P0 — 그대로 진행하면 엣지 사망)** | [`deploy/caddy/Caddyfile`](../../deploy/caddy/Caddyfile), [`compose.tls.yml`](../../deploy/compose/compose.tls.yml) | ① 업스트림 교체: `reverse_proxy nginx:80` → `reverse_proxy gateway:8000` (nginx 제거 후 프록시 대상 소멸). ② 네트워크 재배선: `frontnet` 제거 후 Caddy와 gateway가 서로 다른 네트워크에 남아 502 — Caddy를 `appnet`에 올리거나 전용 `edgenet`을 gateway와 공유. ③ `api.example.com`만 프록시, 웹 도메인 제거 | ✅ 완료 — [`Caddyfile:20`](../../deploy/caddy/Caddyfile) `reverse_proxy gateway:8000`, `api.example.com`만 |
| 3.7 | 스테이징 TLS 오버레이 동기화 + CRLF 정규화 | [`Caddyfile.staging`](../../deploy/caddy/Caddyfile.staging), [`compose.staging-tls.yml`](../../deploy/compose/compose.staging-tls.yml) | 동일하게 업스트림을 gateway로 교체 + 네트워크 재배선. `compose.staging-tls.yml`은 CRLF 라인엔딩 — LF로 정규화 | ✅ 완료 — [`Caddyfile.staging:22`](../../deploy/caddy/Caddyfile.staging) `reverse_proxy gateway:8000` |
| 3.8 | `deploy.sh`에서 웹 관련 서비스 제거 | [`deploy/scripts/deploy.sh`](../../deploy/scripts/deploy.sh) | `WEBAPP_IMAGE` 등 정적 이미지 변수 정리 | ⬜ 미착수 — Phase 5.3과 함께 정리 |

**완료 조건**: `docker compose -f compose.base.yml -f compose.prod.yml up` 시 gateway/worker/engine-*만 기동.
**현재**: 3.1~3.7 완료. **3.8(deploy.sh 웹 서비스 정리)도 완료** — `deploy.sh`에 `WEBAPP_IMAGE` 없음, Phase 5.3과 함께 종결.

---

### Phase 4 — presigned 업로드 전환

**목표**: 브라우저가 Supabase Storage에 직접 업로드, gateway는 `image_key`만 받아 잡 생성.

> **Phase 4는 계획이 그리는 것보다 작다.** `jobs` 테이블에 이미 `image_key` 컬럼이 있고([`main.py` DDL](../../services/gateway/app/main.py)), gateway가 이미 그 키를 생성하며, worker도 이미 `image_key`/`resolve_local`로 동작한다. 데이터 모델 변경이 없으므로 Phase 4는 사실상 `/uploads/presign` 추가 + `/analyze`를 `image_key` 수신으로 전환 + Supabase seam 2곳 구현이 전부다.

| # | 작업 | 대상 파일 | 비고 | 상태 |
|---|------|-----------|------|------|
| 4.1 | `POST /uploads/presign` 엔드포인트 추가 | [`services/gateway/app/main.py`](../../services/gateway/app/main.py) | `image_key` 생성 → Supabase presigned URL 반환 | ✅ 완료 — [`main.py:254`](../../services/gateway/app/main.py) |
| 4.2 | `POST /analyze` 수정 | [`services/gateway/app/main.py`](../../services/gateway/app/main.py) | `multipart` 대신 `image_key` + `survey` JSON 본문 | ✅ 완료 — [`main.py:319`](../../services/gateway/app/main.py) `image_key` 경로 + 소유권/키 형식 방어 |
| 4.3 | 구 multipart 업로드 feature flag | [`services/gateway/app/main.py`](../../services/gateway/app/main.py) | `ENABLE_LEGACY_UPLOAD=1`로 초기 호환 유지 | ✅ 완료 — [`main.py:52`](../../services/gateway/app/main.py) 플래그 + 410 폐기 경로 |
| 4.4 | 웹에서 presigned 업로드 플로우 구현 | [`apps/webapp-next/src/lib/api.ts`](../../apps/webapp-next/src/lib/api.ts) | Next.js 앱. 1) presign → 2) Storage PUT → 3) `/analyze { image_key }` | ✅ 완료 — [`api.ts:48`](../../apps/webapp-next/src/lib/api.ts) presign→PUT→analyze 3단 플로우 |
| 4.5 | `worker`에서 서명 URL로 원본 fetch | [`services/worker/worker.py`](../../services/worker/worker.py) | 실제 worker 계약에 맞춤: `_Supabase.resolve_local(image_key)` → 로컬경로\|None. `storage.local_path()` 대신 서명 URL fetch | ✅ 완료 — [`storage.py:55`](../../services/worker/storage.py) `resolve_local` → `_signed_url` fetch → 임시파일 |
| 4.6 | **worker에서 magic-byte 재검증 (P0 — 이 스텝 없으면 서버 검증이 증발)** | [`services/worker/worker.py`](../../services/worker/worker.py) | presigned 전환 시 브라우저가 Supabase Storage에 직접 PUT하고 gateway는 `image_key`만 받으므로, 현재 [`validate_image()`](../../services/gateway/app/main.py)가 서버에서 하던 MIME/실제 바이트 시그니처 불일치 검사가 통째로 사라짐. 실질 방어선은 worker가 원본 fetch 직후·엔진 호출 전에 magic-byte를 재검증하는 것 | ✅ 완료 — [`worker.py:143`](../../services/worker/worker.py) `validate_image_bytes` 엔진 호출 전 재검증 |
| 4.7 | presigned 발급부 검증 강화 | [`services/gateway/app/main.py`](../../services/gateway/app/main.py) | gateway는 바이트를 안 보는 구조 — `validate_image()`의 magic-byte는 성립 불가. presign 시 `content-type`/크기 제약(약함, 우회 가능) + 만료 짧게(15분) + 레이트리밋. 실질 검증은 4.6 worker로 이관 | ✅ 완료 — content-type 화이트리스트 + `PRESIGN_EXPIRES_SEC=900` + `PRESIGN_RATE_PER_MIN=10` |

**완료 조건**: E2E 테스트 — presigned 업로드 → 잡 생성 → 워커 처리 → 결과 조회 통과.
**현재**: 4.1~4.7 **코드는 모두 완료**. 남은 것은 **실제 Supabase 연결 상태에서의 E2E 검증 → `ENABLE_LEGACY_UPLOAD=0`** 뿐이다(Phase 1 실배포에 종속).

---

### Phase 5 — CD 분리

**목표**: 웹은 Vercel 자동 배포, AI Server만 GH Actions → self-hosted runner로 배포.

| # | 작업 | 대상 파일 | 비고 | 상태 |
|---|------|-----------|------|------|
| 5.1 | `.github/workflows/`에서 웹 빌드/배포 제거 | `deploy-static.yml`, `deploy-webapp.yml` | 이 둘만 제거. [`build-and-deploy-engine.yml`](../../.github/workflows/build-and-deploy-engine.yml)·[`tests.yml`](../../.github/workflows/tests.yml)은 유지 | ✅ 완료 — 파일 이미 없음 |
| 5.2 | AI Server 배포 워크플로 정리 | `.github/workflows/*.yml` | `services/gateway`/`worker`/`engine-*`만 빌드/배포 | ✅ 완료 — paths 필터 이미 적용 + **C5-2 SERVICE 분기(matrix) 적용** |
| 5.3 | `deploy.sh` 환경변수 정리 | [`deploy/scripts/deploy.sh`](../../deploy/scripts/deploy.sh) | `WEBAPP_IMAGE` 등 제거, `.env.images`에서도 정리 | ✅ 완료 — `WEBAPP_IMAGE` 없음(이미 generic). [`.env.images.example`](../../deploy/env/.env.images.example)도 4개 이미지만 존재 |
| 5.4 | Vercel/AI Server 배포 순서 런북 작성 | `docs/operations/` | 계약 버전(`ENGINE_CONTRACT_VERSION`) 게이트 | ✅ 완료 — [`10_Phase5_배포순서_런북.md`](../operations/10_Phase5_배포순서_런북.md) |

**완료 조건**: main push 시 웹은 Vercel 자동 배포, AI Server는 GH Actions로 선택적 배포.
**현재**: ✅ **완료**. 5.1~5.4 모두 종결. C5-2(워크플로 SERVICE 분기)도 matrix로 해결.

---

### Phase 6 — 관측/DR 이관

**목표**: 보존·로그 스크럽·복구 리허설 대상을 Supabase로 전환.

| # | 작업 | 대상 파일 | 비고 | 상태 |
|---|------|-----------|------|------|
| 6.1 | `retention.py` Supabase 대상으로 수정 | [`deploy/ops-jobs/retention.py`](../../deploy/ops-jobs/retention.py) | Storage 객체 삭제 + DB 행 삭제 | ✅ 코드 완료 — `SUPABASE_URL`+service_role 사용. 남은 것: cron 배선·`DRY_RUN` 관찰 후 실적용 |
| 6.2 | `log-scrub.py` 대상 정리 | [`deploy/ops-jobs/log-scrub.py`](../../deploy/ops-jobs/log-scrub.py) | nginx 로그 제거, Caddy/gateway 로그만 | 🟡 코드 완료 — 필터 자체는 대상 무관(임의 로그 텍스트 마스킹, supabase.co signed URL 포함). `nginx-log-privacy.conf`는 nginx 제거로 사문화. 남은 것: 부팅 시 `install_scrubber()` 배선 확인 |
| 6.3 | 복구 리허설 스크립트 수정 | [`deploy/ops-jobs/restore-rehearsal.sh`](../../deploy/ops-jobs/restore-rehearsal.sh) | Supabase 백업/복구 절차로 교체 | ✅ 코드 완료 — Supabase 연결문자열(`db.<ref>.supabase.co`) 덤프 전제. 남은 것: 스테이징에서 1회 실행해 RPO/RTO 기록 |
| 6.4 | 알림/관측 스크립트 수정 | [`deploy/ops-jobs/observability/alert.sh`](../../deploy/ops-jobs/observability/alert.sh) | Supabase 상태 + AI Server 헬스 | ✅ 코드 완료 — `SUPABASE_HEALTH_URL`+`DATABASE_URL` 큐 점검 지원. 남은 것: `ALERT_WEBHOOK` 설정·cron 5분 등록·deploy 실패 훅 연결 |

**완료 조건**: `restore-rehearsal.sh`가 Supabase 백업으로부터 복구를 검증.
**현재**: 🟡 코드는 Supabase 대상으로 전환 완료(6.1/6.3/6.4 ✅, 6.2 필터는 대상 무관). 남은 것은 **운영 배선(cron·webhook)과 실제 리허설 1회 실행**뿐. Phase 1 Supabase 실연결(1.5) 후 즉시 실행 가능.

---

## 2. 제거 대상 요약

| 경로 | 이유 |
|------|------|
| `deploy/nginx/conf.d/{app,www,dev}.conf` | nginx 정적 서빙 제거 |
| `deploy/ops-jobs/nginx-log-privacy.conf` | nginx 제거와 함께 사문화 |
| `deploy/nginx/` 전체 (snippets 포함), `deploy/nginx/.htpasswd.example` | nginx 스택 제거. **단, 아래 책임 이주처를 먼저 확정할 것:** |
| `apps/homepage/public/index.html` | Vercel로 이관 또는 제거 |
| `apps/devpage/public/index.html` | Vercel로 이관 또는 제거 |
| `apps/webapp/` (기존 Vite) | Next.js로 이전 후 제거 |
| `compose.base.yml`의 `frontnet`, `storage` 볼륨 | Vercel/Supabase로 대체 |
| `compose.dev.yml`/`compose.staging.yml`의 `db` 서비스 | Supabase로 통일 |
| `deploy/env/.env.images`의 `WEBAPP_IMAGE` | Vercel 자동 배포 |

**nginx가 겸하던 책임의 이주처 (제거 전 확정 필수):**

| nginx 책임 | 현재 위치 | 이주처 |
|-----------|----------|--------|
| rate limit (`limit_req zone=upload`) | [`api.conf`](../../deploy/nginx/conf.d/api.conf) | Caddy `rate_limit` 플러그인 또는 gateway 미들웨어 |
| basic-auth (devpage) | `deploy/nginx/.htpasswd` | 제거(devpage 폐기) 또는 Caddy `basic_auth` |
| security headers | [`security-headers.conf`](../../deploy/nginx/snippets/security-headers.conf) | Caddy `header` 블록(HSTS는 이미 Caddy에 있음) |
| `client_max_body_size 25m` (엣지 413 경계) | [`api.conf`](../../deploy/nginx/conf.d/api.conf), [`app.conf`](../../deploy/nginx/conf.d/app.conf) | presigned 이후 body-size 부담은 줄지만, **Phase 4 착지 전까지 gateway가 여전히 multipart를 받으므로** 그 사이 상한을 Caddy나 gateway 중 한 곳에 둬야 함 — gateway 주석([`compose.base.yml`](../../deploy/compose/compose.base.yml) "앱단 413 경계 = 엣지 nginx client_max_body_size 와 일치시킬 것")이 참조하는 경계 |

---

## 3. 의존성/순서도

```
Phase 1 (Supabase 정렬)
   │
   ├─→ Phase 2 (웹 포팅)        ──→ Vercel Preview 테스트
   │
   └─→ Phase 3 (AI Server 슬림화) ──→ Phase 4 (presigned 전환)
                                          │
                                          └─→ Phase 5 (CD 분리)
                                                │
                                                └─→ Phase 6 (관측/DR 이관)
```

- **Phase 1은 모든 Phase의 선행 조건** — Supabase 프로젝트 없이는 dev도 불가.
- **Phase 2와 Phase 3은 병렬 가능** — 웹 포팅과 서버 슬림화는 독립적.
- **Phase 4는 Phase 3 이후** — gateway가 presigned 발급을 지원해야 웹이 전환 가능.

---

## 4. 리스크 및 롤백 전략

| 리스크 | 영향 | 롤백 |
|--------|------|------|
| CORS 회귀 | 웹에서 AI Server 호출 실패 | gateway에 `CORSMiddleware` 명시적 허용 오리진 추가 |
| Supabase 마이그레이션 실패 | 데이터 유실 | `03_DB_MIGRATION_ROLLBACK.md` 런북 따라 롤백 |
| presigned URL 유출 | 사진 무단 접근 | 만료 짧게(15분), MIME/크기 서버 검증, 버킷 정책 강화 |
| Next.js 이전 중 기능 회귀 | 사용자 경험 저하 | 기존 Vite 앱을 `legacy` 서브도메인으로 유지, 점진적 전환 |
| GPU 미배선 | 엔진 성능 저하 | `compose.gpu.yml` 오버레이 + `ENGINE_MAX_CONCURRENCY=1` |

---

## 5. 예상 공수 및 우선순위

| Phase | 예상 공수 | 우선순위 | 담당 |
|-------|-----------|----------|------|
| Phase 1 | 2~3일 | P0 | Backend/DevOps |
| Phase 2 | 3~5일 | P0 | Frontend |
| Phase 3 | 1~2일 | P0 | Backend/DevOps |
| Phase 4 | 2~3일 | P1 | Full-stack |
| Phase 5 | 1일 | P1 | DevOps |
| Phase 6 | 1~2일 | P2 | DevOps |

> 총 예상: **10~16일** (1명 기준, 병렬 시 단축 가능)

---

## 6. 성공 기준 (Definition of Done)

- [ ] `supabase start` 없이 로컬 개발이 Supabase dev 프로젝트로 동작
- [ ] Vercel에서 PWA 설치·오프라인 앱셸 동작, `/api`·Supabase는 캐시 없음
- [ ] Supabase RLS로 타 사용자 job/사진 접근 차단이 SQL 정책으로 검증(테스트 포함)
- [ ] AI Server는 443만 노출, 엔진은 `enginenet` 폐쇄망·무자격증명·포트 미발행
- [ ] presigned 업로드 → 잡 생성 → 워커 처리 → 결과 조회 E2E 통과
- [ ] CI에서 `alembic upgrade head` + 스키마 드리프트 테스트 통과
- [ ] GPU 오버레이 적용 시 동시성=1로 VRAM OOM 없이 엔진 헬스 유지
