-- Pipeline / cron job runs (versioned analysis)
create table if not exists public.se_analysis_runs (
    id uuid primary key default gen_random_uuid(),
    status text not null default 'idle'
        check (status in ('idle', 'queued', 'running', 'completed', 'failed')),
    stage text,
    progress_percent smallint not null default 0
        check (progress_percent >= 0 and progress_percent <= 100),
    message text,
    input_source text,
    storage_path text,
    started_at timestamptz,
    completed_at timestamptz,
    error text,
    is_current boolean not null default false,
    conversations_processed integer not null default 0,
    clusters_found integer not null default 0,
    noise_points integer not null default 0,
    topics_labeled integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_se_analysis_runs_is_current
    on public.se_analysis_runs (is_current)
    where is_current = true;

create index if not exists idx_se_analysis_runs_created_at
    on public.se_analysis_runs (created_at desc);

comment on table public.se_analysis_runs is 'One row per pipeline or cron execution';
comment on column public.se_analysis_runs.storage_path is 'Path in Supabase Storage bucket proofs for input file';
