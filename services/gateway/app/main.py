"""
Gateway (FastAPI) — 단일 쓰기 주체 + 파이프라인 관측/보안 경계.
업로드 검증·저장 → Job 등록 → 상태/타임라인/리포트 조회. 엔진엔 쓰기 권한/자격증명 없음(Case A).

보완 반영:
  [보안] AUTH_MODE=strict 면 검증된 X-User-Id(UUID) 필수(없으면 401). dev 면 폴백.
  [안정] 스키마 auto-DDL 은 AUTO_DDL=1(dev)에서만. 운영은 마이그레이션(deploy/db/migrations).
  [스토리지] STORAGE_BACKEND=local|supabase 추상화(storage.py).
  [관측] 구조적 JSON 로깅(job_id 상관ID).
  [도메인] prescriptions 테이블 + jobs.attempts. 리포트 HTML seam(/jobs/{id}/report).
"""
import os, json, time, uuid, html, datetime as dt
from collections import defaultdict, deque
from contextlib import asynccontextmanager, contextmanager

import httpx, jwt
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from fastapi import FastAPI, UploadFile, File, Form, Body, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

from .storage import get_storage
from .logging_setup import get_logger

os.environ.setdefault("SVC_NAME", "gateway")
log = get_logger("gateway")

DATABASE_URL = os.environ["DATABASE_URL"]
ENGINE_ANALYSIS_URL = os.environ.get("ENGINE_ANALYSIS_URL", "http://engine-analysis:8000").rstrip("/")
ENGINE_PRESCRIPTION_URL = os.environ.get("ENGINE_PRESCRIPTION_URL", "http://engine-prescription:8000").rstrip("/")
DEV_DEBUG = os.environ.get("DEV_DEBUG", "0") == "1"
AUTO_DDL = os.environ.get("AUTO_DDL", "0") == "1"
AUTH_MODE = os.environ.get("AUTH_MODE", "dev")            # dev | strict
ENV = os.environ.get("ENV", "dev").lower()               # dev | staging | prod
DEV_FALLBACK_USER_ID = os.environ.get("DEV_FALLBACK_USER_ID", "00000000-0000-0000-0000-000000000000")
# strict 인증: Supabase JWT(HS256) 검증에 쓰는 비밀키. SUPABASE_JWT_SECRET 우선, 없으면 JWT_SECRET.
JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET") or os.environ.get("JWT_SECRET")
JWT_AUD = os.environ.get("JWT_AUD", "authenticated")
# (2-1) JWT iss 고정 — SUPABASE_URL 기반으로 발급자를 강제해 타 프로젝트 토큰 유입을 차단.
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
JWT_ISS = os.environ.get("JWT_ISS") or (f"{SUPABASE_URL}/auth/v1" if SUPABASE_URL else None)

# (2-1) fail-fast — ENV=prod 에서 AUTH_MODE!=strict 면 기동 거부.
# dev 모드(X-User-Id 신뢰)가 운영에 새어들면 누구나 임의 유저로 위장 가능하므로,
# engine-prescription 의 load_config(ENV=prod 에서 example 금지)와 같은 fail-fast 를 인증에도 적용한다.
if ENV == "prod" and AUTH_MODE != "strict":
    raise RuntimeError(
        "ENV=prod 에서는 AUTH_MODE=strict 가 필수입니다. "
        "dev 모드(X-User-Id 무검증 신뢰)가 운영에 노출되면 임의 사용자 위장이 가능합니다."
    )

ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAGIC = {".jpg": [b"\xff\xd8\xff"], ".png": [b"\x89PNG\r\n\x1a\n"], ".webp": [b"RIFF"]}
MAX_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))

# CORS 허용 오리진 — Vercel 도메인 분리로 인해 필수(Phase 3.1).
# 쉼표로 구분된 환경변수. 미설정 시 로컬 개발용 기본값만 허용.
_CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
if not _CORS_ORIGINS:
    _CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]

