# SkinLens ?„ë¡œ?íŠ¸ ì¢…í•© ë¶„ì„ ë³´ê³ ??

> **ë¶„ì„ ?¼ì**: 2026-08-19  
> **ë¶„ì„ ?€??*: SkinLens Monorepo (c:/Project/SkinServer)  
> **ë¶„ì„ ë²”ìœ„**: ?„ë¡œ?íŠ¸ êµ¬ì¡°, Frontend, Backend, Python/FastAPI, Supabase, Docker, ?˜ê²½ë³€?? ë°°í¬, ?´ì˜, ê¸°í?

---

## 1. ?„ë¡œ?íŠ¸ ?”ë ‰?°ë¦¬ êµ¬ì¡° ë¶„ì„

SkinLens??**AI ?¼ë?ë¶„ì„Â·ì²˜ë°© ?Œë«??*?¼ë¡œ, ì½”ë“œÂ·?¸í”„?¼Â·ë¬¸?œë? ?¨ì¼ ?€?¥ì†Œ?ì„œ ê´€ë¦¬í•˜??**Monorepo** êµ¬ì¡°?…ë‹ˆ?? ?„ì¬ **3-Tier(Vercel Â· Supabase Â· AI Server)** ?„í‚¤?ì²˜ë¡??¬í¸ ì¤‘ì…?ˆë‹¤.

### ?”ë ‰?°ë¦¬ êµ¬ì¡°

```
skinlens/
?œâ??€ apps/                    # ?„ë¡ ?¸ì—”???œë©´
??  ?œâ??€ webapp-next/         â­??„í–‰: Next.js PWA (Vercel ë°°í¬ ?€??
??  ?œâ??€ webapp/              ?ˆê±°?? Vite SPA (?œê±° ?ˆì •)
??  ?œâ??€ homepage/            ?•ì  ?Œë ˆ?´ìŠ¤?€??(?´ê?/?œê±° ?ˆì •)
??  ?”â??€ devpage/             ?•ì  ?Œë ˆ?´ìŠ¤?€??(?ê¸° ?ˆì •)
?œâ??€ services/                # AI Server ë°±ì—”??
??  ?œâ??€ gateway/             FastAPI ê²Œì´?¸ì›¨??(?¨ì¼ ?°ê¸° ì£¼ì²´)
??  ?œâ??€ worker/              ë¹„ë™ê¸????Œì»¤ (???Œë¹„)
??  ?œâ??€ engine-analysis/     OpenCV ?¼ë?ë¶„ì„ ?”ì§„ (?ì‡„ë§?
??  ?”â??€ engine-prescription/ ê·œì¹™ ê¸°ë°˜ ì²˜ë°© ?”ì§„ (?ì‡„ë§?
?œâ??€ packages/                # ê³µìš© ì½”ë“œ
??  ?”â??€ common/skinlens_contract/  # ?”ì§„ ê³„ì•½ ?¤í‚¤ë§?(source of truth)
?œâ??€ deploy/                  # ?¸í”„??ì½”ë“œ
??  ?œâ??€ compose/             Docker Compose (base + ?˜ê²½ ?¤ë²„?ˆì´)
??  ?œâ??€ env/                 ?˜ê²½ë³€???ˆì‹œ (.env, .env.images)
??  ?œâ??€ caddy/               Caddy TLS ?¤ì •
??  ?œâ??€ scripts/             ë°°í¬Â·ê¸°ë™Â·ë°±ì—…Â·ê²€ì¦??¤í¬ë¦½íŠ¸
??  ?œâ??€ supabase/            RLS + Storage ?•ì±… SQL
??  ?œâ??€ db/                  ë§ˆì´ê·¸ë ˆ?´ì…˜ SQL
??  ?œâ??€ nginx/               ? ï¸ ?ˆê±°??(?œê±° ?ˆì •)
??  ?”â??€ ops-jobs/            ë³´ì¡´Â·ë¡œê·¸ ?¤í¬?¬ë¹™Â·ê´€ì¸¡Â·ë³µêµ?ë¦¬í—ˆ??
?œâ??€ .github/workflows/       CI/CD (AI Server ?„ìš©)
?œâ??€ tests/                   # ?µí•©/?¤ëª¨???ŒìŠ¤??(pytest)
?œâ??€ docs/                    # ëª¨ë“  ?¤ê³„Â·?´ì˜ ë¬¸ì„œ
?”â??€ site/                    # ë¬¸ì„œ ?¬í„¸
```

