import { supabase } from "./supabase";

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

// 고객 자가보고 설문 — packages/common/skinlens_contract 의 Survey shape 와 일치.
// 앱은 아는 필드만 채워 보내고, 엔진은 아는 필드만 사용한다(모두 선택).
export interface Survey {
  skin_type?: string;                  // oily|dry|combination|normal|sensitive
  sensitivity?: Record<string, boolean>; // stings_easily|reacts_to_products|redness_frequent
  concerns?: string[];                 // acne|pigmentation|wrinkles|pores|redness|dryness …
  age_band?: string;                   // 10s|20s|30s|40s|50s+
  sun_exposure?: string;               // low|medium|high
  notes?: string;
}

export type JobStatus = "queued" | "processing" | "done" | "error";
export interface Job {
  id: string;
  status: JobStatus;
  result?: unknown;
  error?: string | null;
}

// 모든 API 호출에 Supabase JWT 를 Bearer 로 첨부. gateway(strict) 가 HS256+audience 검증.
// 토큰은 메모리/세션에만 두고, 서비스워커·응답은 캐시하지 않는다(PIPA).
async function authHeaders(): Promise<HeadersInit> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface PresignResponse {
  job_id: string;
  image_key: string;
  expires_in: number;
  signed: { url: string; path?: string; token?: string };
}

/**
 * 사진+설문 업로드 → job_id 즉시 반환 (Phase 4.4 presigned 플로우).
 *   1) gateway /uploads/presign  → image_key + 서명 업로드 URL 발급
 *   2) Supabase Storage 에 브라우저가 직접 PUT (게이트웨이는 바이트를 안 만진다)
 *   3) gateway /analyze { image_key, survey } → 잡 생성
 * 사진은 한 번도 우리 서버를 거치지 않는다(PIPA·대역폭 절감). 토큰은 메모리에만(캐시 금지).
 */
export async function analyze(image: File, survey?: Survey): Promise<{ job_id: string }> {
  const headers = await authHeaders();

  // 1) presign — content-type/size 를 선언해 서버 검증·만료를 받는다.
  const presign = await fetch(`${BASE}/uploads/presign`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ content_type: image.type, size_bytes: image.size }),
  });
  if (!presign.ok) throw new Error(`presign 실패: ${presign.status}`);
  const pre: PresignResponse = await presign.json();

  // 2) Supabase Storage 에 직접 PUT. 서명 URL 이 호출 인증을 내장한다.
  const put = await fetch(pre.signed.url, {
    method: "PUT",
    headers: { "Content-Type": image.type },
    body: image,
  });
  if (!put.ok) throw new Error(`storage 업로드 실패: ${put.status}`);

  // 3) 잡 생성 — image_key 와 설문만 본다(이미지 바이트 없음).
  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ image_key: pre.image_key, survey }),
  });
  if (!res.ok) throw new Error(`analyze 실패: ${res.status}`);
  return res.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`${BASE}/jobs/${jobId}`, { headers: await authHeaders() });
  if (res.status === 404) throw new Error("job 없음(권한 없음 포함)");
  if (!res.ok) throw new Error(`job 조회 실패: ${res.status}`);
  return res.json();
}
