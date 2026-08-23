# apps/webapp-next — SkinLens PWA (Next.js)

Vite SPA([`apps/webapp`](../webapp))를 **Next.js(App Router) + PWA** 로 포팅한 웹 표면.
Supabase 로그인 → AI Server(gateway) `/analyze` 호출 → 비동기 Job 폴리.
3-Tier 설계([`docs/architecture/04`](../../docs/architecture/04_3Tier_Vercel_Supabase_AIServer_설계.md))상 **Vercel** 에 배포된다.

## Vite → Next.js 대응표
| 기존(Vite) | 이전(Next.js App Router) |
|---|---|
| `src/main.tsx` + `index.html` | `src/app/layout.tsx` + `src/app/page.tsx` |
| `src/App.tsx` | `src/app/page.tsx` (`"use client"`) |
| `src/styles.css` | `src/app/globals.css` |
| `vite.config.ts` `VitePWA` | `next.config.mjs` `next-pwa` |
| `public/manifest`(정적) | `src/app/manifest.ts`(메타데이터 라우트) |
| `VITE_*` env | `NEXT_PUBLIC_*` env |

모든 대화형 컴포넌트는 `"use client"` 로 표시해 서버 컴포넌트 경계를 명확히 했다.

## 로컬 개발
1. `cp .env.example .env.local` 후 Supabase URL/anon 키·AI API 베이스 입력.
2. AI Server(gateway)를 기동하고 `NEXT_PUBLIC_AI_API_BASE` 로 가리킨다.
   - 오리진이 다륯므로 gateway 에 **CORS 허용 오리진**(이 앱의 dev/preview/prod 도메인)을 명시해야 한다.
3. `npm install && npm run dev` → http://localhost:3000

## 환경변수 (Vercel Project Settings)
| 변수 | 용도 |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase 프로젝트 URL(공개) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon 키(공개, RLS 가 통제) |
| `NEXT_PUBLIC_AI_API_BASE` | AI Server 공개 베이스(예: `https://api.example.com`) |

## 업로드 플로우 (Phase 4 — presigned)
`analyze()`([`src/lib/api.ts`](src/lib/api.ts))는 사진을 우리 서버로 볂내지 않는다. 세 단계:
1. **presign** — gateway `POST /uploads/presign` 에 `content_type`/`size_bytes` 를 볂내 `image_key` + 서명 업로드 URL(15분 만료) 을 받는다.
2. **Storage PUT** — 브라우저가 Supabase Storage 에 직접 `PUT`(서명 URL 이 인증 내장). 게이트웨이는 바이트를 안 만진다.
3. **analyze** — gateway `POST /analyze` 에 `{ image_key, survey }` JSON 만 본내 잡 생성.

서버 측 방어선: presign 시 content-type 화이트리스트·크기 상한·레이트리밋(분당 상한), 실질 매직바이트 재검증은 **worker** 가 원본 fetch 직후 수행(P0). 구 multipart 업로드는 `ENABLE_LEGACY_UPLOAD=1` 동안만 유지되다가 폐기(410)된다.

## PIPA / 보안 메모
- 서비스워커는 **앱 셸(정적)만** precache. `/api/*` 와 `*.supabase.co` 는 `NetworkOnly` — 사진·분석 결과·토큰·세션을 캐시하지 않는다.
- JWT 는 Supabase SDK 세션에만 보관. 오프라인 업로드 큐(Background Sync)는 기본 비활성(민감 이미지 로컬 저장 회피).
- 데이터 접근 권한은 최종적으로 Supabase RLS + gateway 소유권 검사(남의 job=404)로 강제된다.
- 배포는 Vercel(TLS 자동). 서비스워커·설치는 HTTPS(로컬 예외)에서만 동작.
- `NEXT_PUBLIC_*` 만 브라우저 번들에 주입. `SUPABASE_SERVICE_ROLE_KEY` 등 비공개 키는 절대 이 앱에 두지 않는다.
