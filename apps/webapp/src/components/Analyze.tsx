import { useState } from "react";
import { analyze, type Survey } from "../lib/api";
import { useJob } from "../hooks/useJob";
import { SurveyForm, cleanSurvey } from "./SurveyForm";

export function Analyze() {
  const [file, setFile] = useState<File | null>(null);
  const [survey, setSurvey] = useState<Survey>({});
  const [jobId, setJobId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const { job } = useJob(jobId);

  const submit = async () => {
    setErr(null);
    if (!file) { setErr("사진을 선택하세요."); return; }
    setBusy(true);
    try {
      const { job_id } = await analyze(file, cleanSurvey(survey));
      setJobId(job_id);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card">
      <h2>피부 분석</h2>
      <input type="file" accept="image/*" capture="user"
             onChange={(e) => setFile(e.target.files?.[0] ?? null)} aria-label="피부 사진" />

      <SurveyForm value={survey} onChange={setSurvey} />

      <button onClick={submit} disabled={busy || !file}>
        {busy ? "업로드 중…" : "분석 시작"}
      </button>
      {err && <p className="err">{err}</p>}

      {jobId && (
        <div className="status">
          <p>접수번호 <code>{jobId.slice(0, 8)}</code></p>
          <p>상태: <b>{job?.status ?? "queued"}</b>
            {job && job.status !== "done" && job.status !== "error" && " · 조리 중…"}
          </p>
          {job?.status === "done" && (
            <pre className="result">{JSON.stringify(job.result, null, 2)}</pre>
          )}
          {job?.status === "error" && <p className="err">분석 실패: {job.error}</p>}
        </div>
      )}
    </div>
  );
}
