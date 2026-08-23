-- =============================================================
-- 0001_rls_and_storage.sql
--   SkinLens — 교차 사용자 접근 차단(RLS) + Storage 정책 (P0)
--
--   전제/규칙:
--   - 쓰기 주체는 Gateway(FastAPI)·Worker 이며 Supabase "service_role" 키를
--     사용 → RLS 를 우회한다(정상). 이 파일의 정책은 anon/authenticated
--     경로(클라이언트가 직접 접근하거나, 향후 직접 읽기가 생길 때)에 대한
--     "심층 방어"다. Case A 에서도 키가 새거나 경로가 열릴 때를 막는다.
--   - 모든 사용자 데이터 테이블에 user_id uuid (references auth.users) 가 있다고 가정.
--     ★ 실제 테이블/컬럼명이 다르면 아래 이름만 교체.
--   - 원본 피부 이미지는 비공개 버킷 'skin-images' 에 저장하고,
--     객체 경로를 "{user_id}/{job_id}/..." 규약으로 둔다(폴더 첫 조각 = 소유자).
--   - 클라이언트에는 presigned(signed URL, 짧은 TTL)만 서버가 발급한다.
--
--   적용: Supabase SQL Editor 또는 마이그레이션 파이프라인에서 1회 실행(idempotent).
-- =============================================================

-- ---- 0) 비공개 버킷 + 업로드 크기 상한 --------------------------------
-- (2-3) file_size_limit 을 실제 상한으로 설정한다 — presign 의 declared_size 는 자기신고라
--       브라우저가 얼마든 우회할 수 있다. 버킷 레벨 제한만이 신뢰할 수 있는 유일한 방어선이다.
--       단위: 바이트. 25MB = 26214400.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'skin-images',
  'skin-images',
  false,
  26214400,  -- 25MB
  array['image/jpeg', 'image/png', 'image/webp']
)
on conflict (id) do update set
  public = excluded.public,               -- 항상 비공개 강제
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- ---- 1) 사용자 데이터 테이블: RLS 활성 + 소유자 정책 ---------------------
-- 대상 테이블 목록(★ 실제 스키마에 맞게 조정). 각 테이블에 user_id uuid 필요.
do $$
declare
  t text;
  tables text[] := array['profiles','analyses','prescriptions','jobs'];
begin
  foreach t in array tables loop
    if to_regclass('public.'||t) is null then
      raise notice 'skip: public.% 없음(테이블명 확인)', t;
      continue;
    end if;

    execute format('alter table public.%I enable row level security;', t);
    execute format('alter table public.%I force  row level security;', t);

    -- 재실행 안전: 같은 이름 정책 있으면 제거 후 재생성
    execute format('drop policy if exists %I on public.%I;', t||'_sel_own', t);
    execute format('drop policy if exists %I on public.%I;', t||'_ins_own', t);
    execute format('drop policy if exists %I on public.%I;', t||'_upd_own', t);
    execute format('drop policy if exists %I on public.%I;', t||'_del_own', t);

    -- 본인 행만 조회
    execute format($f$
      create policy %I on public.%I
      for select to authenticated
      using (user_id = auth.uid());
    $f$, t||'_sel_own', t);

    -- 본인 소유로만 삽입
    execute format($f$
      create policy %I on public.%I
      for insert to authenticated
      with check (user_id = auth.uid());
    $f$, t||'_ins_own', t);

    -- 본인 행만 수정(수정 후에도 소유 유지)
    execute format($f$
      create policy %I on public.%I
      for update to authenticated
      using (user_id = auth.uid())
      with check (user_id = auth.uid());
    $f$, t||'_upd_own', t);

    -- 본인 행만 삭제
    execute format($f$
      create policy %I on public.%I
      for delete to authenticated
      using (user_id = auth.uid());
    $f$, t||'_del_own', t);
  end loop;
end $$;

-- ---- 1b) job_events: 소유자 컬럼이 없으므로 상위 job 소유권으로 묶는다 -----
--   (job_events 엔 user_id 가 없다 — 부모 job 의 소유자만 이벤트를 읽도록 EXISTS 로 강제.)
do $$
begin
  if to_regclass('public.job_events') is not null then
    execute 'alter table public.job_events enable row level security';
    execute 'alter table public.job_events force  row level security';
    execute 'drop policy if exists job_events_sel_own on public.job_events';
    execute $p$
      create policy job_events_sel_own on public.job_events
      for select to authenticated
      using (exists (
        select 1 from public.jobs j
        where j.id = job_events.job_id and j.user_id = auth.uid()
      ));
    $p$;
  else
    raise notice 'skip: public.job_events 없음';
  end if;
end $$;

-- ---- 2) Storage 객체: 폴더 첫 조각(=소유자 uid)만 접근 -------------------
-- storage.objects 는 기본적으로 RLS 활성. 'skin-images' 버킷에 소유자 정책 부여.
drop policy if exists "skinimg_read_own"   on storage.objects;
drop policy if exists "skinimg_insert_own" on storage.objects;
drop policy if exists "skinimg_update_own" on storage.objects;
drop policy if exists "skinimg_delete_own" on storage.objects;

create policy "skinimg_read_own" on storage.objects
  for select to authenticated
  using (
    bucket_id = 'skin-images'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "skinimg_insert_own" on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'skin-images'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "skinimg_update_own" on storage.objects
  for update to authenticated
  using (
    bucket_id = 'skin-images'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "skinimg_delete_own" on storage.objects
  for delete to authenticated
  using (
    bucket_id = 'skin-images'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

-- ---- 3) (권장) 보존: 원본 자동 삭제 정책의 자리 -------------------------
-- 이미지/PII 보존은 별도 잡(cron)에서 처리(P1). 예:
--   · 리포트 생성 완료 후 원본 객체 삭제(파생 결과만 유지)
--   · 미완료 업로드는 N일 후 정리, presigned TTL 5~10분
-- 여기서는 스키마 훅만 남기고, 실제 삭제는 worker/cron 이 service_role 로 수행.

-- =============================================================
-- 확인 쿼리(참고):
--   select relname, relrowsecurity, relforcerowsecurity
--   from pg_class where relname in ('profiles','analyses','prescriptions','jobs');
--   select policyname, tablename from pg_policies where schemaname='public';
--   select policyname from pg_policies where tablename='objects';
-- =============================================================
