import { createClient } from "@supabase/supabase-js";

// 인증만 담당. 데이터 접근은 gateway API 를 통하며, 실제 권한은 Supabase RLS 로 강제된다.
export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY,
  { auth: { persistSession: true, autoRefreshToken: true } },
);