# ---- Phase 4: presigned 업로드 전환 -----------------------------------------
# 구 multipart 업로드(/analyze multipart) 호환 플래그. 초기엔 1 로 열어 두고,
# 웹이 presigned 로 전환 확인 후 0 으로 닫는다(제거 예정).
ENABLE_LEGACY_UPLOAD = os.environ.get("ENABLE_LEGACY_UPLOAD", "1") == "1"
# presigned 발급 만료(초). 짧게 유지해 서명 URL 유출 피해를 줄인다(설계 04 §리스크).
PRESIGN_EXPIRES = int(os.environ.get("PRESIGN_EXPIRES_SEC", "900"))      # 15분
# 업로드 전용 레이트리밋(사용자당 분당 presign 발급 상한). presigned 남용 방지.
PRESIGN_RATE_LIMIT = int(os.environ.get("PRESIGN_RATE_PER_MIN", "10"))

storage = get_storage()

# 사용자별 presign 발급 시각(초) 슬라이딩 윈도우. 단일 프로세스 인메모리 구현 —
# gateway 는 1 레플리카 전제(큐는 Postgres SKIP LOCKED). 다중 레플리카 도입 시 Redis 로 이관.
_presign_hits: dict[str, deque] = defaultdict(deque)


def _rate_limit_presign(user_id: uuid.UUID) -> None:
    now = time.monotonic()
    dq = _presign_hits[str(user_id)]
    while dq and now - dq[0] > 60:
        dq.popleft()
    if len(dq) >= PRESIGN_RATE_LIMIT:
        raise HTTPException(429, "업로드 요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요")
    dq.append(now)


# (2-2) DB 커넥션 풀 — 요청마다 psycopg.connect 를 새로 열지 않고 재사용한다.
# Supabase 는 커넥션 상한이 있으므로, 부하 시 연결 고갈을 막기 위해 풀링이 필수다.
# pool_size 는 gateway 1 레플리카 + 동시 요청 수준에 맞춰 10 으로 둔다(필요시 env 조정).
_pool = ConnectionPool(
    DATABASE_URL,
    min_size=int(os.environ.get("DB_POOL_MIN", "2")),
    max_size=int(os.environ.get("DB_POOL_MAX", "10")),
    kwargs={"row_factory": dict_row},
    open=False,
)


@contextmanager
def db():
    """풀에서 커넥션을 빌려 쓰고 반납한다. 기존 `with db() as conn` 패턴 유지."""
    with _pool.connection() as conn:
        yield conn


DDL = """
CREATE TABLE IF NOT EXISTS jobs (
    id uuid PRIMARY KEY, user_id uuid NOT NULL, kind text NOT NULL, status text NOT NULL DEFAULT 'queued',
    image_key text, inputs jsonb NOT NULL DEFAULT '{}'::jsonb, result jsonb, error text,
    attempts int NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS jobs_status_idx ON jobs (status, created_at);
CREATE INDEX IF NOT EXISTS jobs_user_idx ON jobs (user_id, created_at);
CREATE TABLE IF NOT EXISTS job_events (
    id bigserial PRIMARY KEY, job_id uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    stage text NOT NULL, detail jsonb, at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS job_events_job_idx ON job_events (job_id, at);
CREATE TABLE IF NOT EXISTS prescriptions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id uuid NOT NULL UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    user_id uuid NOT NULL,
    grade text, ratio_pct numeric, score numeric,
    selected_mixes jsonb, pcr_mixes jsonb, per_metric jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS prescriptions_job_idx ON prescriptions (job_id);
CREATE INDEX IF NOT EXISTS prescriptions_user_idx ON prescriptions (user_id);
"""


def record_event(cur, job_id, stage, detail=None):
    cur.execute("INSERT INTO job_events (job_id, stage, detail) VALUES (%s,%s,%s)",
                (str(job_id), stage, json.dumps(detail) if detail is not None else None))


