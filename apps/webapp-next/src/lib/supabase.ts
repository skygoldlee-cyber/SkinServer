import { createClient, type SupabaseClient } from "@supabase/supabase-js";

// 인증만 담당. 데이터 접근은 gateway API 를 통하며, 실제 권한은 Supabase RLS 로 강제된다.
// NEXT_PUBLIC_* 는 브라우저 번들에 주입되는 공개 키(anon)이며, RLS 가 최종 경계다.
//
// 모듈 스코프에서 createClient 를 호출하지 않는다 — App Router 는 클라이언트 컴포넌트도
// 빌드 타임에 모듈을 평가하므로, env 없는 prerender 에서 즉시 실패한다.
// 브라우저에서 첫 사용 시점에 지연 생성한다(싱글턴).
let _client: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient {
  if (typeof window === "undefined") {
    throw new Error("supabase 클라이언트는 브라우저에서만 생성할 수 있다.");
  }
  if (!_client) {
    _client = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      { auth: { persistSession: true, autoRefreshToken: true } },
    );
  }
  return _client;
}

// 기존 `supabase.auth.*` 호출부를 바꾸지 않기 위한 지연 프록시.
// 프로퍼티 접근 시점에 브라우저에서만 실제 클라이언트로 위임한다.
export const supabase = new Proxy({} as SupabaseClient, {
  get(_t, prop) {
    const client = getSupabase() as unknown as Record<PropertyKey, unknown>;
    const value = client[prop];
    return typeof value === "function" ? value.bind(client) : value;
  },
});
