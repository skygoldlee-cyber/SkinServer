"""
스토리지 추상화 — dev/스테이징은 로컬 볼륨, 운영은 Supabase Storage(presigned).
STORAGE_BACKEND=local|supabase 로 선택. local 은 완전 동작, supabase 는 구현 자리(seam).
키 규약: {user_id}/{job_id}/original.<ext> (RLS 폴더 정책과 정렬).
"""
from __future__ import annotations
import os


class LocalStorage:
    name = "local"
    def __init__(self, root: str):
        self.root = os.path.realpath(root)
        os.makedirs(self.root, exist_ok=True)

    def _safe(self, key: str) -> str:
        dest = os.path.realpath(os.path.join(self.root, key))
        if os.path.commonpath([self.root, dest]) != self.root:
            raise ValueError("잘못된 저장 경로")
        return dest

    def save(self, key: str, data: bytes) -> None:
        dest = self._safe(key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)

    def local_path(self, key: str) -> str:
        return self._safe(key)

    def create_signed_upload_url(self, key: str, expires_in: int = 900) -> dict:
        """local 백엔드는 presigned 업로드를 지원하지 않는다(명시적 seam)."""
        raise NotImplementedError("local 백엔드는 presigned 업로드를 지원하지 않음")


class SupabaseStorage:
    """
    Supabase Storage 실구현.
    SUPABASE_URL / SUPABASE_SERVICE_KEY / STORAGE_BUCKET 필요.
    ⚠ 자격증명은 gateway/worker 에만(엔진엔 금지 — Case A).
    """
    name = "supabase"

    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        self.bucket = os.environ.get("STORAGE_BUCKET", "skin-images")
        self.key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not (self.url and self.key):
            raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY 미설정")

    def _headers(self, extra: dict | None = None) -> dict:
        h = {
            "Authorization": f"Bearer {self.key}",
            "apikey": self.key,
        }
        if extra:
            h.update(extra)
        return h

    def save(self, key: str, data: bytes) -> None:
        import httpx
        with httpx.Client(timeout=30) as c:
            r = c.post(
                f"{self.url}/storage/v1/object/{self.bucket}/{key}",
                headers=self._headers({"Content-Type": "application/octet-stream"}),
                content=data,
            )
            r.raise_for_status()

    def local_path(self, key: str) -> str:
        raise NotImplementedError("supabase 는 로컬 경로 없음 — worker 는 서명 URL 로 fetch")

    def create_signed_upload_url(self, key: str, expires_in: int = 900) -> dict:
        """presigned 업로드 URL 발급. 반환: {url, path, token}"""
        import httpx
        with httpx.Client(timeout=30) as c:
            r = c.post(
                f"{self.url}/storage/v1/object/upload/sign/{self.bucket}/{key}",
                headers=self._headers({"Content-Type": "application/json"}),
                json={"expiresIn": expires_in},
            )
            r.raise_for_status()
            return r.json()

    def create_signed_url(self, key: str, expires_in: int = 900) -> str:
        """다운로드용 서명 URL 발급."""
        import httpx
        with httpx.Client(timeout=30) as c:
            r = c.post(
                f"{self.url}/storage/v1/object/sign/{self.bucket}/{key}",
                headers=self._headers({"Content-Type": "application/json"}),
                json={"expiresIn": expires_in},
            )
            r.raise_for_status()
            data = r.json()
            return f"{self.url}{data['signedURL']}"


def get_storage():
    if os.environ.get("STORAGE_BACKEND") == "supabase":
        return SupabaseStorage()
    return LocalStorage(os.environ.get("STORAGE_DIR", "/data/storage"))
