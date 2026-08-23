# MIGRATION — 원본 문서세트 → 운영 monorepo 대응표

기존 `SkinServer`(문서세트)를 아래 원칙으로 재배치했다.

1. **코드 · 인프라 · 문서 분리** — `services/`·`apps/` / `deploy/` / `docs/`.
2. **배포 스택 통합** — 중복되던 두 compose(`03_webstack_스캐폴드`, `05/skinlens-ops`)를
   `compose.base.yml` + 환경 오버레이(`dev`/`staging`/`prod`)로 단일화.
3. **서비스별 레포 → 단일 레포** — `05/workflows/*` 템플릿을 `.github/workflows/` 로 이동
   (운영 시 각 워크플로에 `paths:` 필터를 걸어 변경 서비스만 빌드).

> ⚠️ **2026-08 기준 구조 변경**: monorepo는 이후 **3-Tier(Vercel · Supabase · AI Server)** 구조로
> 재편 중이다. 아래 "1차 재배치 대응표"는 문서세트 → monorepo 이동의 정본이고,
> 그 이후의 **3-Tier 재편 대응표**(무엇이 Vercel/Supabase로 이관되고 무엇이 제거되는가)는
> 별도 섹션으로 뒤에 둔다. 3-Tier 설계·작업계획의 정본은
> [`docs/architecture/04_3Tier_Vercel_Supabase_AIServer_설계.md`](./docs/architecture/04_3Tier_Vercel_Supabase_AIServer_설계.md) ·
> [`docs/architecture/05_3Tier_이전_작업계획.md`](./docs/architecture/05_3Tier_이전_작업계획.md).

## 경로 대응 (1차 재배치: 문서세트 → monorepo)

| 원본 | 신규 |
|---|---|
| `03_webstack_스캐폴드/gateway/` | `services/gateway/` |
| `03_webstack_스캐폴드/worker/` | `services/worker/` |
| `03_webstack_스캐폴드/engine-analysis/` | `services/engine-analysis/` |
| `03_webstack_스캐폴드/engine-prescription/` | `services/engine-prescription/` |
| `03_webstack_스캐폴드/homepage/index.html` | `apps/homepage/public/index.html` |
| `03_webstack_스캐폴드/devpage/index.html` | `apps/devpage/public/index.html` |
| `03_webstack_스캐폴드/docker-compose.yml` | `deploy/compose/compose.base.yml` + `compose.dev.yml` 로 **통합** |
| `05_CD_배포/skinlens-ops/docker-compose.yml` | `deploy/compose/compose.base.yml` + `compose.{staging,prod}.yml` 로 **통합** |
| `05_CD_배포/skinlens-ops/docker-compose.gpu.yml` | `deploy/compose/compose.gpu.yml` |
| `05_CD_배포/skinlens-ops/docker-compose.tls.yml` | `deploy/compose/compose.tls.yml` |
| `05_CD_배포/skinlens-ops/Caddyfile` | `deploy/caddy/Caddyfile` |
| `05_CD_배포/skinlens-ops/nginx/` | `deploy/nginx/` ⚠️ 3-Tier 이전으로 제거 예정 |
| `05_CD_배포/skinlens-ops/.env.example` | `deploy/env/.env.example` |
| `05_CD_배포/skinlens-ops/.env.images.example` | `deploy/env/.env.images.example` |
| `05_CD_배포/skinlens-ops/deploy.sh` | `deploy/scripts/deploy.sh` (경로 통합에 맞춰 수정) |
| `05_CD_배포/skinlens-ops/sites/` | 삭제(첫기동 플레이스홀더) → `apps/` 산출물로 대체 |
| `05_CD_배포/supabase/` | `deploy/supabase/` |
| `05_CD_배포/followup-P1/` | `deploy/ops-jobs/` |
| `05_CD_배포/workflows/` | `.github/workflows/` |
| `01_서버구축_패치본_v3/*.sh`, `*.ps1` | `deploy/scripts/` |
| `01_서버구축_패치본_v3/test_environment.py` | `tests/test_environment.py` |
| `01_서버구축_패치본_v3/*.md`, `CHANGES*.diff` | `docs/server-setup/` (`changes/` 하위에 diff) |
| `02_적합성검토/` | `docs/architecture/` |
| `08_최종리뷰/00~03` | `docs/architecture/` |
| `08_최종리뷰/04_후속보완_로드맵.md` | `docs/roadmap/` |
| `04_이야기/` | `docs/stories/` |
| `06_운영·배포_체크리스트.md`, `07_학습_로드맵.md` | `docs/operations/` |
| `09_구현우선순위_배포구조_리스크정리.md` | `docs/roadmap/` |
| `00_INDEX.md` | `docs/README.md` |
| `00_파일안내_MANIFEST.md` | `docs/MANIFEST.md` |
| `index.html` | `site/index.html` |

## 배포 스택 통합 상세

두 원본 compose 는 토폴로지가 동일하고 차이는 세 가지뿐이었다 →
공통부를 base 로 빼고 차이만 오버레이로 표현했다.

