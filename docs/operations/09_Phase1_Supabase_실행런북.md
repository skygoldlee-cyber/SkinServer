# Phase 1.1–1.3 실행 런북 — Supabase 프로젝트 생성·스키마·RLS 적용

> 목적: Supabase 콘솔에서 `skinlens-dev` / `skinlens-prod` 프로젝트를 생성하고,
> 스키마 마이그레이션과 RLS/Storage 정책을 적용한 뒤, 각 서버의 `.env`에 연결 정보를 채운다.
> 이 런북은 **외부 작업(Supabase 콘솔)** 이며, 리포지토리 코드 변경은 포함하지 않는다.
>
> 상위 계획: [`05_3Tier_이전_작업계획.md`](../architecture/05_3Tier_이전_작업계획.md) Phase 1.1–1.3

---

## 0. 사전 준비

| 항목 | 확인 |
|------|------|
| Supabase 계정 | 조직(Organization) 생성 여부. 없으면 `https://supabase.com/dashboard` 에서 생성 |
| 리전 선택 | `ap-northeast-2`(서울) 권장. AI Server(국내)와 지연 최소화 |
| 비밀번호 관리 | DB 비밀번호·service_role key는 **비밀 관리자(1Password 등)** 에 즉시 기록 |

> **중요**: `skinlens-dev` 와 `skinlens-prod` 는 **스키마는 동일, 데이터는 완전 분리** 한다.
> dev/staging 은 `skinlens-dev` 를 공유하고, prod 만 `skinlens-prod` 를 사용한다.

---

## 1. Phase 1.1 — Supabase 프로젝트 생성

### 1.1.1 `skinlens-dev` 생성

1. Supabase Dashboard → **New project** 클릭.
2. 아래 값 입력:

   | 필드 | 값 |
   |------|-----|
   | Name | `skinlens-dev` |
   | Database Password | **강력한 비밀번호 생성** (예: `openssl rand -base64 32`) → 비밀 관리자에 저장 |
   | Region | `Northeast Asia (Seoul)` |
   | Pricing Plan | `Free` (개발용) |

3. **Create new project** 클릭 → 프로비저닝 완료 대기(약 2분).

### 1.1.2 `skinlens-prod` 생성

1. 동일 절차로 **New project** 생성.
2. 아래 값 입력:

   | 필드 | 값 |
   |------|-----|
   | Name | `skinlens-prod` |
   | Database Password | **dev와 다른 강력한 비밀번호** 생성 → 비밀 관리자에 저장 |
   | Region | `Northeast Asia (Seoul)` |
   | Pricing Plan | `Pro` (운영용, RLS·백업·관측 필요) |

3. 프로비저닝 완료 대기.

### 1.1.3 프로젝트 참조(ref) 확인

각 프로젝트의 **Settings → General → Reference ID** 에서 `project-ref` 를 확인한다.
예: `abcdefgh` → 연결 문자열은 `db.abcdefgh.supabase.co` 형태가 된다.

| 프로젝트 | project-ref | DATABASE_URL 호스트 |
|----------|-------------|---------------------|
| skinlens-dev | `<dev-ref>` | `db.<dev-ref>.supabase.co` |
| skinlens-prod | `<prod-ref>` | `db.<prod-ref>.supabase.co` |

---

## 2. Phase 1.2 — DB 스키마 마이그레이션 적용

> 대상 파일: [`deploy/db/migrations/0001_init.sql`](../../deploy/db/migrations/0001_init.sql)
> 적용 방법: **SQL Editor(권장)** 또는 `psql $DATABASE_URL`

### 2.1 SQL Editor로 적용 (권장)

1. Supabase Dashboard → **SQL Editor** → **New query** 클릭.
2. 아래 SQL을 붙여넣고 **Run** 클릭:

```sql
-- deploy/db/migrations/0001_init.sql 과 동일 내용
CREATE TABLE IF NOT EXISTS jobs (
    id uuid PRIMARY KEY, user_id uuid NOT NULL, kind text NOT NULL, status text NOT NULL DEFAULT 'queued',
    image_key text, inputs jsonb NOT NULL DEFAULT '{}'::jsonb, result jsonb, error text,
    attempts int NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS jobs_status_idx ON jobs (status, created_at);
CREATE INDEX IF NOT EXISTS jobs_user_idx   ON jobs (user_id, created_at);

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
CREATE INDEX IF NOT EXISTS prescriptions_job_idx  ON prescriptions (job_id);
CREATE INDEX IF NOT EXISTS prescriptions_user_idx ON prescriptions (user_id);
```

