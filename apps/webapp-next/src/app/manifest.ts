import type { MetadataRoute } from "next";

// next-pwa 가 서비스워커를 만들고, 이 파일이 웹앱 매니페스트를 만든다.
// Vite 시절 public/manifest 를 App Router 메타데이터 라우트로 이전.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "SkinLens",
    short_name: "SkinLens",
    description: "AI 피부 분석 · 맞춤 처방",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#EEF1EA",
    theme_color: "#2E4B3F",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
