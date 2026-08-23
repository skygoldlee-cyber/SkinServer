-- 운영 스키마 마이그레이션(초기). gateway auto-DDL 은 dev 전용이며, 운영은 이 파일을 적용한다.
-- 적용: psql "$DATABASE_URL" -f deploy/db/migrations/0001_init.sql
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
    job_id uuid NOT NULL UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,   -- 재처리 중복 차단
    user_id uuid NOT NULL,                                               -- RLS/소유권 정렬
    grade text, ratio_pct numeric, score numeric,
    selected_mixes jsonb, pcr_mixes jsonb, per_metric jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS prescriptions_job_idx  ON prescriptions (job_id);
CREATE INDEX IF NOT EXISTS prescriptions_user_idx ON prescriptions (user_id);
