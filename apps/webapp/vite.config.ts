import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// 같은 오리진 라우팅: 운영/스테이징은 엣지 nginx 가 /api → gateway 로 프록시.
// 로컬 dev 는 아래 server.proxy 가 /api → gateway(8000) 로 넘긴다(동일 출처 유지 → CORS 불필요).
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      // 등록 스크립트를 외부 registerSW.js 로 주입(인라인 아님) → CSP `script-src 'self'` 와 호환.
      injectRegister: "script",
      includeAssets: ["favicon.png", "icon-192.png", "icon-512.png"],
      manifest: {
        name: "SkinLens",
        short_name: "SkinLens",
        description: "AI 피부 분석 · 맞춤 처방",
        start_url: "/",
        scope: "/",
        display: "standalone",
        background_color: "#EEF1EA",
        theme_color: "#2E4B3F",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      // PIPA: 앱 셸(정적)만 precache. 개인정보가 흐르는 /api 는 절대 캐시하지 않는다.
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,ico,webmanifest}"],
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          { urlPattern: /^\/api\//, handler: "NetworkOnly", method: "GET" },
          { urlPattern: /^\/api\//, handler: "NetworkOnly", method: "POST" },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      // 로컬 dev: gateway 8000 을 루프백에 publish 해 두고 사용(compose.dev.yml 의 ports 주석 해제).
      "/api": { target: "http://localhost:8000", changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, "") },
    },
  },
});
