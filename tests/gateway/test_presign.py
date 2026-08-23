"""Phase 4.1/4.7 — presign 발급부 검증 + 레이트리밋 단위 테스트.

엔드포인트 부팅은 DB 연결이 필요하므로(TestClient lifespan 이 _ensure_schema 를 타진 않아도
AUTO_DDL=0 이지만 앱 임포트는 가능), 순수 함수 단위로 검증한다.
"""
import uuid
import pytest
from fastapi import HTTPException

from tests._util import load

gw = load("gateway", "app.main")


# ---------------------------------------------------------------------------
# _ext_for_content_type — content-type 화이트리스트 (약한 검증, 4.7)
# ---------------------------------------------------------------------------

def test_ext_for_content_type_accepts_jpeg():
    assert gw._ext_for_content_type("image/jpeg") == ".jpg"


def test_ext_for_content_type_accepts_png_webp():
    assert gw._ext_for_content_type("image/png") == ".png"
    assert gw._ext_for_content_type("image/webp") == ".webp"


def test_ext_for_content_type_strips_params_and_case():
    assert gw._ext_for_content_type("Image/JPEG; charset=binary") == ".jpg"


def test_ext_for_content_type_rejects_unsupported():
    with pytest.raises(HTTPException) as e:
        gw._ext_for_content_type("application/pdf")
    assert e.value.status_code == 415


def test_ext_for_content_type_rejects_empty():
    with pytest.raises(HTTPException) as e:
        gw._ext_for_content_type(None)
    assert e.value.status_code == 415


# ---------------------------------------------------------------------------
# _rate_limit_presign — 사용자당 분당 발급 상한 (4.7)
# ---------------------------------------------------------------------------

def test_rate_limit_allows_under_cap():
    uid = uuid.uuid4()
    gw._presign_hits.clear()
    for _ in range(gw.PRESIGN_RATE_LIMIT):
        gw._rate_limit_presign(uid)  # 상한까지는 예외 없음


def test_rate_limit_blocks_over_cap():
    uid = uuid.uuid4()
    gw._presign_hits.clear()
    for _ in range(gw.PRESIGN_RATE_LIMIT):
        gw._rate_limit_presign(uid)
    with pytest.raises(HTTPException) as e:
        gw._rate_limit_presign(uid)
    assert e.value.status_code == 429


def test_rate_limit_is_per_user():
    gw._presign_hits.clear()
    a, b = uuid.uuid4(), uuid.uuid4()
    for _ in range(gw.PRESIGN_RATE_LIMIT):
        gw._rate_limit_presign(a)
    # 다른 사용자는 영향 없음
    gw._rate_limit_presign(b)


def test_rate_limit_window_expires(monkeypatch):
    uid = uuid.uuid4()
    gw._presign_hits.clear()
    t = [1000.0]
    monkeypatch.setattr(gw.time, "monotonic", lambda: t[0])
    for _ in range(gw.PRESIGN_RATE_LIMIT):
        gw._rate_limit_presign(uid)
    with pytest.raises(HTTPException):
        gw._rate_limit_presign(uid)
    # 61초 경과 → 윈도우 밖으로 밀려 다시 허용
    t[0] += 61.0
    gw._rate_limit_presign(uid)


# ---------------------------------------------------------------------------
# _normalize_inputs — survey/pcr JSON 정규화 (4.2)
# ---------------------------------------------------------------------------

def test_normalize_inputs_none_and_empty():
    assert gw._normalize_inputs(None, None) == {}
    assert gw._normalize_inputs("", "   ") == {}


def test_normalize_inputs_parses_json_string():
    out = gw._normalize_inputs('{"skin_type":"oily"}', None)
    assert out == {"survey": {"skin_type": "oily"}}


def test_normalize_inputs_accepts_dict():
    out = gw._normalize_inputs({"skin_type": "dry"}, {"q": 1})
    assert out["survey"] == {"skin_type": "dry"}
    assert out["pcr"] == {"q": 1}


def test_normalize_inputs_rejects_bad_json():
    with pytest.raises(HTTPException) as e:
        gw._normalize_inputs("{not json", None)
    assert e.value.status_code == 400


def test_normalize_inputs_rejects_non_object():
    with pytest.raises(HTTPException) as e:
        gw._normalize_inputs('["a","b"]', None)
    assert e.value.status_code == 400


# ---------------------------------------------------------------------------
# P0-3: presign_upload() 엔드포인트 단위 테스트
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, patch


def _presign_client(monkeypatch, storage_mock):
    """presign_upload 엔드포인트를 TestClient 로 테스트하기 위한 헬퍼.
    DB 와 storage 를 mock 하고, require_user 를 우회한다."""
    monkeypatch.setattr(gw, "storage", storage_mock)
    monkeypatch.setattr(gw, "require_user", lambda a, b: uuid.uuid4())
    monkeypatch.setattr(gw, "_rate_limit_presign", lambda uid: None)
    # DB 연결은 사용하지 않으므로 pass
    return gw


