"""구조적 JSON 로깅(공통). job_id 상관ID를 붙여 파이프라인 추적을 쉽게 한다."""
import json, logging, os, sys, time


class JsonFormatter(logging.Formatter):
    def format(self, r: logging.LogRecord) -> str:
        base = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(r.created)),
            "level": r.levelname, "svc": os.environ.get("SVC_NAME", r.name),
            "msg": r.getMessage(),
        }
        for k in ("job_id", "stage", "attempt"):
            v = getattr(r, k, None)
            if v is not None:
                base[k] = v
        if r.exc_info:
            base["exc"] = self.formatException(r.exc_info)
        return json.dumps(base, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    lg = logging.getLogger(name)
    if not lg.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(JsonFormatter())
        lg.addHandler(h)
        lg.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
        lg.propagate = False
    return lg
