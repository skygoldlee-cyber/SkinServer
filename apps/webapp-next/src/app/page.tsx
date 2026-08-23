"use client";

import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "../lib/supabase";
import { Login } from "../components/Login";
import { Analyze } from "../components/Analyze";

// 기존 Vite App.tsx 의 App Router 대응. 세션을 구독해 로그인/분석 표면을 가른다.
// 이 앱은 세션-게이트된 순수 클라이언트 표면이라 서버 프리렌더 의미가 없다.
// 강제 다이나믹으로 빌드 타임 정적 생성을 건드리지 않는다
// (Supabase env 는 런타임 브라우저 번들에만 주입되므로 prerender 시 createClient 가 실패한다).
export const dynamic = "force-dynamic";

export default function Page() {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => { setSession(data.session); setReady(true); });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  if (!ready) return <main><div className="card">불러오는 중…</div></main>;

  return (
    <main>
      {session ? (
        <>
          <header className="topbar">
            <span>SkinLens</span>
            <button className="ghost" onClick={() => supabase.auth.signOut()}>로그아웃</button>
          </header>
          <Analyze />
        </>
      ) : (
        <Login />
      )}
    </main>
  );
}
