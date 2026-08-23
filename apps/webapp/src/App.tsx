import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./lib/supabase";
import { Login } from "./components/Login";
import { Analyze } from "./components/Analyze";

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => { setSession(data.session); setReady(true); });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  if (!ready) return <div className="card">불러오는 중…</div>;

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
