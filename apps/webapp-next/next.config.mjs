import withPWAInit from "next-pwa";

// PIPA: 앱 셸(정적)만 precache. 개인정보가 흐르는 /api 와 Supabase 는 절대 캐시하지 않는다.
// - runtimeCaching 으로 /api/*·*.supabase.co 를 NetworkOnly 로 명시.
// - 문서(HTML) 오프라인 폴리은 두지 않는다 — next-pwa 의 `fallbacks` 옵션은
//   precacheFallback 초기화 버그(undefined)가 있고, PIPA 상 탐색 응답을 캐시하지 않는 편이 안전하다.
const withPWA = withPWAInit({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === "development",
  runtimeCaching: [
    // AI Server gateway — 사진·분석 결과·토큰이 오가므로 NetworkOnly.
    {
      urlPattern: /^\/api\/.*$/i,
      handler: "NetworkOnly",
      method: "GET",
    },
    {
      urlPattern: /^\/api\/.*$/i,
      handler: "NetworkOnly",
      method: "POST",
    },
    {
      urlPattern: /^\/api\/.*$/i,
      handler: "NetworkOnly",
      method: "PUT",
    },
    {
      urlPattern: /^\/api\/.*$/i,
      handler: "NetworkOnly",
      method: "DELETE",
    },
    // AI Server gateway 절대 URL(교차 오리진) — NEXT_PUBLIC_AI_API_BASE 가
    // 별도 도메인(예: https://api.example.com)으로 배포될 때도 NetworkOnly.
    {
      urlPattern: ({ url }) => url.pathname.startsWith("/api/"),
      handler: "NetworkOnly",
      method: "GET",
    },
    {
      urlPattern: ({ url }) => url.pathname.startsWith("/api/"),
      handler: "NetworkOnly",
      method: "POST",
    },
    {
      urlPattern: ({ url }) => url.pathname.startsWith("/api/"),
      handler: "NetworkOnly",
      method: "PUT",
    },
    {
      urlPattern: ({ url }) => url.pathname.startsWith("/api/"),
      handler: "NetworkOnly",
      method: "DELETE",
    },
    // Supabase(Auth/DB/Storage) — 세션·PII·서명 URL 이므로 NetworkOnly.
    {
      urlPattern: /^https:\/\/.*\.supabase\.co\/.*$/i,
      handler: "NetworkOnly",
      method: "GET",
    },
    {
      urlPattern: /^https:\/\/.*\.supabase\.co\/.*$/i,
      handler: "NetworkOnly",
      method: "POST",
    },
    {
      urlPattern: /^https:\/\/.*\.supabase\.co\/.*$/i,
      handler: "NetworkOnly",
      method: "PUT",
    },
    {
      urlPattern: /^https:\/\/.*\.supabase\.co\/.*$/i,
      handler: "NetworkOnly",
      method: "DELETE",
    },
  ],
  buildExcludes: [/middleware-manifest\.json$/],
});

/** @type {import("next").NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};

export default withPWA(nextConfig);
