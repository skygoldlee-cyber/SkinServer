"""
소유권(IDOR) 회귀 — dev 모드에서 X-User-Id 로 사용자를 분리해,
남의 job 은 조회/이벤트/리포트 모두 404 로 막히는지 검증한다.
"""
import os, struct, zlib
from fastapi.testclient import TestClient
import pytest

from tests._util import load

pytestmark = pytest.mark.integration

USER_A = "11111111-1111-1111-1111-111111111111"
USER_B = "22222222-2222-2222-2222-222222222222"


def _png(w=8, h=8):
    def ch(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    raw = b''.join(b'\x00' + b'\x50\x70\x90' * w for _ in range(h))
    return (b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
            + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b''))


def test_cross_user_job_access_is_404(database_url, schema, storage_dir):
    os.environ["DATABASE_URL"] = database_url
    os.environ["STORAGE_DIR"] = storage_dir
    os.environ["AUTO_DDL"] = "0"; os.environ["AUTH_MODE"] = "dev"

    gw = load("gateway", "app.main")
    client = TestClient(gw.app)

    # A 가 업로드
    r = client.post("/analyze", files={"image": ("f.png", _png(), "image/png")},
                    headers={"X-User-Id": USER_A})
    assert r.status_code == 202
    jid = r.json()["job_id"]

    # A 는 본인 job 조회 가능
    assert client.get(f"/jobs/{jid}", headers={"X-User-Id": USER_A}).status_code == 200

    # B 는 A 의 job 을 조회/이벤트/리포트 모두 404
    for path in (f"/jobs/{jid}", f"/jobs/{jid}/events", f"/jobs/{jid}/report"):
        assert client.get(path, headers={"X-User-Id": USER_B}).status_code == 404, path

    # 목록도 사용자별로 분리
    assert len(client.get("/jobs", headers={"X-User-Id": USER_A}).json()["jobs"]) >= 1
    assert client.get("/jobs", headers={"X-User-Id": USER_B}).json()["jobs"] == []
