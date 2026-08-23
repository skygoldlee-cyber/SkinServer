from fastapi.testclient import TestClient
from tests._util import load
gw = load("gateway", "app.main")
client = TestClient(gw.app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_root_reports_modes():
    r = client.get("/")
    b = r.json()
    assert b["service"] == "gateway" and "auth" in b and "storage" in b
