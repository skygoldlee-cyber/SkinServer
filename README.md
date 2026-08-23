# SkinLens — Monorepo

AI 피부분석 · 처방 플랫폼. **코드 · 인프라 · 문서**를 하나의 저장소에서 관리하며,
**3-Tier(Vercel · Supabase · AI Server)** 구조로 재편 중이다.

기존 문서세트(`SkinServer`)를 운영 가능한 구조로 재배치한 결과물이다. 원본 파일과의 대응은
[`MIGRATION.md`](./MIGRATION.md) 를 참고한다.

## 현재 아키텍처 — 3-Tier

```
사용자
  │
  ▼
┌─────────────┐      (정적/PWA·엣지 캐시)
│   Vercel    │  ── Next.js PWA (apps/webapp-next)
└──────┬──────┘      서비스워커는 앱셸만 precache, /api·Supabase NetworkOnly
       │  (1) 인증·DB·스토리지 = Supabase SDK (브라우저, anon key + RLS)
       │  (2) AI 작업 요청    = HTTPS → AI Server
       ▼                     ▼
┌───────────┐          ┌──────────────┐
│ Supabase  │          │  AI Server   │
│ Postgres  │◀─service│  (전용 호스트)│
│ Auth      │  role   │  FastAPI     │
│ Storage   │  (서버만)│  OpenCV      │
│ (RLS 강제) │          │  Docker·GPU  │
└───────────┘          └──────────────┘
```

- **Vercel** — SkinLens 웹서비스(PWA)를 전역 배포. Next.js App Router + PWA.
- **Supabase** — 데이터(Postgres)·인증(Auth)·파일(Storage)의 단일 진실원본. RLS가 최종 경계.
- **AI Server** — 분석/처방 엔진 + 잡 큐/워커 + 얇은 게이트웨이를 싣는 전용 호스트(Docker Compose). 외부엔 443(Caddy)만 연다.

> 설계 정본: [`docs/architecture/04_3Tier_Vercel_Supabase_AIServer_설계.md`](./docs/architecture/04_3Tier_Vercel_Supabase_AIServer_설계.md)
> 이전 작업계획·상태: [`docs/architecture/05_3Tier_이전_작업계획.md`](./docs/architecture/05_3Tier_이전_작업계획.md)

## 저장소 구조

```
skinlens/
├── apps/
│   ├── webapp-next/     ⭐ 현행: Next.js PWA (Vercel 배포 대상)
│   ├── webapp/          레거시: Vite SPA (이전 완료 후 제거 예정)
│   ├── homepage/        정적 플레이스홀더 (Vercel 이관 또는 제거 예정)
│   └── devpage/         정적 플레이스홀더 (폐기 예정)
├── services/            AI Server: gateway · worker · engine-analysis · engine-prescription
├── packages/            서비스 공용 코드(스키마·규칙) — skinlens_contract
├── deploy/              AI Server 전용 배포 스택 (인프라 코드)
│   ├── compose/         compose.base.yml + dev/staging/prod + gpu/tls 오버레이
│   ├── env/            .env / .env.images 예시
│   ├── caddy/          AI Server TLS(Caddyfile) — api 도메인만
│   ├── scripts/        deploy.sh(헬스게이트+롤백) · 백업 · 검증 · 이관
│   ├── supabase/       RLS · Storage 정책 SQL
│   ├── db/             마이그레이션 SQL
│   ├── nginx/          ⚠️ 레거시 (제거 예정 — 책임은 Caddy/gateway로 이주 중)
│   └── ops-jobs/       보존·로그 스크러빙·관측·복구 리허설
├── .github/workflows/ CI/CD (AI Server 전용 — 웹은 Vercel 자동)
├── tests/             통합/스모크(pytest)
├── docs/              모든 설계·운영 문서 (코드와 분리)
└── site/              문서 포털(index.html)
```

## 아키텍처 한눈에