3. **Success** 확인 후, 아래 검증 쿼리로 테이블 생성 확인:

```sql
select tablename from pg_tables where schemaname = 'public' order by tablename;
-- 예상 결과: job_events, jobs, prescriptions (+ Supabase 기본 테이블들)
```

### 2.2 psql로 적용 (대안)

로컬에 `psql` 클라이언트가 있으면:

```bash
# skinlens-dev
export DATABASE_URL="postgresql://postgres:<dev-db-password>@db.<dev-ref>.supabase.co:5432/postgres?sslmode=require"
psql "$DATABASE_URL" -f deploy/db/migrations/0001_init.sql

# skinlens-prod
export DATABASE_URL="postgresql://postgres:<prod-db-password>@db.<prod-ref>.supabase.co:5432/postgres?sslmode=require"
psql "$DATABASE_URL" -f deploy/db/migrations/0001_init.sql
```

### 2.3 두 프로젝트 모두 적용

- [ ] `skinlens-dev` 에 `0001_init.sql` 적용 완료
- [ ] `skinlens-prod` 에 `0001_init.sql` 적용 완료

---

## 3. Phase 1.3 — RLS/Storage 정책 적용

> 대상 파일: [`deploy/supabase/policies/0001_rls_and_storage.sql`](../../deploy/supabase/policies/0001_rls_and_storage.sql)
> 이 파일은 **idempotent** 하므로 재실행필요 시 다시 실행핏도 안전하다.

### 3.1 SQL Editor로 적용

1. Supabase Dashboard → **SQL Editor** → **New query** 클릭.
2. [`deploy/supabase/policies/0001_rls_and_storage.sql`](../../deploy/supabase/policies/0001_rls_and_storage.sql) 전체 내용을 붙여넣고 **Run** 클릭.

### 3.2 정책 적용 확인

아래 쿼리로 RLS·정책이 올바르게 생성되었는지 확인한다.

```sql
-- 1) 테이블 RLS 활성화 확인
select relname, relrowsecurity, relforcerowsecurity
from pg_class
where relname in ('jobs','job_events','prescriptions')
order by relname;
-- 예상: 모두 relrowsecurity=true, relforcerowsecurity=true

-- 2) 정책 목록 확인
select schemaname, tablename, policyname, permissive, roles, cmd
from pg_policies
where schemaname = 'public'
order by tablename, policyname;
-- 예상: jobs_del_own, jobs_ins_own, jobs_sel_own, jobs_upd_own,
--        job_events_sel_own,
--        prescriptions_del_own, prescriptions_ins_own, prescriptions_sel_own, prescriptions_upd_own

-- 3) Storage 버킷 확인
select id, name, public from storage.buckets where id = 'skin-images';
-- 예상: public=false

-- 4) Storage 정책 확인
select policyname from pg_policies where schemaname = 'storage' and tablename = 'objects';
-- 예상: skinimg_read_own, skinimg_insert_own, skinimg_update_own, skinimg_delete_own
```

### 3.3 두 프로젝트 모두 적용

- [ ] `skinlens-dev` 에 RLS/Storage 정책 적용 완료
- [ ] `skinlens-prod` 에 RLS/Storage 정책 적용 완료

---

## 4. Phase 1.3(계속) — API 키·연결 정보 확보

각 프로젝트에서 아래 값을 확보해 비밀 관리자에 저장한다.

### 4.1 Supabase Dashboard → Settings → API

| 항목 | 위치 | 용도 |
|------|------|------|
| Project URL | `https://<project-ref>.supabase.co` | `SUPABASE_URL` |
| anon public key | `anon` `public` | 브라우저용(Phase 2) |
| service_role key | `service_role` `secret` | `SUPABASE_SERVICE_KEY` (서버만) |
| JWT Secret | `JWT Settings` → `JWT Secret` | `SUPABASE_JWT_SECRET` |

### 4.2 Supabase Dashboard → Settings → Database

| 항목 | 값 |
|------|-----|
| Host | `db.<project-ref>.supabase.co` |
| Database name | `postgres` |
| Port | `5432` |
| User | `postgres` |
| Password | 프로젝트 생성 시 설정한 DB 비밀번호 |

