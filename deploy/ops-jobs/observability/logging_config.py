#!/usr/bin/env python3
# =============================================================
# logging_config.py — 구조적 JSON 로깅 + job_id 상관ID (②)
#
#  왜: 한 요청/잡을 처음부터 끝까지 추적하려면 모든 로그 줄에 job_id 가 붙어야 함.
#      JSON 로그면 나중에 수집/검색(Loki·CloudWatch·jq)도 쉬움.
#
#  설치(gateway/worker 부팅 시):
#     from followup_P1.logging_config import setup_logging, set_job_id
#     setup_logging()                      # JSON 포맷 + 스크러빙 필터
#     ...
#     set_job_id(job_id)                   # 잡 처리 시작 시 1회
#
#  FastAPI 미들웨어 예(요청마다 상관ID 세팅):
#     @app.middleware("http")
#     async def cid(request, call_next):
#         set_job_id(request.headers.get("x-job-id") or new_id())
#         return await call_next(request)
#
#  외부 의존성 없음(표준 logging 만). log-scrub.py 가 있으면 함께 부착.
# =============================================================
import contextvars
import json
import logging
import sys
import time

_job_id: "contextvars.ContextVar[str]" = contextvars.ContextVar("job_id", default="-")


def set_job_id(value: str) -> None:
    _job_id.set(value or "-")


class JobIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.job_id = _job_id.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
                  + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "job_id": getattr(record, "job_id", "-"),
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # 예약 키 외 추가 필드(extra=) 통과
        for k, v in record.__dict__.items():
            if k not in payload and k not in _RESERVED:
                try:
                    json.dumps(v); payload[k] = v
                except Exception:
                    payload[k] = str(v)
        return json.dumps(payload, ensure_ascii=False)


_RESERVED = set(vars(logging.makeLogRecord({})).keys()) | {"job_id", "msg", "message", "asctime"}


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    h.addFilter(JobIdFilter())
    # 로그 스크러빙 필터가 있으면 함께(민감정보 마스킹)
    try:
        from log_scrub import ScrubFilter  # 같은 폴더
        h.addFilter(ScrubFilter())
    except Exception:
        pass
    root.addHandler(h)


if __name__ == "__main__":
    setup_logging()
    set_job_id("demo-123")
    logging.getLogger("skinlens").info("분석 시작", extra={"stage": "analysis"})
    logging.getLogger("skinlens").warning("VRAM 높음", extra={"vram_pct": 91})
