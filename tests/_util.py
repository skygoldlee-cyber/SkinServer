"""
서비스별 격리 로더 — gateway/analysis/prescription 이 모두 'app' 패키지라 한 세션에서
그대로 임포트하면 충돌한다. 로드 직전에 app* 를 sys.modules 에서 비우고, 해당 서비스
디렉토리만 path 에 올려 임포트한다(테스트는 반환된 모듈 참조를 top-level 에 바인딩).
"""
import os, sys, pathlib, importlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _env():
    os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
    os.environ.setdefault("STORAGE_DIR", "/tmp/sl_test_storage")
    os.environ.setdefault("ENGINE_ANALYSIS_URL", "http://engine-analysis:8000")
    os.environ.setdefault("ENGINE_PRESCRIPTION_URL", "http://engine-prescription:8000")


def load(service: str, dotted: str):
    _env()
    for m in list(sys.modules):
        if m == "app" or m.startswith("app.") or m in ("worker", "logging_setup"):
            del sys.modules[m]
    svc = str(ROOT / "services" / service)
    sys.path = [p for p in sys.path if "/services/" not in p.replace("\\", "/")]
    sys.path.insert(0, svc)
    return importlib.import_module(dotted)
