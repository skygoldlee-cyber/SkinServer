import struct, zlib, uuid, pytest
from fastapi import HTTPException
from tests._util import load
gw = load("gateway", "app.main")


def _png():
    def ch(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            + ch(b'IDAT', zlib.compress(b'\x00\x00\x00\x00')) + ch(b'IEND', b''))


def test_validate_accepts_png():
    assert gw.validate_image("image/png", _png()) == ".png"


def test_reject_unsupported_type():
    with pytest.raises(HTTPException) as e:
        gw.validate_image("application/pdf", b"%PDF")
    assert e.value.status_code == 415


def test_reject_magicbyte_mismatch():
    with pytest.raises(HTTPException) as e:
        gw.validate_image("image/png", b"not-a-real-png-header")
    assert e.value.status_code == 415


def test_reject_empty():
    with pytest.raises(HTTPException) as e:
        gw.validate_image("image/png", b"")
    assert e.value.status_code == 400


def test_reject_too_large(monkeypatch):
    monkeypatch.setattr(gw, "MAX_BYTES", 10)
    with pytest.raises(HTTPException) as e:
        gw.validate_image("image/png", _png())
    assert e.value.status_code == 413


def test_require_user_dev_fallback(monkeypatch):
    monkeypatch.setattr(gw, "AUTH_MODE", "dev")
    assert isinstance(gw.require_user(None, None), uuid.UUID)


def test_require_user_strict_requires_token(monkeypatch):
    monkeypatch.setattr(gw, "AUTH_MODE", "strict")
    with pytest.raises(HTTPException) as e:
        gw.require_user(None, None)
    assert e.value.status_code == 401


def test_require_user_strict_ignores_spoofed_x_user_id(monkeypatch):
    """strict 에서 X-User-Id 는 무시되어야 한다(위조 방지) — 토큰 없으면 401."""
    monkeypatch.setattr(gw, "AUTH_MODE", "strict")
    with pytest.raises(HTTPException) as e:
        gw.require_user(None, str(uuid.uuid4()))
    assert e.value.status_code == 401


def test_require_user_strict_valid_jwt(monkeypatch):
    import jwt
    secret = "test-secret"
    monkeypatch.setattr(gw, "AUTH_MODE", "strict")
    monkeypatch.setattr(gw, "JWT_SECRET", secret)
    monkeypatch.setattr(gw, "JWT_AUD", "authenticated")
    sub = str(uuid.uuid4())
    tok = jwt.encode({"sub": sub, "aud": "authenticated"}, secret, algorithm="HS256")
    assert str(gw.require_user(f"Bearer {tok}", None)) == sub


def test_require_user_strict_bad_token(monkeypatch):
    monkeypatch.setattr(gw, "AUTH_MODE", "strict")
    monkeypatch.setattr(gw, "JWT_SECRET", "test-secret")
    with pytest.raises(HTTPException) as e:
        gw.require_user("Bearer not.a.jwt", None)
    assert e.value.status_code == 401


def test_require_user_dev_bad_uuid(monkeypatch):
    monkeypatch.setattr(gw, "AUTH_MODE", "dev")
    with pytest.raises(HTTPException) as e:
        gw.require_user(None, "not-a-uuid")
    assert e.value.status_code == 400


# ---------------------------------------------------------------------------
# P0-1: ENV=prod + AUTH_MODE!=strict fail-fast
# ---------------------------------------------------------------------------

def test_env_prod_requires_strict_auth():
    """ENV=prod 에서 AUTH_MODE!=strict 면 기동 거부 (RuntimeError)."""
    import importlib, os, sys
    old_env = os.environ.copy()
    try:
        os.environ["ENV"] = "prod"
        os.environ["AUTH_MODE"] = "dev"
        # gateway 를 다시 로드하면 fail-fast 가 터져야 한다.
        for m in list(sys.modules):
            if m == "app" or m.startswith("app."):
                del sys.modules[m]
        with pytest.raises(RuntimeError, match="AUTH_MODE=strict"):
            importlib.import_module("app.main")
    finally:
        os.environ.clear()
        os.environ.update(old_env)
        # 복원: 원래 모듈 상태로 돌려놓기 위해 재로드
        for m in list(sys.modules):
            if m == "app" or m.startswith("app."):
                del sys.modules[m]
        load("gateway", "app.main")


# ---------------------------------------------------------------------------
# P0-2: _verify_jwt() 전체 경로
# ---------------------------------------------------------------------------

def test_verify_jwt_no_authorization():
    assert gw._verify_jwt(None) is None


def test_verify_jwt_not_bearer_scheme():
    assert gw._verify_jwt("Basic abc123") is None


def test_verify_jwt_empty_token():
    assert gw._verify_jwt("Bearer ") is None
    assert gw._verify_jwt("Bearer    ") is None


def test_verify_jwt_missing_secret(monkeypatch):
    monkeypatch.setattr(gw, "JWT_SECRET", None)
    with pytest.raises(HTTPException) as e:
        gw._verify_jwt("Bearer any.token.here")
    assert e.value.status_code == 500


def test_verify_jwt_invalid_sub_uuid(monkeypatch):
    import jwt
    secret = "test-secret"
    monkeypatch.setattr(gw, "JWT_SECRET", secret)
    monkeypatch.setattr(gw, "JWT_AUD", "authenticated")
    tok = jwt.encode({"sub": "not-a-uuid", "aud": "authenticated"}, secret, algorithm="HS256")
    with pytest.raises(HTTPException) as e:
        gw._verify_jwt(f"Bearer {tok}")
    assert e.value.status_code == 401


def test_verify_jwt_missing_sub(monkeypatch):
    import jwt
    secret = "test-secret"
    monkeypatch.setattr(gw, "JWT_SECRET", secret)
    monkeypatch.setattr(gw, "JWT_AUD", "authenticated")
    tok = jwt.encode({"aud": "authenticated"}, secret, algorithm="HS256")
    with pytest.raises(HTTPException) as e:
        gw._verify_jwt(f"Bearer {tok}")
    assert e.value.status_code == 401