---

## 2. Frontend ë¶„ì„

### 2.1 apps/webapp-next (?„í–‰ ??Next.js PWA)

**ê¸°ìˆ  ?¤íƒ**: Next.js 14 (App Router) + React 18 + TypeScript + next-pwa + Supabase JS v2

**?µì‹¬ ?¹ì§•**:
- **PWA**: `next-pwa` ?¬ìš©, ???¸ë§Œ precache, `/api`Â·`*.supabase.co`??**NetworkOnly** (PIPA ì¤€??
- **Supabase ì§€??ì´ˆê¸°??*: [`getSupabase()`](apps/webapp-next/src/lib/supabase.ts:11)ê°€ ë¸Œë¼?°ì? ì²??¬ìš© ?œì ???±ê????ì„± (App Router prerender ?€??
- **Presigned ?…ë¡œ??*: ë¸Œë¼?°ì?ê°€ Supabase Storage??ì§ì ‘ PUT ??gateway??`image_key`ë§??˜ì‹ 
- **?¸ì¦**: Supabase JWT Bearer ? í°, ? í° ë¶€????[`AuthRequiredError`](apps/webapp-next/src/lib/api.ts:28) ì¦‰ì‹œ throw

**API ?Œë¡œ??* ([`api.ts`](apps/webapp-next/src/lib/api.ts:56)):
1. `POST /uploads/presign` ??`image_key` + ?œëª… URL ë°œê¸‰
2. Supabase Storage??ì§ì ‘ PUT (?œë²„ ë°”ì´?¨ìŠ¤)
3. `POST /analyze { image_key, survey }` ??`job_id` ë°˜í™˜

### 2.2 apps/webapp (?ˆê±°????Vite SPA)

- React 18 + TypeScript + Vite
- ?´ì „ ?„ë£Œ ???œê±° ?ˆì •

---

## 3. Backend ë¶„ì„

### 3.1 Gateway (FastAPI) ???¨ì¼ ?°ê¸° ì£¼ì²´

**?µì‹¬ ??• **: ?¸ì¦ ê²½ê³„ + ?…ë¡œ??ê²€ì¦?+ Job ?±ë¡ + ?íƒœ ì¡°íšŒ

**ì£¼ìš” ê¸°ëŠ¥**:
- **?¸ì¦**: `AUTH_MODE=strict` (prod) / `dev` (ë¡œì»¬)
  - Supabase JWT(HS256) ê²€ì¦? `aud` + `iss` ê³ ì •
  - prod?ì„œ `AUTH_MODE!=strict` ??**ê¸°ë™ ê±°ë?** (fail-fast)
- **Presigned ?…ë¡œ??*: 
  - content-type/size ê²€ì¦???`image_key` ë°œê¸‰
  - ?ˆì´?¸ë¦¬ë°? ?¬ìš©?ë‹¹ ë¶„ë‹¹ 10??
  - ?œëª… URL ë§Œë£Œ: 15ë¶?
- **DB**: `psycopg-pool` ì»¤ë„¥???€ (min 2 / max 10)
- **Auto-DDL**: `AUTO_DDL=1` (dev ?„ìš©), prod??ë§ˆì´ê·¸ë ˆ?´ì…˜ ?Œì¼ ?¬ìš©

**?”ë“œ?¬ì¸??*:
- `GET /health` ???ì¡´ ì²´í¬
- `POST /uploads/presign` ???œëª… ?…ë¡œ??URL ë°œê¸‰
- `POST /analyze` ?????ì„± (presigned ?ëŠ” ?ˆê±°??multipart)
- `GET /jobs/{id}` ?????íƒœ/ê²°ê³¼ ì¡°íšŒ
- `GET /jobs/{id}/events` ???¨ê³„ë³??€?„ë¼??

### 3.2 Worker ??ë¹„ë™ê¸???ì²˜ë¦¬

**?µì‹¬ ??• **: ???Œë¹„ + ?”ì§„ ?¸ì¶œ + ê²°ê³¼ ê¸°ë¡

**?ˆì •??ê¸°ëŠ¥**:
- **??*: Postgres `FOR UPDATE SKIP LOCKED` (Redis ë¶ˆí•„??
- **?¬ì‹œ??*: ?”ì§„ ?¸ì¶œ ìµœë? 3?? ì§€??ë°±ì˜¤??
- **ë¦¬í¼**: `STALE_SECONDS=120` ì´ˆê³¼ ??ë©ˆì¶˜ ???Œìˆ˜
- **?°ë“œ?ˆí„°**: `MAX_ATTEMPTS=3` ì´ˆê³¼ ??`error` ?íƒœ
- **?ì??*: `finish_ok()`?ì„œ `prescriptions` INSERT + `jobs` UPDATEë¥?**?¨ì¼ ?¸ëœ??…˜**?¼ë¡œ ì²˜ë¦¬
- **?„ì‹œ?Œì¼ ?•ë¦¬**: `finally` ë¸”ë¡?ì„œ `is_temp` ?Œë˜ê·¸ë¡œ êµ¬ë¶„?˜ì—¬ ?•ë¦¬

**ì²˜ë¦¬ ?Œë¡œ??*:
1. `claim_one()` ??`queued` ???ì???´ë ˆ??
2. `validate_image_bytes()` ??magic-byte ?¬ê?ì¦?(presigned ê²½ë¡œ ?„ìˆ˜)
3. `engine-analysis /score` ?¸ì¶œ ??10ì§€??+ ì¢…í•©?ìˆ˜
4. `engine-prescription /prescribe` ?¸ì¶œ ???±ê¸‰ + ë¯¹ìŠ¤ ? íƒ
5. `finish_ok()` ??`prescriptions` INSERT + `jobs` UPDATE (?¸ëœ??…˜)

---

## 4. Python/FastAPI ë¶„ì„

### 4.1 engine-analysis (ë¶„ì„ ?”ì§„)

- **?ì‡„ë§?*: `enginenet` ?„ìš©, ?¸ë? egress ì°¨ë‹¨, ?ê²©ì¦ëª… ?†ìŒ
- **ê¸°ìˆ **: OpenCV + NumPy
- **baseline**: Haar cascade ROI ?¬ë¡­ + 10ì§€???¤ì¸¡ (ì§€??ê±´ì„±/ë³µí•©??ë¯¼ê°???¸ëŸ¬ë¸??‰ì†ŒÂ·??ëª¨ê³µ/?¼ë?ê²?ì£¼ë¦„Â·?„ë ¥/ë¶‰ì?ê¸?
- **ML seam**: `model.py`??`MLScorer` ê°€ì¤‘ì¹˜ TODO (?¥í›„ `ENGINE_MODEL=ml` ?„í™˜)
- **ê³„ì•½ ê²€ì¦?*: `AnalysisOut` Pydantic ?¤í‚¤ë§ˆë¡œ ì¶œë ¥ ê²€ì¦?

### 4.2 engine-prescription (ì²˜ë°© ?”ì§„)

- **?ì‡„ë§?*: `enginenet` ?„ìš©
- **?…ë ¥**: ë¶„ì„ ê²°ê³¼ + ?¤ë¬¸ + PCR ì¤???
- **ê·œì¹™**: ?ìˆ˜?’ë“±ê¸‰â†’ë¹„ìœ¨ ?•ì • (76~100 ?‘í˜¸ 0% / 60~76 ê²½ë? 0.5% / 40~60 ë³´í†µ 1.0% / <40 ?„í—˜/?¬ê° 3.0%)
- **ë¯¹ìŠ¤ ? íƒ**: `config/mixes.json` ì£¼ì… (prod??example config ?¬ìš© ??**fail-fast**)
- **?¤ë¬¸ ?´ì„**: ë¯¼ê°??ë³µí•©????CVë¡??´ë ¤??ì§€???°ì¶œ

### 4.3 ê³µìš© ê³„ì•½ (skinlens_contract)

- **10ì§€??*: `oiliness`, `dryness`, `combination`, `sensitivity`, `trouble`, `pigmentation_tone`, `pores`, `texture`, `wrinkle_elasticity`, `redness`
- **?±ê¸‰??*: `GRADE_TABLE` (?ìˆ˜?’ë“±ê¸‰â†’ì²˜ë°©ë¹„ìœ¨)
- **?¤í‚¤ë§?*: `AnalysisResult`, `PrescribeRequest`, `PrescribeResult`, `Survey`
- **ë²„ì „**: `ENGINE_CONTRACT_VERSION = "1.0.0"`

---

## 5. Supabase ?°ê²° ë¶„ì„

### 5.1 ?°ì´?°ë² ?´ìŠ¤

- **???˜ê²½ Supabase**: ë¡œì»¬ postgres ?†ìŒ
  - dev/staging: `skinlens-dev`
  - prod: `skinlens-prod`
- **?¤í‚¤ë§?*: `jobs`, `job_events`, `prescriptions` ?Œì´ë¸?
- **ë§ˆì´ê·¸ë ˆ?´ì…˜**: `deploy/db/migrations/0001_init.sql` (?´ì˜), gateway auto-DDL (dev ?„ìš©)

### 5.2 ?¸ì¦ (Auth)

- **ë¸Œë¼?°ì?**: anon key + RLSë¡?ì§ì ‘ ?‘ê·¼
- **?œë²„**: service_role ?¤ë¡œ RLS ?°íšŒ (gateway/workerë§?
- **JWT ê²€ì¦?*: HS256, `aud=authenticated`, `iss={SUPABASE_URL}/auth/v1`

### 5.3 ?¤í† ë¦¬ì? (Storage)

- **ë²„í‚·**: `skin-images` (ë¹„ê³µê°?
- **?Œì¼ ?¬ê¸° ?œí•œ**: 25MB (ë²„í‚· ?ˆë²¨ ê°•ì œ)
- **?ˆìš© MIME**: `image/jpeg`, `image/png`, `image/webp`
- **ê²½ë¡œ ê·œì•½**: `{user_id}/{job_id}/original.{ext}`

### 5.4 RLS (Row Level Security)

- **ëª¨ë“  ?¬ìš©???Œì´ë¸?*: `enable row level security` + `force row level security`
- **?•ì±…**: `user_id = auth.uid()` (ë³¸ì¸ ?‰ë§Œ ì¡°íšŒ/?½ì…/?˜ì •/?? œ)
- **job_events**: ?ìœ„ `jobs` ?Œìœ ê¶Œìœ¼ë¡?`EXISTS` ë°”ì¸??
- **Storage**: `(storage.foldername(name))[1] = auth.uid()::text` (?´ë” ì²?ì¡°ê° = ?Œìœ ??

---

## 6. Docker êµ¬ì„± ë¶„ì„

### 6.1 ?¤íŠ¸?Œí¬ êµ¬ì¡°

```
appnet (?¸ë? ?µì‹  ê°€??
  ?”â??€ gateway, worker

enginenet (internal: true ???¸ë? egress ì°¨ë‹¨)
  ?”â??€ engine-analysis, engine-prescription
```

### 6.2 ?œë¹„?¤ë³„ êµ¬ì„±

| ?œë¹„??| ?´ë?ì§€ | ë©”ëª¨ë¦?| CPU | ?¹ì§• |
|--------|--------|--------|-----|------|
| gateway | `sl_gateway:latest` | 1g | 1.5 | CORS, presigned ?…ë¡œ??|
| worker | `sl_worker:latest` | 1g | 1.5 | ???Œë¹„, ?”ì§„ ?¸ì¶œ |
| engine-analysis | `ghcr.io/.../engine-analysis` | 2g | 2.0 | GPU ?€ë¹? OpenCV |
| engine-prescription | `ghcr.io/.../engine-prescription` | 2g | 1.5 | ê·œì¹™ ê¸°ë°˜ |

### 6.3 ?˜ë“œ??(ê³µí†µ)

- `security_opt: ["no-new-privileges:true"]`
- `cap_drop: ["ALL"]`
- `read_only: true`
- `tmpfs: ["/tmp"]`
- `restart: unless-stopped`
- ë¡œê¹…: `json-file` (max 10m, 3ê°?ë¡œí…Œ?´ì…˜)

### 6.4 ?˜ê²½ ?¤ë²„?ˆì´

- **dev**: `build:` ?ŒìŠ¤ ë¹Œë“œ, `DEV_DEBUG=1`, `AUTH_MODE=dev`
- **staging**: `.env.images` ?œê·¸, `pull_policy: always`
- **prod**: `.env.images` ?œê·¸, `ENV=prod`, `AUTH_MODE=strict`, `pull_policy: always`
- **gpu**: GPU ?ˆì•½ + ì§ë ¬??
- **tls**: Caddy ?ë™ TLS + HSTS

---

## 7. ?˜ê²½ë³€??êµ¬ì¡° ë¶„ì„

### 7.1 ?µì‹¬ ?˜ê²½ë³€??

| ë³€??| ?¤ëª… | ?„ìˆ˜ |
|------|------|------|
| `DATABASE_URL` | Supabase Postgres ?°ê²° ë¬¸ì??| ??|
| `SUPABASE_URL` | Supabase ?„ë¡œ?íŠ¸ URL | ??|
| `SUPABASE_SERVICE_KEY` | service_role ??| ??|
| `SUPABASE_JWT_SECRET` | JWT ?œëª… ê²€ì¦???| prod ?„ìˆ˜ |
| `STORAGE_BACKEND` | `local` \| `supabase` | ê¸°ë³¸ supabase |
| `STORAGE_BUCKET` | ?¤í† ë¦¬ì? ë²„í‚·ëª?| ê¸°ë³¸ `skin-images` |
| `AUTH_MODE` | `dev` \| `strict` | prod??strict ?„ìˆ˜ |
| `ENV` | `dev` \| `staging` \| `prod` | - |
| `CORS_ORIGINS` | ?ˆìš© ?¤ë¦¬ì§?(?¼í‘œ êµ¬ë¶„) | - |
| `ENABLE_LEGACY_UPLOAD` | êµ?multipart ?¸í™˜ | ê¸°ë³¸ 1 (?œê±° ?ˆì •) |
| `PRESIGN_EXPIRES_SEC` | ?œëª… URL ë§Œë£Œ | ê¸°ë³¸ 900 (15ë¶? |
| `MAX_UPLOAD_BYTES` | ?…ë¡œ???¬ê¸° ?í•œ | ê¸°ë³¸ 25MB |

### 7.2 ?˜ê²½ ?Œì¼

- `deploy/env/.env` ???œë²„ë³?ë¹„ë?Â·?¤ì • (gitignore)
- `deploy/env/.env.images` ???´ë?ì§€ ?œê·¸ (gitignore)
- `deploy/env/.env.example` ???ˆì‹œ
- `deploy/env/.env.dev.example` ??dev ?ˆì‹œ
- `deploy/env/.env.prod.example` ??prod ?ˆì‹œ

---

## 8. ë°°í¬ êµ¬ì¡° ë¶„ì„

### 8.1 CI/CD ?Œì´?„ë¼??

**??(apps/webapp-next)**:
- `main` push ??Vercel ?ë™ ë¹Œë“œ/ë°°í¬
- ??ë¦¬í¬ì§€? ë¦¬?ì„œ ?¹ì„ ë¹Œë“œ/ë°°í¬?˜ì? ?ŠìŒ

**AI Server (services/)**:
- `.github/workflows/deploy-built-service.yml` ??gateway/worker (?œë²„?ì„œ ë¹Œë“œ)
- `.github/workflows/build-and-deploy-engine.yml` ??engine-* (CI ë¹Œë“œ ??GHCR push ???œë²„ pull)
- `paths` ?„í„°ë¡?ë³€ê²??œë¹„?¤ë§Œ ë¹Œë“œ

### 8.2 ë°°í¬ ?¤í¬ë¦½íŠ¸ (deploy.sh)

**ê¸°ëŠ¥**:
1. `.env.images` ?œê·¸ ?ì??êµì²´ (flock ì§ë ¬??
2. (?„ìš”??GHCR pull)
3. `up -d` ???¬ìŠ¤ì²´í¬ ?€ê¸?(ìµœë? 120ì´?
4. ?¤íŒ¨ ??**?ë™ ë¡¤ë°±** (?´ì „ ?œê·¸ë¡?ë³µì›)

**?¬ìš©**:
```bash
./deploy.sh --service gateway --image sl_gateway:abc123 --env staging
./deploy.sh --service engine-analysis --image ghcr.io/...:abc123 --env production --pull
```

### 8.3 ?µí•© ê¸°ë™ CLI (sl)

**?™ì‚¬**: `up` / `down` / `logs` / `ps` / `doctor` / `init` / `deploy`

```bash
deploy/scripts/sl init dev    # ìµœì´ˆ ?¤ì •
deploy/scripts/sl up dev      # ê¸°ë™
deploy/scripts/sl doctor dev  # ?ê?ì§„ë‹¨
deploy/scripts/sl deploy gateway sl_gateway:abc123 --env staging
```

---

## 9. ?´ì˜ êµ¬ì¡° ë¶„ì„

### 9.1 ëª¨ë‹ˆ?°ë§Â·?œì–´

- **?ê²© ëª¨ë‹ˆ?°ë§**: `deploy/scripts/remote.ps1` / `remote.cmd` (Windows ??Linux SSH)
- **?œë²„ ?íƒœ**: `deploy/ops/remote-status.sh` (ì»¨í…Œ?´ë„ˆÂ·?¬ìŠ¤Â·?”ìŠ¤??·ë©”ëª¨ë¦¬Â·?Â·GPU ?˜ì§‘)
- **ë¡œê¹…**: êµ¬ì¡°??JSON ë¡œê¹… (job_id ?ê?ID)
- **?Œë¦¼**: `deploy/ops-jobs/observability/alert.sh` (?„ê³„ webhook)

### 9.2 ë°±ì—…Â·ë³µêµ¬

- **DB ë°±ì—…**: `deploy/scripts/pg_backup.sh` (?¼ë¦¬ ë°±ì—…, AES-256 ?”í˜¸?? ?¤í”„?¬ì´??
- **ë³µêµ¬ ë¦¬í—ˆ??*: `deploy/ops-jobs/restore-rehearsal.sh` (RPO/RTO ì¸¡ì •)
- **ë³´ì¡´ ?•ì±…**: `deploy/ops-jobs/retention.py` (?„ë£Œ ?ë³¸ ?? œ, ë¯¸ì™„ë£??•ë¦¬)

### 9.3 ë¡œê·¸ ê´€ë¦?

- **ë¡œê·¸ ?¤í¬?¬ë¹™**: `deploy/ops-jobs/log-scrub.py` (? í°/URL/PII ë§ˆìŠ¤??
- **?‘ê·¼ ë¡œê·¸**: `nginx-log-privacy.conf` (ì¿¼ë¦¬?¤íŠ¸ë§Â·ì¸ì¦??œì™¸)

---

## 10. ê¸°í?

### 10.1 ?ŒìŠ¤??

- **?¨ìœ„** (203ê°??µê³¼): `tests/gateway/`, `tests/engine_analysis/`, `tests/engine_prescription/`, `tests/worker/`
  - ì»¤ë²„ë¦¬ì? ê°?ë¶„ì„: [`docs/TEST_COVERAGE_GAP_ANALYSIS.md`](./TEST_COVERAGE_GAP_ANALYSIS.md) ??P0(6ê±?+P1(6ê±?+P2(5ê±? ?„ë? ?´ê²°(?ŒìŠ¤??ì»¤ë²„ë¦¬ì? ê°?ê¸°ì? ??ì½”ë“œë¦¬ë·° ë°±ë¡œê·¸ì˜ P1-3(presigned E2EÂ·RLS)?€??ë³„ê°œ ?¸íŠ¸?´ë©° ê·?ê±´ì? ë¯¸í•´ê²?
- **?µí•©**: `tests/integration/` (?”ë“œ?¬ì—”???Œì´?„ë¼?? ?Œìœ ê¶?ê²€ì¦?
- **ê³„ì•½**: `tests/common/test_contract.py` (?¤í‚¤ë§?ë¶ˆë???ê²€ì¦?
- **?¤í–‰**: `make test` (?¨ìœ„), `make itest` (?µí•©), `make smoke` (?”ë“œ?¬ì—”???¤ëª¨??

### 10.2 ë¬¸ì„œ

- **?¤ê³„**: `docs/architecture/` (3-Tier ?¤ê³„ ?•ë³¸, ?´ì „ ?‘ì—…ê³„íš)
- **?´ì˜**: `docs/operations/` (ì²´í¬ë¦¬ìŠ¤?? ?°ë¶, ?¸ëŸ¬ë¸”ìŠˆ??
- **ë¡œë“œë§?*: `docs/roadmap/` (Phase ë¡œë“œë§? ?°ì„ ?œìœ„)
- **ë¦¬ë·°**: `docs/review/` (ì½”ë“œ ë¦¬ë·° 1ì°?2ì°?
- **?´ì•¼ê¸?*: `docs/stories/` (ê°œë… ?”ì•½ ?´ì•¼ê¸°ì²´)

### 10.3 ?„ì¬ ?íƒœ (2026-08-19 ê¸°ì?)

**???„ë£Œ**:
- 3-Tier ì½”ë“œ ?´ì „ (Phase 1~4)
- PIPA ìºì‹œ ?•ì±… (SW NetworkOnly)
- CI ?„ìƒ (requirements-dev ?€, psycopg-pool ì¶”ê?)
- presigned ?¬ì¸µ ë°©ì–´ ì²´ì¸
- ?¨ìœ„ ?ŒìŠ¤??ì»¤ë²„ë¦¬ì? ë³´ì™„ (?ŒìŠ¤??ì»¤ë²„ë¦¬ì? P0/P1/P2 17ê±??„ë?, 203ê°??µê³¼ ??ì½”ë“œë¦¬ë·° P1-3?€ ë³„ê±´Â·ë¯¸í•´ê²?

**?Ÿ¡ ì§„í–‰ ì¤?*:
- 3-Tier ?¤ë°°??·E2EÂ·?œê±° (Vercel ?°ê²°, êµ¬ì•± ?œê±°, nginx ?œê±°)
- docs ??ê²½ë¡œ ë§í¬ ì¹˜í™˜

**?”´ ë¯¸í•´ê²?*:
- ?¤ì œ ë°°í•©??`config/mixes.json` (prod ë¸”ë¡œì»?
- GAN/ML ëª¨ë¸ ?™ìŠµ ??`ENGINE_MODEL=ml` ?„í™˜

---

## ì¢…í•© ?‰ê?

SkinLens??**?¤ê³„Â·ë³´ì•ˆÂ·?ˆì •?±Â·ë¬¸?œí™”** ëª¨ë“  ë©´ì—??**ë§¤ìš° ?’ì? ?˜ì?**???„ë¡œ?íŠ¸?…ë‹ˆ??

**ê°•ì **:
1. **3-Tier ?„í‚¤?ì²˜**: Vercel(?? + Supabase(?°ì´?? + AI Server(?”ì§„) ëª…í™•??ë¶„ë¦¬
2. **?¬ì¸µ ë°©ì–´**: presigned ?…ë¡œ??(gateway ??ë²„í‚· ??worker ??magic-byte)
3. **fail-fast**: prod?ì„œ ?¸ì¦Â·?¤í† ë¦¬ì?Â·config ?¤ì„¤????ê¸°ë™ ê±°ë?
4. **?ì??*: ???´ë ˆ??SKIP LOCKED), ì²˜ë°© ê¸°ë¡(?¨ì¼ ?¸ëœ??…˜)
5. **ë¬¸ì„œ??*: ?¤ê³„ ?•ë³¸Â·?°ë¶Â·ë¡œë“œë§µÂ·ë¦¬ë·°ê? ì½”ë“œ?€ ?•í•©

**ì£¼ì˜?¬í•­**:
1. **prod ë°°í¬ ???„ìˆ˜**: `config/mixes.json` ?¤ì œ ë°°í•©??ì¤€ë¹?
2. **?ˆê±°???•ë¦¬**: nginxÂ·webappÂ·homepageÂ·devpage ?œê±° ?ˆì •

???„ë¡œ?íŠ¸??**?¸ì£¼ ê°œë°œ ?¸ë„**ë¥??„í•œ SRSÂ·HANDOFF ë¬¸ì„œ???„ë¹„?˜ì–´ ?ˆì–´, **ê¸°ìˆ  ?´ê? ë°??´ì˜ ?¸ìˆ˜?¸ê³„**ê°€ ?©ì´??êµ¬ì¡°?…ë‹ˆ??

---

*ë³?ë³´ê³ ?œëŠ” 2026-08-19 ê¸°ì??¼ë¡œ ?‘ì„±?˜ì—ˆ?µë‹ˆ??*
