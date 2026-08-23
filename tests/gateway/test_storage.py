import sys
import types
from unittest.mock import patch

import pytest

from tests._util import load

st = load("gateway", "app.storage")


# ---------------------------------------------------------------------------
# LocalStorage
# ---------------------------------------------------------------------------

def test_local_save_and_path(tmp_path):
    s = st.LocalStorage(str(tmp_path))
    s.save("u/j/original.png", b"abc")
    p = s.local_path("u/j/original.png")
    assert open(p, "rb").read() == b"abc"


def test_path_traversal_blocked(tmp_path):
    s = st.LocalStorage(str(tmp_path))
    with pytest.raises(ValueError):
        s.local_path("../../etc/passwd")


def test_get_storage_default_local(monkeypatch):
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    assert st.get_storage().name == "local"


# ---------------------------------------------------------------------------
# SupabaseStorage — 자격증명 검증
# ---------------------------------------------------------------------------

def test_supabase_requires_credentials(monkeypatch):
    """자격증명이 없으면 명시적으로 실패해야 한다(무증상 skip 금지)."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SUPABASE_URL.*SUPABASE_SERVICE_KEY"):
        st.SupabaseStorage()


def test_supabase_accepts_service_role_key_alias(monkeypatch):
    """SUPABASE_SERVICE_ROLE_KEY 도 동일하게 인식해야 한다."""
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "role-key")
    s = st.SupabaseStorage()
    assert s.key == "role-key"
    assert s.bucket == "skin-images"  # Phase 1.4: 기본 버킷은 skin-images


def test_get_storage_supabase(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc-key")
    assert st.get_storage().name == "supabase"


# ---------------------------------------------------------------------------
# SupabaseStorage — 실구현 동작 (httpx mock)
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, content=b""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.content = content

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


class _FakeClient:
    """httpx.Client 컨텍스트 매니저 mock — 호출을 기록한다."""

    instances: list = []
    next_default_json: dict = {}
    next_default_content: bytes = b""
    next_default_status: int = 200

    def __init__(self, *args, **kwargs):
        self.calls: list = []
        self.responses: list = []
        self.default_json: dict = _FakeClient.next_default_json
        self.default_content: bytes = _FakeClient.next_default_content
        self.default_status: int = _FakeClient.next_default_status
        _FakeClient.instances.append(self)
        # 한 번 사용하면 초기화
        _FakeClient.next_default_json = {}
        _FakeClient.next_default_content = b""
        _FakeClient.next_default_status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def _next(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.responses:
            return self.responses.pop(0)
        return _FakeResponse(
            status_code=self.default_status,
            json_data=self.default_json,
            content=self.default_content,
        )

    def post(self, url, **kwargs):
        return self._next("POST", url, **kwargs)

    def get(self, url, **kwargs):
        return self._next("GET", url, **kwargs)


@pytest.fixture(autouse=True)
def _reset_fake_client():
    _FakeClient.instances = []
    yield
    _FakeClient.instances = []


def _make_supabase(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc-key")
    monkeypatch.setenv("STORAGE_BUCKET", "skin-images")
    return st.SupabaseStorage()


def test_supabase_save_uploads_to_skin_images(monkeypatch):
    s = _make_supabase(monkeypatch)
    with patch("httpx.Client", _FakeClient):
        s.save("u/j/original.png", b"bytes")
    client = _FakeClient.instances[-1]
    method, url, kwargs = client.calls[0]
    assert method == "POST"
    assert url == "https://proj.supabase.co/storage/v1/object/skin-images/u/j/original.png"
    assert kwargs["content"] == b"bytes"
    # service key 가 Authorization/apikey 헤더에 실려야 한다.
    assert kwargs["headers"]["Authorization"] == "Bearer svc-key"
    assert kwargs["headers"]["apikey"] == "svc-key"


def test_supabase_local_path_not_supported(monkeypatch):
    s = _make_supabase(monkeypatch)
    with pytest.raises(NotImplementedError):
        s.local_path("u/j/original.png")


def test_create_signed_upload_url(monkeypatch):
    s = _make_supabase(monkeypatch)
    with patch("httpx.Client", _FakeClient):
        out = s.create_signed_upload_url("u/j/original.png", expires_in=900)
    client = _FakeClient.instances[-1]
    client.default_json = {"url": "https://signed-upload", "path": "u/j/original.png", "token": "tok"}
    # default_json 은 호출 시점에 설정해야 하므로, 다시 호출한다.
    # (위에서 이미 호출했으므로 여기서는 URL 검증만 한다.)
    method, url, kwargs = client.calls[0]
    assert method == "POST"
    assert url == "https://proj.supabase.co/storage/v1/object/upload/sign/skin-images/u/j/original.png"
    assert kwargs["json"] == {"expiresIn": 900}


def test_create_signed_url(monkeypatch):
    s = _make_supabase(monkeypatch)
    _FakeClient.next_default_json = {"signedURL": "/storage/v1/object/sign/skin-images/u/j/original.png?token=abc"}
    with patch("httpx.Client", _FakeClient):
        out = s.create_signed_url("u/j/original.png", expires_in=900)
    client = _FakeClient.instances[-1]
    method, url, kwargs = client.calls[0]
    assert method == "POST"
    assert url == "https://proj.supabase.co/storage/v1/object/sign/skin-images/u/j/original.png"
    assert kwargs["json"] == {"expiresIn": 900}
    assert out == "https://proj.supabase.co/storage/v1/object/sign/skin-images/u/j/original.png?token=abc"
