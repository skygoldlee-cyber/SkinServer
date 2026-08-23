import os
import sys
from unittest.mock import patch

import pytest

from tests._util import load

st = load("worker", "storage")


# ---------------------------------------------------------------------------
# _Local
# ---------------------------------------------------------------------------

def test_local_resolve_existing(tmp_path):
    p = tmp_path / "u" / "j"
    p.mkdir(parents=True)
    (p / "original.png").write_bytes(b"img")
    s = st._Local(str(tmp_path))
    assert s.resolve_local("u/j/original.png") == str(p / "original.png")


def test_local_resolve_missing_returns_none(tmp_path):
    s = st._Local(str(tmp_path))
    assert s.resolve_local("u/j/original.png") is None


def test_local_path_traversal_blocked(tmp_path):
    s = st._Local(str(tmp_path))
    with pytest.raises(ValueError):
        s.resolve_local("../../etc/passwd")


def test_get_storage_default_local(monkeypatch):
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    assert st.get_storage().name == "local"


# ---------------------------------------------------------------------------
# _Supabase — 자격증명 검증
# ---------------------------------------------------------------------------

def test_supabase_requires_credentials(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SUPABASE_URL.*SUPABASE_SERVICE_KEY"):
        st._Supabase()


def test_supabase_accepts_service_role_key_alias(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "role-key")
    s = st._Supabase()
    assert s.key == "role-key"
    assert s.bucket == "skin-images"


def test_get_storage_supabase(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc-key")
    assert st.get_storage().name == "supabase"


# ---------------------------------------------------------------------------
# _Supabase — resolve_local (httpx mock)
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

    def iter_bytes(self, chunk_size=65536):
        # 스트리밍 mock — content 를 chunk_size 단위로 나눠 흘려병낸다.
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i:i + chunk_size]


class _FakeStreamCtx:
    """httpx stream() 의 컨텍스트매니저 mock — 응답 객체를 그대로 돌려준다."""

    def __init__(self, response):
        self._response = response

    def __enter__(self):
        return self._response

    def __exit__(self, *exc):
        return False


class _FakeClient:
    instances: list = []
    next_default_json: dict = {}
    next_default_content: bytes = b""
    next_default_status: int = 200
    next_responses: list = []

    def __init__(self, *args, **kwargs):
        self.calls: list = []
        self.responses: list = []
        if _FakeClient.next_responses:
            self.responses.append(_FakeClient.next_responses.pop(0))
        self.default_json: dict = _FakeClient.next_default_json
        self.default_content: bytes = _FakeClient.next_default_content
        self.default_status: int = _FakeClient.next_default_status
        _FakeClient.instances.append(self)

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

    def stream(self, method, url, **kwargs):
        # httpx.Client.stream 의 mock — _next 와 동일하게 호출을 기록하고
        # _FakeStreamCtx 로 감싸 컨텍스트매니저 프로토콜을 맞춘다.
        return _FakeStreamCtx(self._next(method, url, **kwargs))


@pytest.fixture(autouse=True)
def _reset_fake_client():
    _FakeClient.instances = []
    yield
    _FakeClient.instances = []


def _make_supabase(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc-key")
    monkeypatch.setenv("STORAGE_BUCKET", "skin-images")
    return st._Supabase()


def test_supabase_resolve_local_fetches_via_signed_url(monkeypatch):
    s = _make_supabase(monkeypatch)
    # patch 블록 내에서 Client 인스턴스가 생성되므로,
    # next_default_* 클래스 변수로 응답을 설정해 둔다.
    _FakeClient.next_default_json = {"signedURL": "/storage/v1/object/sign/skin-images/u/j/original.png?token=abc"}
    _FakeClient.next_default_content = b"img-bytes"
    with patch("httpx.Client", _FakeClient):
        out = s.resolve_local("u/j/original.png")
    assert out is not None
    assert os.path.exists(out)
    assert open(out, "rb").read() == b"img-bytes"
    os.unlink(out)

    sign_client = _FakeClient.instances[0]
    method, url, kwargs = sign_client.calls[0]
    assert method == "POST"
    assert url == "https://proj.supabase.co/storage/v1/object/sign/skin-images/u/j/original.png"
    assert kwargs["json"] == {"expiresIn": 900}
    assert kwargs["headers"]["Authorization"] == "Bearer svc-key"

    dl_client = _FakeClient.instances[1]
    method, url, _ = dl_client.calls[0]
    assert method == "GET"
    assert url == "https://proj.supabase.co/storage/v1/object/sign/skin-images/u/j/original.png?token=abc"


def test_supabase_resolve_local_404_returns_none(monkeypatch):
    s = _make_supabase(monkeypatch)
    # sign 응답은 정상, download 만 404 여야 한다.
    # 첫 번째 Client(sign)는 next_responses[0], 두 번째 Client(download)는 next_responses[1].
    _FakeClient.next_responses = [
        _FakeResponse(json_data={"signedURL": "/storage/v1/object/sign/skin-images/u/j/original.png?token=abc"}),
        _FakeResponse(status_code=404),
    ]
    with patch("httpx.Client", _FakeClient):
        out = s.resolve_local("u/j/original.png")
    assert out is None

    sign_client = _FakeClient.instances[0]
    method, url, kwargs = sign_client.calls[0]
    assert method == "POST"
    assert url == "https://proj.supabase.co/storage/v1/object/sign/skin-images/u/j/original.png"

    dl_client = _FakeClient.instances[1]
    method, url, _ = dl_client.calls[0]
    assert method == "GET"
    assert url == "https://proj.supabase.co/storage/v1/object/sign/skin-images/u/j/original.png?token=abc"


# ---------------------------------------------------------------------------
# (2-3) 스트리밍 다운로드 상한 — 초과 시 ValueError + 임시파일 정리
# ---------------------------------------------------------------------------

def test_supabase_resolve_local_download_limit(monkeypatch):
    """MAX_DOWNLOAD_BYTES 초과 시 ValueError 를 던지고 임시파일을 남기지 않는다(2-3)."""
    s = _make_supabase(monkeypatch)
    monkeypatch.setattr(st, "MAX_DOWNLOAD_BYTES", 10)  # 10 바이트 상한
    _FakeClient.next_default_json = {"signedURL": "/storage/v1/object/sign/skin-images/u/j/original.png?token=abc"}
    _FakeClient.next_default_content = b"x" * 100  # 100 바이트 → 초과
    with patch("httpx.Client", _FakeClient):
        with pytest.raises(ValueError, match="상한 초과"):
            s.resolve_local("u/j/original.png")


def test_supabase_resolve_local_cleans_up_on_download_error(monkeypatch):
    """다운로드 중 예외가 나도 임시파일이 tmpfs 에 남지 않아야 한다(1-1 심화)."""
    s = _make_supabase(monkeypatch)
    _FakeClient.next_default_json = {"signedURL": "/storage/v1/object/sign/skin-images/u/j/original.png?token=abc"}
    _FakeClient.next_default_content = b"x" * 100
    monkeypatch.setattr(st, "MAX_DOWNLOAD_BYTES", 10)
    with patch("httpx.Client", _FakeClient):
        with pytest.raises(ValueError):
            s.resolve_local("u/j/original.png")
    # _Supabase.resolve_local 이 만든 임시파일이 정리됐는지 확인한다.
    # 이전 테스트의 잔여물이 있을 수 있으므로, 현재 테스트에서 생성된 파일만 추적한다.
    import tempfile, glob
    # 테스트 시작 전 잔여물을 먼저 정리한다(격리).
    for f in glob.glob(os.path.join(tempfile.gettempdir(), "sl_*")):
        try:
            os.unlink(f)
        except OSError:
            pass
    with patch("httpx.Client", _FakeClient):
        with pytest.raises(ValueError):
            s.resolve_local("u/j/original.png")
    leftovers = glob.glob(os.path.join(tempfile.gettempdir(), "sl_*"))
    assert leftovers == [], f"임시파일이 정리되지 않음: {leftovers}"