def _ensure_schema():
    import time
    last = None
    for _ in range(30):
        try:
            with db() as conn, conn.cursor() as cur:
                cur.execute(DDL); conn.commit()
            return
        except Exception as e:  # noqa: BLE001
            last = e; time.sleep(2)
    raise RuntimeError(f"DB 초기화 실패: {last}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # (2-2) 풀은 lifespan 에서 열고 닫는다 — 프로세스 생애주기와 일치.
    _pool.open()
    if AUTO_DDL:
        _ensure_schema()
        log.info("auto-DDL 적용(dev)")
    else:
        log.info("auto-DDL 비활성 — 마이그레이션 전제(운영)")
    yield
    _pool.close()


app = FastAPI(title="SkinLens Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-User-Id"],
    max_age=600,
)


def _verify_jwt(authorization):
    """Authorization: Bearer <jwt> 를 검증하고 sub(uuid)를 돌려준다. 실패 시 None/401."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    if not JWT_SECRET:
        # 운영 오설정: strict 인데 검증 비밀키가 없음 — 조용히 통과시키지 않는다.
        raise HTTPException(500, "인증 비밀키 미설정(SUPABASE_JWT_SECRET)")
    try:
        decode_kwargs = {"algorithms": ["HS256"], "audience": JWT_AUD}
        # (2-1) iss 가 설정돼 있으면 발급자도 함께 검증해 토큰 혼용을 막는다.
        if JWT_ISS:
            decode_kwargs["issuer"] = JWT_ISS
        claims = jwt.decode(token.strip(), JWT_SECRET, **decode_kwargs)
    except Exception:  # noqa: BLE001 — 만료/서명불일치/형식오류 모두 401 로 수렴
        raise HTTPException(401, "토큰 검증 실패")
    try:
        return uuid.UUID(str(claims.get("sub")))
    except (ValueError, TypeError):
        raise HTTPException(401, "토큰 subject(uuid) 형식 오류")


def require_user(authorization=None, x_user_id=None):
    """
    신뢰 경계의 유일한 인증 지점.
      strict: 검증된 JWT 만 신뢰한다. 클라이언트가 보낸 X-User-Id 는 무시(위조 방지).
      dev   : X-User-Id(있으면) 또는 고정 폴백 UUID.
    """
    if AUTH_MODE == "strict":
        uid = _verify_jwt(authorization)
        if uid is None:
            raise HTTPException(401, "인증 필요(Bearer 토큰)")
        return uid
    if x_user_id:
        try:
            return uuid.UUID(x_user_id)
        except ValueError:
            raise HTTPException(400, "X-User-Id 형식이 올바르지 않습니다(UUID)")
    return uuid.UUID(DEV_FALLBACK_USER_ID)


def _webp(head): return len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP"


def validate_image(ct, data):
    ext = ALLOWED_TYPES.get((ct or "").split(";")[0].strip().lower())
    if ext is None: raise HTTPException(415, "지원하지 않는 형식(jpeg/png/webp)")
    if len(data) == 0: raise HTTPException(400, "빈 파일")
    if len(data) > MAX_BYTES: raise HTTPException(413, f"용량 초과(최대 {MAX_BYTES//(1024*1024)}MB)")
    head = data[:16]
    ok = _webp(head) if ext == ".webp" else any(head.startswith(s) for s in MAGIC[ext])
    if not ok: raise HTTPException(415, "내용이 선언 형식과 불일치")
    return ext


def _ext_for_content_type(content_type) -> str:
    """presign 요청의 content_type 화이트리스트 검증 → 확장자. gateway 는 바이트를 안 본다(4.7)."""
    ct = (content_type or "").split(";")[0].strip().lower()
    ext = ALLOWED_TYPES.get(ct)
    if ext is None:
        raise HTTPException(415, "지원하지 않는 형식(jpeg/png/webp)")
    return ext


def _normalize_inputs(survey, pcr):
    """survey/pcr JSON(문자열 또는 이미 파싱된 객체)을 inputs dict 로 정규화."""
    inputs: dict = {}
    for field, raw in (("survey", survey), ("pcr", pcr)):
        if raw is None:
            continue
        parsed = raw
        if isinstance(raw, str):
            if not raw.strip():
                continue
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                raise HTTPException(400, f"{field} 는 JSON 이어야 합니다")
        if not isinstance(parsed, dict):
            raise HTTPException(400, f"{field} 는 JSON 객체여야 합니다")
        inputs[field] = parsed
    return inputs


def _iso(row):
    for k, v in list(row.items()):
        if isinstance(v, dt.datetime): row[k] = v.isoformat()
    return row


@app.get("/")
def root(): return {"status": "ok", "service": "gateway", "auth": AUTH_MODE, "storage": storage.name}


@app.get("/health")
def health(): return {"status": "ok"}


@app.get("/health/db")
def health_db():
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1")
    return {"db": "ok"}


@app.post("/uploads/presign")
def presign_upload(payload: dict = Body(default=None),
                   authorization: str | None = Header(default=None, alias="Authorization"),
                   x_user_id: str | None = Header(default=None, alias="X-User-Id")):
    """
    presigned 업로드 URL 발급(Phase 4.1/4.7). 브라우저는 여기서 받은 URL 로 Supabase Storage 에
    직접 PUT 하고, 완료 후 `POST /analyze { image_key }` 로 잡만 생성한다.

    gateway 는 바이트를 보지 않으므로 magic-byte 검증은 성립 불가 — 실질 재검증은 worker(4.6)가 한다.
    여기서는 ① content-type 화이트리스트(약함, 우회 가능) ② 크기 상한 선언 ③ 짧은 만료 ④ 레이트리밋.
    """
    user_id = require_user(authorization, x_user_id)
    _rate_limit_presign(user_id)

    body = payload if isinstance(payload, dict) else {}
    ext = _ext_for_content_type(body.get("content_type"))
    declared_size = body.get("size_bytes")
    if declared_size is not None:
        try:
            declared_size = int(declared_size)
        except (TypeError, ValueError):
            raise HTTPException(400, "size_bytes 는 정수여야 합니다")
        if declared_size <= 0:
            raise HTTPException(400, "size_bytes 가 올바르지 않습니다")
        if declared_size > MAX_BYTES:
            raise HTTPException(413, f"용량 초과(최대 {MAX_BYTES // (1024 * 1024)}MB)")

    from .storage import SupabaseStorage
    if not isinstance(storage, SupabaseStorage):
        # presigned 는 Supabase Storage 전용. local 백엔드(dev)는 구 multipart 를 쓴다.
        raise HTTPException(409, "presigned 업로드는 STORAGE_BACKEND=supabase 에서만 지원")

    job_id = uuid.uuid4()
    image_key = f"{user_id}/{job_id}/original{ext}"
    try:
        signed = storage.create_signed_upload_url(image_key, expires_in=PRESIGN_EXPIRES)
    except Exception:  # noqa: BLE001 — Supabase 장애를 500 으로 표면화(조용한 성공 금지)
        log.exception("presign 발급 실패", extra={"job_id": str(job_id)})
        raise HTTPException(502, "업로드 서명 발급 실패(스토리지)")

    log.info("presign 발급", extra={"job_id": str(job_id)})
    return {
        "job_id": str(job_id),
        "image_key": image_key,
        "expires_in": PRESIGN_EXPIRES,
        "signed": signed,   # {url, path, token} — 브라우저가 그대로 PUT
    }


@app.post("/analyze")
async def analyze(image: UploadFile = File(default=None),
                  survey: str | None = Form(None),
                  pcr: str | None = Form(None),
                  payload: dict = Body(default=None),
                  authorization: str | None = Header(default=None, alias="Authorization"),
                  x_user_id: str | None = Header(default=None, alias="X-User-Id")):
    """
    잡 생성. 두 입력 경로:
      (기본)  presigned — application/json 본문: { image_key, survey?, pcr? } (Phase 4.2).
              브라우저가 이미 Storage 에 PUT 한 image_key 만 받아 잡을 만든다. 바이트는 안 만진다.
      (레거시) multipart/form-data: image 파일 + survey/pcr 필드. ENABLE_LEGACY_UPLOAD=1 일 때만(4.3).
              dev(STORAGE_BACKEND=local)·초기 호환용. 웹 전환 확인 후 플래그를 0 으로 닫는다.
    """
    user_id = require_user(authorization, x_user_id)

    # ---- (기본) presigned 경로: JSON 본문 ----------------------------------
    if isinstance(payload, dict) and payload.get("image_key"):
        image_key = str(payload["image_key"]).strip()
        # 소유권/키 형식 방어: 반드시 이 사용자의 폴터 아래 original.<허용확장자> 형태여야 한다.
        # (버킷 내 임의 키를 가리켜 남의 업로드를 자기 잡으로 등록하는 것 차단)
        parts = image_key.split("/")
        if len(parts) != 3 or parts[0] != str(user_id):
            raise HTTPException(400, "image_key 형식이 올바르지 않습니다")
        ext = os.path.splitext(parts[2])[1].lower()
        if ext not in MAGIC or not parts[2].startswith("original"):
            raise HTTPException(400, "image_key 형식이 올바르지 않습니다")
        inputs = _normalize_inputs(payload.get("survey"), payload.get("pcr"))

        # N1: presign 이 박아둔 job_id(image_key 두 번째 조각)를 잡 id 로 재사용한다.
        # 클라이언트가 job_id 를 명시하면 image_key 와 일치하는지 검증해 키-잡 결합을 강제하고,
        # 생략하면 image_key 에서 추출한다(고아 업로드 추적성 확보).
        key_job_id = parts[1]
        req_job_id = payload.get("job_id")
        if req_job_id is not None:
            req_job_id = str(req_job_id).strip()
            if req_job_id != key_job_id:
                raise HTTPException(400, "job_id 가 image_key 와 일치하지 않습니다")
            try:
                job_id = uuid.UUID(req_job_id)
            except ValueError:
                raise HTTPException(400, "job_id 형식이 올바르지 않습니다")
        else:
            try:
                job_id = uuid.UUID(key_job_id)
            except ValueError:
                job_id = uuid.uuid4()
        with db() as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO jobs (id, user_id, kind, image_key, inputs) VALUES (%s,%s,%s,%s,%s)",
                        (job_id, str(user_id), "analysis", image_key, json.dumps(inputs)))
            record_event(cur, job_id, "uploaded",
                         {"via": "presigned", "ext": ext, "inputs_present": list(inputs.keys())})
            record_event(cur, job_id, "queued", None)
            conn.commit()
        log.info("job 등록(presigned)", extra={"job_id": str(job_id)})
        return JSONResponse(status_code=202, content={"job_id": str(job_id), "status": "queued"})

    # ---- (레거시) multipart 경로 ------------------------------------------
    if not ENABLE_LEGACY_UPLOAD:
        raise HTTPException(410, "multipart 업로드는 폐기됐습니다. presigned 플로우를 사용하세요")
    if image is None:
        raise HTTPException(400, "image 파일 또는 image_key 가 필요합니다")

    job_id = uuid.uuid4()
    data = await image.read()
    ext = validate_image(image.content_type, data)
    image_key = f"{user_id}/{job_id}/original{ext}"
    storage.save(image_key, data)

    inputs = {}
    if image.filename: inputs["original_filename"] = os.path.basename(image.filename)
    inputs.update(_normalize_inputs(survey, pcr))

    with db() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO jobs (id, user_id, kind, image_key, inputs) VALUES (%s,%s,%s,%s,%s)",
                    (job_id, str(user_id), "analysis", image_key, json.dumps(inputs)))
        record_event(cur, job_id, "uploaded",
                     {"via": "multipart", "bytes": len(data), "ext": ext, "inputs_present": list(inputs.keys())})
        record_event(cur, job_id, "queued", None)
        conn.commit()
    log.info("job 등록(multipart)", extra={"job_id": str(job_id)})
    return JSONResponse(status_code=202, content={"job_id": str(job_id), "status": "queued"})


@app.get("/jobs")
def list_jobs(limit: int = 20,
              authorization: str | None = Header(default=None, alias="Authorization"),
              x_user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = require_user(authorization, x_user_id)
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, kind, status, attempts, created_at, updated_at FROM jobs "
                    "WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
                    (str(user_id), min(limit, 100)))
        rows = cur.fetchall()
    return {"jobs": [_iso(r) for r in rows]}


# 컬럼 화이트리스트: 소유자라도 내부 필드는 최소로만 반환.
_JOB_COLS = "id, user_id, kind, status, image_key, inputs, result, error, attempts, created_at, updated_at"


@app.get("/jobs/{job_id}")
def get_job(job_id: uuid.UUID,
            authorization: str | None = Header(default=None, alias="Authorization"),
            x_user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = require_user(authorization, x_user_id)
    with db() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT {_JOB_COLS} FROM jobs WHERE id = %s AND user_id = %s",
                    (str(job_id), str(user_id)))
        row = cur.fetchone()
    if not row: raise HTTPException(404, "job 없음")   # 남의 job 도 404 로 응답(존재 노출 방지)
    return _iso(row)


@app.get("/jobs/{job_id}/events")
def get_job_events(job_id: uuid.UUID,
                   authorization: str | None = Header(default=None, alias="Authorization"),
                   x_user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = require_user(authorization, x_user_id)
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM jobs WHERE id=%s AND user_id=%s", (str(job_id), str(user_id)))
        if not cur.fetchone(): raise HTTPException(404, "job 없음")
        cur.execute("SELECT stage, detail, at FROM job_events WHERE job_id=%s ORDER BY at, id",
                    (str(job_id),))
        rows = cur.fetchall()
    return {"job_id": str(job_id), "events": [_iso(r) for r in rows]}


@app.get("/jobs/{job_id}/report", response_class=HTMLResponse)
def get_report(job_id: uuid.UUID,
               authorization: str | None = Header(default=None, alias="Authorization"),
               x_user_id: str | None = Header(default=None, alias="X-User-Id")):
    """
    리포트 seam — 결과를 최소 HTML 로 렌더. 실제 고객 리포트(Word/Excel/브랜디드 HTML)는
    이 자리를 템플릿 엔진/문서 생성기로 교체. 지금은 방어적으로 모든 동적 값을 이스케이프한다
    (seam 이 설문 notes/파일명 등 사용자 입력을 렌더하게 되어도 저장형 XSS 를 차단).
    """
    user_id = require_user(authorization, x_user_id)
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT status, result FROM jobs WHERE id=%s AND user_id=%s",
                    (str(job_id), str(user_id)))
        row = cur.fetchone()
    if not row: raise HTTPException(404, "job 없음")
    e = html.escape
    if row["status"] != "done" or not row["result"]:
        return HTMLResponse(f"<h3>아직 준비 안 됨: status={e(str(row['status']))}</h3>")
    r = row["result"]; pres = r.get("prescription", {})
    rows_html = "".join(
        f"<tr><td>{e(str(k))}</td><td>{e(str(v.get('grade')))}</td>"
        f"<td>{e(str(v.get('ratio_pct')))}%</td><td>{e(str(v.get('source')))}</td></tr>"
        for k, v in (pres.get("per_metric", {}) or {}).items())
    mixes = ", ".join(e(str(m.get("mix"))) for m in pres.get("selected_mixes", []))
    return HTMLResponse(
        f"<html><head><meta charset='utf-8'><title>SkinLens Report</title></head><body>"
        f"<h2>SkinLens 리포트 (placeholder)</h2>"
        f"<p>종합: <b>{e(str(pres.get('grade')))}</b> · 비율 {e(str(pres.get('prescription_ratio_pct')))}%</p>"
        f"<table border=1 cellpadding=4><tr><th>지표</th><th>등급</th><th>비율</th><th>출처</th></tr>{rows_html}</table>"
        f"<p>선택 믹스: {mixes}</p></body></html>")


@app.get("/debug/engines")
def debug_engines():
    if not DEV_DEBUG: raise HTTPException(404, "not found")
    out = {}
    for name, base in (("engine-analysis", ENGINE_ANALYSIS_URL), ("engine-prescription", ENGINE_PRESCRIPTION_URL)):
        try:
            with httpx.Client(timeout=5) as c:
                rr = c.get(f"{base}/health")
                out[name] = {"reachable": True, "status_code": rr.status_code, "body": rr.json()}
        except Exception as e:  # noqa: BLE001
            out[name] = {"reachable": False, "error": str(e)}
    return out
