-- Cluster assignments and GPT topic labels per analysis run
create table if not exists public.se_cluster_assignments (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references public.se_conversations (id) on delete cascade,
    analysis_run_id uuid not null references public.se_analysis_runs (id) on delete cascade,
    cluster_id integer not null,
    processed_text text,
    created_at timestamptz not null default now(),
    constraint se_cluster_assignments_run_conversation_key
        unique (conversation_id, analysis_run_id)
);

create index if not exists idx_se_cluster_assignments_run
    on public.se_cluster_assignments (analysis_run_id);

create index if not exists idx_se_cluster_assignments_cluster
    on public.se_cluster_assignments (analysis_run_id, cluster_id);

create table if not exists public.se_topic_labels (
    id uuid primary key default gen_random_uuid(),
    analysis_run_id uuid not null references public.se_analysis_runs (id) on delete cascade,
    cluster_id integer not null,
    topic text not null,
    summary text not null,
    severity text not null default 'medium'
        check (severity in ('low', 'medium', 'high', 'critical')),
    created_at timestamptz not null default now(),
    constraint se_topic_labels_run_cluster_key
        unique (analysis_run_id, cluster_id)
);

create index if not exists idx_se_topic_labels_run
    on public.se_topic_labels (analysis_run_id);

-- View: latest completed run insights (for API)
create or replace view public.se_latest_insights as
select
    ar.id as analysis_run_id,
    ar.conversations_processed,
    ar.clusters_found,
    ar.noise_points,
    ar.topics_labeled,
    ar.completed_at
from public.se_analysis_runs ar
where ar.is_current = true
  and ar.status = 'completed'
limit 1;

comment on view public.se_latest_insights is 'Pointer to the current production analysis run';
