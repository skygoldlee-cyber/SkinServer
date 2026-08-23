"""구조적 JSON 로깅(worker 사본). gateway 와 동일 포맷."""
import json, logging, os, sys, time
class JsonFormatter(logging.Formatter):
    def format(self, r):
        b = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(r.created)),
             "level": r.levelname, "svc": os.environ.get("SVC_NAME", r.name), "msg": r.getMessage()}
        for k in ("job_id", "stage", "attempt"):
            v = getattr(r, k, None)
            if v is not None: b[k] = v
        if r.exc_info: b["exc"] = self.formatException(r.exc_info)
        return json.dumps(b, ensure_ascii=False)
def get_logger(name):
    lg = logging.getLogger(name)
    if not lg.handlers:
        h = logging.StreamHandler(sys.stdout); h.setFormatter(JsonFormatter())
        lg.addHandler(h); lg.setLevel(os.environ.get("LOG_LEVEL", "INFO")); lg.propagate = False
    return lg
