from fastapi.testclient import TestClient
from tests._util import load
main = load("engine-prescription", "app.main")
client = TestClient(main.app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_prescribe_with_analysis():
    body = {"analysis": {"score": 50, "metrics": {"redness": {"value": 20, "source": "cv"}}}}
    r = client.post("/prescribe", json=body)
    assert r.status_code == 200
    b = r.json()
    assert b["grade"] == "보통" and b["prescription_ratio_pct"] == 1.0
    assert b["contract_version"] == "1.0.0" and "per_metric" in b


def test_prescribe_survey_only():
    r = client.post("/prescribe", json={"survey": {"skin_type": "sensitive"}})
    assert r.status_code == 200 and r.json()["score_source"] == "default"


def test_prescribe_requires_at_least_one_input():
    r = client.post("/prescribe", json={})
    assert r.status_code == 400
