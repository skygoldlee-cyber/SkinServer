# apps/webapp — SkinLens PWA

Vite + React + TypeScript 정적 SPA. Supabase 로그인 → `/api` 로 gateway 호출 → 비동기 Job 폴링.
API 와 **같은 오리진**(`app.` 호스트에서 엣지 nginx 가 `/`→webapp, `/api/`→gateway)으로 서빙되므로 CORS 불필요.

## 로컬 개발
1. `cp .env.example .env` 후 Supabase URL/anon 키 입력.
2. gateway 를 루프백에 publish: `compose.dev.yml` 의 gateway `ports: ["127.0.0.1:8000:8000"]` 주석 해제 후 스택 기동.
3. `npm install && npm run dev` → http://localhost:5173 (Vite 가 `/api` → localhost:8000 프록시).

## 컨테이너로 실행
`docker compose -f deploy/compose/compose.base.yml -f deploy/compose/compose.dev.yml up -d --build webapp`
(base 는 `image:`, dev 오버레이가 `build:` 를 얹는다 — gateway/worker 와 동일 패턴.)

> ⚠ **레거시(롤백용)** — 활성 표면은 Next.js 포트 [`apps/webapp-next`](../webapp-next)다. 이 앱은 계획의 롤백 노트에 따라 당분간 유지한다.
> 업로드는 Phase 4 부터 **presigned 플로우**([`src/lib/api.ts`](src/lib/api.ts)): presign → Supabase Storage 직접 PUT → `/analyze { image_key }`. 구 multipart 는 gateway 의 `ENABLE_LEGACY_UPLOAD=1` 동안만 동작한다.

## PIPA / 보안 메모
- 서비스워커는 **앱 셸(정적)만** precache. `/api/*` 는 `NetworkOnly` — 사진·분석 결과·토큰을 캐시하지 않는다.
- **CSP**: 엣지에서 `app.` 표면에만 전용 CSP 적용(`deploy/nginx/snippets/csp-app.conf`). `connect-src` 는 same-origin `/api` + Supabase 오리진만 허용 — 배포 전 `<PROJECT>.supabase.co` 를 실제 값으로 교체한다.
- JWT 는 Supabase SDK 세션에만 보관. 오프라인 업로드 큐(Background Sync)는 기본 비활성(민감 이미지 로컬 저장 회피).
- 데이터 접근 권한은 최종적으로 Supabase RLS + gateway 소유권 검사(남의 job=404)로 강제된다.
- 배포 호스트(`app.`)에는 TLS 필수 — 서비스워커·설치는 HTTPS(로컬 예외)에서만 동작.