def test_presign_upload_rejects_non_dict_payload(monkeypatch):
    storage_mock = MagicMock()
    _presign_client(monkeypatch, storage_mock)
    with pytest.raises(HTTPException) as e:
        # payload 가 dict 가 아니면 _ext_for_content_type 에서 415
        gw.presign_upload(payload=None, authorization=None, x_user_id=None)
    assert e.value.status_code == 415


def test_presign_upload_rejects_bad_size_bytes_type(monkeypatch):
    storage_mock = MagicMock()
    _presign_client(monkeypatch, storage_mock)
    with pytest.raises(HTTPException) as e:
        gw.presign_upload(payload={"content_type": "image/png", "size_bytes": "not-int"},
                          authorization=None, x_user_id=None)
    assert e.value.status_code == 400


def test_presign_upload_rejects_non_positive_size(monkeypatch):
    storage_mock = MagicMock()
    _presign_client(monkeypatch, storage_mock)
    with pytest.raises(HTTPException) as e:
        gw.presign_upload(payload={"content_type": "image/png", "size_bytes": 0},
                          authorization=None, x_user_id=None)
    assert e.value.status_code == 400


def test_presign_upload_rejects_oversize(monkeypatch):
    storage_mock = MagicMock()
    _presign_client(monkeypatch, storage_mock)
    with pytest.raises(HTTPException) as e:
        gw.presign_upload(payload={"content_type": "image/png", "size_bytes": gw.MAX_BYTES + 1},
                          authorization=None, x_user_id=None)
    assert e.value.status_code == 413


def test_presign_upload_rejects_non_supabase_storage(monkeypatch):
    """local 스토리지 백엔드에서는 presign 을 지원하지 않는다(409)."""
    class FakeLocalStorage:
        name = "local"
    _presign_client(monkeypatch, FakeLocalStorage())
    with pytest.raises(HTTPException) as e:
        gw.presign_upload(payload={"content_type": "image/png"},
                          authorization=None, x_user_id=None)
    assert e.value.status_code == 409


def _make_real_supabase_storage(monkeypatch):
    """gateway 가 실제로 isinstance 체크에 쓰는 SupabaseStorage 의 실제 인스턴스를 만든다.

    presign_upload() 낶에서 함수 로컬 임포트(`from .storage import SupabaseStorage`)를
    하기 때문에, 테스트가 `services.gateway.app.storage` 를 임포트하면 sys.path 조작으로
    인해 별개의 클래스 객체가 되어 isinstance 가 False 가 된다. 따라서 gateway 모듈이
    실제로 사용하는 `app.storage` 네임스페이스에서 SupabaseStorage 를 가져와 인스턴스화한다.
    """
    import sys
    storage_mod = sys.modules["app.storage"]
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc-key")
    return storage_mod.SupabaseStorage()


def test_presign_upload_returns_signed_url(monkeypatch):
    """정상 요청 시 signed URL 을 반환한다."""
    real_storage = _make_real_supabase_storage(monkeypatch)
    monkeypatch.setattr(
        real_storage,
        "create_signed_upload_url",
        lambda key, expires_in=900: {"url": "https://signed", "path": key, "token": "t"},
    )
    _presign_client(monkeypatch, real_storage)
    out = gw.presign_upload(payload={"content_type": "image/png"},
                            authorization=None, x_user_id=None)
    assert "job_id" in out and "image_key" in out
    assert out["signed"]["url"] == "https://signed"
    assert out["expires_in"] == gw.PRESIGN_EXPIRES


def test_presign_upload_storage_failure_returns_502(monkeypatch):
    """Supabase 장애 시 502 를 반환한다."""
    real_storage = _make_real_supabase_storage(monkeypatch)
    def _raise(key, expires_in=900):
        raise RuntimeError("supabase down")
    monkeypatch.setattr(real_storage, "create_signed_upload_url", _raise)
    _presign_client(monkeypatch, real_storage)
    with pytest.raises(HTTPException) as e:
        gw.presign_upload(payload={"content_type": "image/png"},
                          authorization=None, x_user_id=None)
    assert e.value.status_code == 502


# ---------------------------------------------------------------------------
# P0-4: analyze() presigned 경로 image_key 검증
# ---------------------------------------------------------------------------

def _analyze_client(monkeypatch):
    """analyze 엔드포인트를 테스트하기 위한 헬퍼. DB 는 mock."""
    monkeypatch.setattr(gw, "require_user", lambda a, b: uuid.UUID("11111111-1111-1111-1111-111111111111"))
    # DB 커서 mock
    cur = MagicMock()
    cur.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = lambda s: cur
    conn.cursor.return_value.__exit__ = lambda s, *a: None
    conn.__enter__ = lambda s: conn
    conn.__exit__ = lambda s, *a: None
    monkeypatch.setattr(gw, "db", lambda: conn)
    return gw