- **네트워크**: AI Server 남부만 `appnet` ↔ `enginenet(internal:true)` 2분할. `frontnet`·nginx·정적 표면은 Vercel로 이관됨.
- **엔진 격리(Case A)**: `engine-*` 는 `enginenet` 전용 · 포트 미발행 · 자격증명 없음 · 외부 egress 불가.
- **presigned 업로드**: 브라우저가 Supabase Storage에 직접 PUT → gateway는 `image_key`만 수신 → worker가 서명 URL로 fetch + magic-byte 재검증.
- **비동기 Job**: gateway 가 Job 등록→`job_id` 즉시 반환, worker 가 분석→처방 호출 후 결과 기록.
- **단일 쓰기 주체**: DB 쓰기는 gateway·worker(service role). 브라우저는 anon key + RLS로 읽기/제한적 쓰기.
- **앱 표면(PWA)**: Vercel이 Next.js PWA 서빙. 서비스워커는 앱 셸만 precache, `/api/*`·`*.supabase.co` 는 `NetworkOnly`(PIPA).

## 배포 스택 (AI Server 전용)

한 벌의 `compose.base.yml` 위에 환경 오버레이만 갈아끼운다. **DB/Storage/Auth는 전 환경 Supabase**를 사용한다(로컬 postgres 없음).

| 환경 | compose 조합 | DB/Storage | 이미지 |
|---|---|---|---|
| dev | `base + dev` | Supabase `skinlens-dev` | 소스 빌드(`build:`) |
| staging | `base + staging` | Supabase `skinlens-dev` | `.env.images` 태그 |
| prod | `base + prod (+ tls)` | Supabase `skinlens-prod` | `.env.images` 태그 |
| GPU | `... + gpu` | — | 엔진 GPU 예약 + 직렬화 |

## 빠른 시작 (dev)

모든 기동 명령의 진실원본은 [`deploy/scripts/sl`](./deploy/scripts/sl) (Windows는 `sl.ps1`) 이다.
환경(dev/staging/prod) 무관하게 같은 동사를 쓴다 — `up / down / logs / ps / doctor / init / deploy`.

```bash
deploy/scripts/sl init dev   # 최초 1회: .env 생성 → Supabase 값 입력 안내 → 자가진단
deploy/scripts/sl up dev     # base + dev 빌드·기동
deploy/scripts/sl ps dev     # 상태
deploy/scripts/sl down dev
```

> `make` 습관이 있다면 그대로: `make dev-up` 등은 `sl`을 호출하는 래퍼다.
> 환경별 절차 전체: [`docs/operations/환경별_빌드_기동_절차.md`](./docs/operations/환경별_빌드_기동_절차.md)

> ⚠️ dev 기동 전에 Supabase 프로젝트(`skinlens-dev`) 생성·마이그레이션·RLS 적용이 선행되어야 한다.
> 실행 런북: [`docs/operations/09_Phase1_Supabase_실행런북.md`](./docs/operations/09_Phase1_Supabase_실행런북.md)

## 파이프라인 실행·점검

**분석 엔진은 OpenCV 실측**(더미 아님) — 붉은기/색소·톤/모공/피부결/주름/지성/트러블 등을 픽셀에서 계산해 10지표 점수와 종합 점수를 낸다. **처방 엔진**은 확정된 등급/비율 규칙 + 지표별 믹스 선택(M01~M11 / PM01~PM03)을 낸다. GAN 복원·ML 스코어러·실제 배합은 명시된 seam/설정으로 남겨 향후 보완한다.

- **API**(AI Server, Caddy TLS 뒤):
  - `GET /health`·`/health/db`·`/debug/engines` — 파트별 생존(엔진은 gateway 대리 확인)
  - `POST /uploads/presign` → `image_key` + 서명 업로드 URL(15분 만료)
  - `POST /analyze { image_key, survey }` → `job_id`
  - `GET /jobs/{id}/events` — 업로드→큐→분석→처방→완료 각 단계의 JSON 스냅샷
  - `GET /jobs/{id}` — 최종 `result`(analysis 10지표 + prescription 믹스 선택)

관측 단계는 `job_events` 테이블에 기록된다(엔진은 `enginenet` 폐쇄망이라 직접 열지 않고 gateway 경유로만 점검 — Case A 유지).

