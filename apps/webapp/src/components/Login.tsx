import { useState } from "react";
import { supabase } from "../lib/supabase";

// 매직링크(OTP) 로그인. 비밀번호 방식을 쓰면 signInWithPassword 로 교체.
export function Login() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const send = async () => {
    setErr(null);
    if (!email.includes("@")) { setErr("올바른 이메일을 입력하세요."); return; }
    const { error } = await supabase.auth.signInWithOtp({ email });
    if (error) setErr(error.message);
    else setSent(true);
  };

  return (
    <div className="card">
      <h1>SkinLens</h1>
      <p className="muted">AI 피부 분석 · 맞춤 처방</p>
      {sent ? (
        <p>메일로 로그인 링크를 보냈습니다. 받은 편지함을 확인하세요.</p>
      ) : (
        <>
          <input
            type="email" placeholder="you@example.com" value={email}
            onChange={(e) => setEmail(e.target.value)} aria-label="이메일"
          />
          <button onClick={send}>로그인 링크 받기</button>
          {err && <p className="err">{err}</p>}
        </>
      )}
    </div>
  );
}