import asyncio


def _run_analyze(coro):
    """async analyze() 를 동기적으로 실행한다."""
    return asyncio.get_event_loop().run_until_complete(coro)


def test_analyze_presigned_rejects_bad_image_key_parts(monkeypatch):
    """image_key 의 경로 조각이 3개가 아니면 400."""
    _analyze_client(monkeypatch)
    with pytest.raises(HTTPException) as e:
        _run_analyze(gw.analyze(image=None, survey=None, pcr=None,
                                payload={"image_key": "onlyonepart"},
                                authorization=None, x_user_id=None))
    assert e.value.status_code == 400


def test_analyze_presigned_rejects_wrong_user_prefix(monkeypatch):
    """image_key 의 user_id 가 인증 사용자와 다륩면 400."""
    _analyze_client(monkeypatch)
    bad_key = f"22222222-2222-2222-2222-222222222222/{uuid.uuid4()}/original.png"
    with pytest.raises(HTTPException) as e:
        _run_analyze(gw.analyze(image=None, survey=None, pcr=None,
                                payload={"image_key": bad_key},
                                authorization=None, x_user_id=None))
    assert e.value.status_code == 400


def test_analyze_presigned_rejects_bad_extension(monkeypatch):
    """허용되지 않은 확장자(.gif 등)는 400."""
    _analyze_client(monkeypatch)
    bad_key = f"11111111-1111-1111-1111-111111111111/{uuid.uuid4()}/original.gif"
    with pytest.raises(HTTPException) as e:
        _run_analyze(gw.analyze(image=None, survey=None, pcr=None,
                                payload={"image_key": bad_key},
                                authorization=None, x_user_id=None))
    assert e.value.status_code == 400


def test_analyze_presigned_rejects_non_original_prefix(monkeypatch):
    """original. 접두사가 아니면 400."""
    _analyze_client(monkeypatch)
    bad_key = f"11111111-1111-1111-1111-111111111111/{uuid.uuid4()}/photo.png"
    with pytest.raises(HTTPException) as e:
        _run_analyze(gw.analyze(image=None, survey=None, pcr=None,
                                payload={"image_key": bad_key},
                                authorization=None, x_user_id=None))
    assert e.value.status_code == 400


def test_analyze_presigned_rejects_mismatched_job_id(monkeypatch):
    """명시한 job_id 가 image_key 의 job_id 와 다륩면 400."""
    _analyze_client(monkeypatch)
    key_job = str(uuid.uuid4())
    bad_key = f"11111111-1111-1111-1111-111111111111/{key_job}/original.png"
    with pytest.raises(HTTPException) as e:
        _run_analyze(gw.analyze(image=None, survey=None, pcr=None,
                                payload={"image_key": bad_key, "job_id": str(uuid.uuid4())},
                                authorization=None, x_user_id=None))
    assert e.value.status_code == 400


def test_analyze_presigned_rejects_bad_job_id_format(monkeypatch):
    """job_id 가 UUID 형식이 아니면 400."""
    _analyze_client(monkeypatch)
    bad_key = f"11111111-1111-1111-1111-111111111111/not-a-uuid/original.png"
    with pytest.raises(HTTPException) as e:
        _run_analyze(gw.analyze(image=None, survey=None, pcr=None,
                                payload={"image_key": bad_key, "job_id": "also-not-a-uuid"},
                                authorization=None, x_user_id=None))
    assert e.value.status_code == 400


def test_analyze_presigned_extracts_job_id_from_key(monkeypatch):
    """job_id 생략 시 image_key 에서 UUID 를 추출해 사용한다."""
    _analyze_client(monkeypatch)
    job_id = str(uuid.uuid4())
    good_key = f"11111111-1111-1111-1111-111111111111/{job_id}/original.png"
    out = _run_analyze(gw.analyze(image=None, survey=None, pcr=None,
                                  payload={"image_key": good_key},
                                  authorization=None, x_user_id=None))
    assert out.status_code == 202
    assert out.body  # JSONResponse


def test_analyze_presigned_accepts_explicit_matching_job_id(monkeypatch):
    """명시한 job_id 가 image_key 와 일치하면 202."""
    _analyze_client(monkeypatch)
    job_id = str(uuid.uuid4())
    good_key = f"11111111-1111-1111-1111-111111111111/{job_id}/original.png"
    out = _run_analyze(gw.analyze(image=None, survey=None, pcr=None,
                                  payload={"image_key": good_key, "job_id": job_id},
                                  authorization=None, x_user_id=None))
    assert out.status_code == 202


