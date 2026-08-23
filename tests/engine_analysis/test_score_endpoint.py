import struct, zlib
from fastapi.testclient import TestClient
from tests._util import load
main = load("engine-analysis", "app.main")
client = TestClient(main.app)


def _png(w=8, h=8):
    def ch(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    raw = b''.join(b'\x00' + b'\x40\x80\xc0' * w for _ in range(h))
    return (b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
            + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b''))


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_score_returns_validated_schema():
    r = client.post("/score", files={"image": ("f.png", _png(), "image/png")})
    assert r.status_code == 200
    b = r.json()
    assert set(b["metrics"]) and "score" in b and b["contract_version"] == "1.0.0"


def test_score_rejects_bad_image():
    r = client.post("/score", files={"image": ("f.png", b"not-an-image", "image/png")})
    assert r.status_code == 400