| 차이점 | dev | staging | prod |
|---|---|---|---|
| 서비스 이미지 | `build:`(소스) | `.env.images` 태그 | `.env.images` 태그 |
| 데이터·스토리지 | Supabase `skinlens-dev` | Supabase `skinlens-dev` | Supabase `skinlens-prod` |
| 엔진 이미지 | 로컬 빌드 | GHCR pull | GHCR pull |

`compose.base.yml` 은 각 서비스에 `image: ${SERVICE_IMAGE:-기본태그}` 를 두고,
`compose.dev.yml` 이 그 위에 `build:` 를 얹는다(빌드 시 해당 태그로 태깅되어 롤백 태그 체계와 일치).

> **3-Tier 재편 이후**: 로컬 postgres `db` 서비스는 제거됐고, 전 환경이 Supabase 를 쓴다.
> 로컬 볼륨 `storage:` 도 제거되고 Supabase Storage(`skin-images` 버킷, presigned 업로드)로 대첐됐다.

## 3-Tier 재편 대응표 (monorepo → Vercel · Supabase · AI Server)

| 축 | 1차 재배치 상태 | 3-Tier 이후 | 상태 |
|---|---|---|---|
| 웹 표면 | `apps/webapp`(Vite SPA) + nginx 정적 서빙 | **`apps/webapp-next`(Next.js PWA) → Vercel** | ✅ 코드 이전 완료 · ⬜ Vercel 연결·구앱 제거 |
| 엣지/TLS | nginx 80 + Caddy TLS | **Vercel(웹) + Caddy(AI Server `api.*` 만)** | ✅ Caddy 재배선 완료 |
| 네트워크 | `frontnet`/`appnet`/`enginenet` 3분할 | **`appnet`/`enginenet` 2분할** (`frontnet` 제거) | ✅ 완료 |
| 데이터 | dev/staging=로컬 pg, prod=Supabase | **전 환경 Supabase** (`skinlens-dev`/`skinlens-prod`) | ✅ 코드 완료 · ⬜ 프로젝트 생성·`.env` 실값 |
| 스토리지 | 로컬 볼륨 `storage:` | **Supabase Storage `skin-images`** (presigned) | ✅ 코드 완료 · ⬜ E2E 검증 |
| 업로드 | gateway multipart 수신 | **presigned**: 브라우저→Storage 직접 PUT, gateway는 `image_key`만 | ✅ 코드 완료 · ⬜ `ENABLE_LEGACY_UPLOAD=0` |
| 인증 | Supabase JWT, gateway 검증 | 동일 — 브라우저→Supabase 직결, gateway는 검증만 + CORS | ✅ 완료 |
| CI/CD — 웹 | `.github/workflows/deploy-{static,webapp}.yml` | **Vercel 자동 배포** (워크플로 제거 완료) | ✅ 완료 |
| CI/CD — AI Server | `deploy-built-service.yml`·`build-and-deploy-engine.yml` | 동일 (유지) + C5-2 SERVICE 분기 적용 | ✅ |
| nginx 책임 | `deploy/nginx/`(라우팅·레이트리밋·보안헤더·basic-auth) | **Caddy/gateway 로 이주**, nginx 제거 예정 | ⬜ 책임 이주 확정 후 제거 |
| 관측/DR | `deploy/ops-jobs/` 대상=로컬 pg·볼륨 | 대상을 **Supabase**로 전환 | ⬜ 미착수 |

## 남은 수작업(권장)

- `docs/**` 남부 상호 링크는 옛 경로(`01_…`, `05_…`)를 참조한다. 위 표 기준으로 순차 치환.
- `.github/workflows/*.yml` 에 `on.push.paths` 필터 추가(예: `services/gateway/**`)로
  변경 서비스만 빌드되도록 조정.
- **3-Tier 잔여 작업** (상세는 `docs/architecture/05_3Tier_이전_작업계획.md` 상태표):
  - Phase 1: Supabase 프로젝트 생성·마이그레이션·RLS 적용·`.env` 실값(런북 `docs/operations/09_Phase1_Supabase_실행런북.md`).
  - Phase 2: Vercel 프로젝트 연결·환경변수·PWA 실검증 → 구 `apps/webapp` 제거.
  - ~~Phase 3.8/5.3: `deploy.sh` 의 웹 서비스(`WEBAPP_IMAGE` 등) 정리~~ ✅ 완료
  - ~~Phase 5: `deploy-static.yml`·`deploy-webapp.yml` 워크플로 제거~~ ✅ 완료 (C5-2 SERVICE 분기도 matrix로 해결)
  - Phase 6: `ops-jobs`(retention·log-scrub·restore-rehearsal·alert) 대상을 Supabase로 전환.
  - `deploy/nginx/` 전체 제거 — 단, 책임 이주(rate limit→Caddy/gateway, security headers→Caddy, body-size→gateway) 확정 후.
  - `apps/homepage`·`apps/devpage` 를 Vercel 이관 또는 제거.
- `tests/fixtures/sample.jpg` 추가(스모크용 샘플 업로드 이미지).
