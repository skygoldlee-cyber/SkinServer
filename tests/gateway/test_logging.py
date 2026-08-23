import json, logging
from tests._util import load
ls = load("gateway", "app.logging_setup")


def test_json_formatter_outputs_valid_json_with_corr():
    rec = logging.LogRecord("gateway", logging.INFO, __file__, 1, "hi", None, None)
    rec.job_id = "J1"; rec.stage = "claimed"
    out = json.loads(ls.JsonFormatter().format(rec))
    assert out["msg"] == "hi" and out["job_id"] == "J1" and out["stage"] == "claimed"
    assert out["level"] == "INFO"
