-- Phase 4J: dataset training job queue (backend runner only)
-- Run in Supabase SQL editor. Does not train or deploy automatically.

create table if not exists public.dataset_training_jobs (
  id uuid primary key default gen_random_uuid(),
  requested_by text,
  status text not null default 'requested',
  requested_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  result_report_path text,
  candidate_model_path text,
  error text
);

comment on table public.dataset_training_jobs is
  'Queue for safe auto-train pipeline runs. Backend runner updates status; never auto-promotes production.';

comment on column public.dataset_training_jobs.status is
  'requested|running|blocked_gate_closed|failed|passed_candidate|rejected_candidate|promotion_ready';

create index if not exists dataset_training_jobs_status_requested_at_idx
  on public.dataset_training_jobs (status, requested_at);

-- Optional: restrict writes to service role (adjust RLS for your project)
alter table public.dataset_training_jobs enable row level security;