### 4.3 DATABASE_URL 조립

```
postgresql://postgres:<db-password>@db.<project-ref>.supabase.co:5432/postgres?sslmode=require
```

> **주의**: Supabase는 **연결 풀링(PgBouncer)** 을 제공한다.
> 장기 연결을 유지하는 worker는 `postgresql://postgres:<password>@db.<project-ref>.supabase.co:6543/postgres?sslmode=require` (포트 6543) 을 사용하는 것이 안정적이다.
> 단, 마이그레이션/DDL은 5432(직접 연결)로 실행해야 한다.

---

## 5. Phase 1.3(계속) — 각 서버 `.env` 채우기

리포지토리의 [`deploy/env/.env.example`](../../deploy/env/.env.example) 을 각 서버에 복사한 뒤,
아래 표에 따라 실제 값으로 교체한다.

### 5.1 dev/staging 서버 (WSL 개발 박스)

```bash
cp deploy/env/.env.example deploy/env/.env
```

`.env` 파일에서 아래 항목을 `skinlens-dev` 값으로 교체:

| 키 | 예시 값 | 비고 |
|----|---------|------|
| `DATABASE_URL` | `postgresql://postgres:<dev-pw>@db.<dev-ref>.supabase.co:5432/postgres?sslmode=require` | 마이그레이션·DDL용 |
| `SUPABASE_URL` | `https://<dev-ref>.supabase.co` | |
| `SUPABASE_SERVICE_KEY` | `<dev-service-role-key>` | 절대 커밋 금지 |
| `SUPABASE_JWT_SECRET` | `<dev-jwt-secret>` | |
| `AUTH_MODE` | `strict` | |
| `STORAGE_BACKEND` | `supabase` | Phase 1.7에서 활성화 예정 |
| `STORAGE_BUCKET` | `skin-images` | |

### 5.2 prod 서버 (운영 VPS)

```bash
cp deploy/env/.env.example deploy/env/.env
```

`.env` 파일에서 아래 항목을 `skinlens-prod` 값으로 교체:

| 키 | 예시 값 | 비고 |
|----|---------|------|
| `DATABASE_URL` | `postgresql://postgres:<prod-pw>@db.<prod-ref>.supabase.co:5432/postgres?sslmode=require` | |
| `SUPABASE_URL` | `https://<prod-ref>.supabase.co` | |
| `SUPABASE_SERVICE_KEY` | `<prod-service-role-key>` | |
| `SUPABASE_JWT_SECRET` | `<prod-jwt-secret>` | |
| `AUTH_MODE` | `strict` | |
| `STORAGE_BACKEND` | `supabase` | |
| `STORAGE_BUCKET` | `skin-images` | |

---

## 6. 완료 체크리스트 (Phase 1.1–1.3)

- [ ] `skinlens-dev` Supabase 프로젝트 생성 완료
- [ ] `skinlens-prod` Supabase 프로젝트 생성 완료
- [ ] 두 프로젝트에 `0001_init.sql` 스키마 적용 완료
- [ ] 두 프로젝트에 `0001_rls_and_storage.sql` RLS/Storage 정책 적용 완료
- [ ] `skin-images` 버킷이 비공개(`public=false`)로 생성됨을 확인
- [ ] RLS 정책이 `jobs`/`job_events`/`prescriptions`/`storage.objects`에 적용됨을 SQL로 확인
- [ ] dev/staging 서버 `.env`에 `skinlens-dev` 연결 정보 채움
- [ ] prod 서버 `.env`에 `skinlens-prod` 연결 정보 채움
- [ ] 모든 비밀번호·키를 비밀 관리자에 저장하고, `.env` 파일은 절대 커밋하지 않음

---

## 7. 다음 단계

Phase 1.1–1.3 완료 후:

1. **Phase 1.4** — 버킷 이름 통일(`uploads`→`skin-images`) 버그 수정
2. **Phase 1.5** — `DATABASE_URL`을 Supabase로 전환(이미 `.env`에 반영됨)
3. **Phase 1.6** — 로컬 `db` 서비스 제거
4. **Phase 1.7** — `storage.py` Supabase seam 실구현
5. **Phase 2** — 웹 포팅(Vite → Next.js PWA → Vercel)

> Phase 2 착수 전, Phase 1.4–1.7의 코드 변경이 선행되어야
> `STORAGE_BACKEND=supabase` 가 실제로 동작한다.
