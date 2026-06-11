-- Phase 4H: duplicate protection and review workflow for private_dataset_captures
-- Run in Supabase SQL editor (not committed with raw images).

create unique index if not exists private_dataset_captures_sha256_uidx
  on public.private_dataset_captures (sha256);

alter table public.private_dataset_captures
  add column if not exists ready_for_import boolean not null default false,
  add column if not exists review_status text,
  add column if not exists is_duplicate boolean not null default false,
  add column if not exists duplicate_of_id uuid,
  add column if not exists keep_for_regression_only boolean not null default false,
  add column if not exists quality_warnings jsonb;

comment on column public.private_dataset_captures.ready_for_import is
  'Set true when human-approved; import script pulls these locally.';
comment on column public.private_dataset_captures.review_status is
  'approve|reject|duplicate|wrong_bucket|low_quality|keep_for_regression_only';
