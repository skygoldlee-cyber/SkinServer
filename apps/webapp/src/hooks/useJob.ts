import { useEffect, useRef, useState } from "react";
import { getJob, type Job } from "../lib/api";

// events 엔드포인트가 SSE 가 아니라 이벤트 JSON 이므로, done/error 까지 폴리한다.
// (추후 SSE/WebSocket 도입 시 이 훅만 스트림 구독으로 교체.)
//
// (P3 #10) 지수 백오프: 고정 간격 폴리는 모바일/저전력 환경에서 배터리·데이터를
//          소모한다. 성공할 때마다 간격을 intervalMs 부터 최대 maxIntervalMs 까지
//          지수적으로 늘리고, 상태가 바뀌면(=진전이 있으면) intervalMs 로 리셋한다.
//          탭이 백그라운드로 가면(visibilitychange) 폴리를 잠시 멈춰 소모를 줄인다.
export function useJob(
  jobId: string | null,
  intervalMs = 1500,
  maxIntervalMs = 15000,
) {
  const [job, setJob] = useState<Job | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!jobId) return;
    let alive = true;
    let delay = intervalMs;
    let lastStatus: string | null = null;

    const clear = () => {
      if (timer.current) {
        window.clearTimeout(timer.current);
        timer.current = null;
      }
    };

    const tick = async () => {
      if (!alive) return;
      // 탭이 숨겨져 있으면 이번 틱은 건드리지 않고 다음 틱으로 미룬다(배터리 절약).
      if (document.visibilityState === "hidden") {
        timer.current = window.setTimeout(tick, delay);
        return;
      }
      try {
        const j = await getJob(jobId);
        if (!alive) return;
        setJob(j);
        if (j.status === "done" || j.status === "error") {
          clear();
          return; // 폴폴 종료
        }
        // 상태가 바뀌면(진전) 지연을 리셋, 아니면 지수 백오프.
        delay = j.status !== lastStatus ? intervalMs : Math.min(delay * 2, maxIntervalMs);
        lastStatus = j.status;
        setErr(null);
      } catch (e) {
        if (!alive) return;
        setErr((e as Error).message);
        // 오류 시에도 백오프해 실패 루프가 서버를 두드리지 않게 한다.
        delay = Math.min(delay * 2, maxIntervalMs);
      }
      if (alive) timer.current = window.setTimeout(tick, delay);
    };

    tick();
    return () => {
      alive = false;
      clear();
    };
  }, [jobId, intervalMs, maxIntervalMs]);

  return { job, err };
}