- 서버 반입·실행·운영 전체 절차: [`docs/operations/서버_실행_운영_가이드.md`](./docs/operations/서버_실행_운영_가이드.md)
- 엔진 baseline·교체 지점(seam)·믹스 설정: [`docs/architecture/엔진_baseline_교체_가이드.md`](./docs/architecture/엔진_baseline_교체_가이드.md)
- 웹앱(Next.js PWA) 로컬 개발·PIPA 캐시 메모: [`apps/webapp-next/README.md`](./apps/webapp-next/README.md)
- Flutter 앱 연동(사진+설문) 계약: [`docs/integration/flutter_app_contract.md`](./docs/integration/flutter_app_contract.md)
- 파이프라인 체크포인트·트러블슈팅: [`docs/operations/파이프라인_체크포인트_트러블슈팅.md`](./docs/operations/파이프라인_체크포인트_트러블슈팅.md)
- 보완 반영 요약(안정성/정확성/관측/도메인) + 남은 seam: [`docs/changelog/보완반영_요약.md`](./docs/changelog/보완반영_요약.md)

주요 환경변수: `AUTH_MODE`(dev|strict) · `AUTO_DDL`(dev만) · `STORAGE_BACKEND`(supabase) · `DATABASE_URL`(Supabase) · `SUPABASE_URL`·`SUPABASE_SERVICE_KEY` · `CORS_ORIGINS`(Vercel 도메인) · `ENABLE_LEGACY_UPLOAD`(구 multipart 호환 플래그) · `PRESIGN_EXPIRES_SEC` · `MAX_ATTEMPTS` · `STALE_SECONDS` · `ENGINE_RETRIES` · `ENGINE_MODEL`(baseline|ml) · `LOG_LEVEL`.

## 배포 (웹 / AI Server 분리)

**웹(apps/webapp-next)**: `main` push → Vercel 자동 빌드/배포. 이 리포지토리에서 웹을 빌드/배포하지 않는다.

**AI Server(services/)**: GH Actions → self-hosted runner → `deploy/scripts/deploy.sh`.
수동으로는 `sl deploy`가 같은 스크립트를 감싼다.

```bash
# 스테이징에서 gateway 를 새 이미지로
deploy/scripts/sl deploy gateway sl_gateway:abc123 --env staging

# 운영에서 엔진을 GHCR 이미지로(pull)
deploy/scripts/sl deploy engine-analysis \
  ghcr.io/coteleafdev/skinlens-engine-analysis:abc123 --env production --pull
```

배포는 `.env.images` 태그를 원자적으로 교체 → up → **헬스체크 게이트 + 실패 시 자동 롤백**한다.
스택 전체 기동은 `sl up staging` / `sl up prod` (prod는 기동 전 doctor 자동 검사).

계약(`packages/common/skinlens_contract`) 변경 시 **AI Server 먼저, 웹은 그 다음** 배포하는 게이트 런북:
[`docs/operations/10_Phase5_배포순서_런북.md`](./docs/operations/10_Phase5_배포순서_런북.md)

## 문서

- 읽는 순서·전체 지도: [`docs/README.md`](./docs/README.md)
- 파일 카탈로그: [`docs/MANIFEST.md`](./docs/MANIFEST.md)
- 3-Tier 설계·이전 계획: [`docs/architecture/04_3Tier_Vercel_Supabase_AIServer_설계.md`](./docs/architecture/04_3Tier_Vercel_Supabase_AIServer_설계.md) · [`docs/architecture/05_3Tier_이전_작업계획.md`](./docs/architecture/05_3Tier_이전_작업계획.md)
- 구현 우선순위·리스크: [`docs/roadmap/09_구현우선순위_배포구조_리스크정리.md`](./docs/roadmap/09_구현우선순위_배포구조_리스크정리.md)

> ⚠️ `docs/` 안의 문서 상당수는 재배치 이전 경로(`01_…`, `05_…`)로 상호 링크되어 있다.
> 새 경로 대응은 [`MIGRATION.md`](./MIGRATION.md) 표를 기준으로 읽는다.
