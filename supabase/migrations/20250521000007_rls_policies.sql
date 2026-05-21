-- Row Level Security (enable when using Supabase Auth from clients)
-- Backend using service_role key bypasses RLS.

alter table public.se_analysis_runs enable row level security;
alter table public.se_conversations enable row level security;
alter table public.se_messages enable row level security;
alter table public.se_processed_texts enable row level security;
alter table public.se_embeddings enable row level security;
alter table public.se_cluster_assignments enable row level security;
alter table public.se_topic_labels enable row level security;
alter table public.se_cluster_centroids enable row level security;

-- Service role full access (used by FastAPI backend)
create policy "Service role all se_analysis_runs"
    on public.se_analysis_runs for all to service_role
    using (true) with check (true);

create policy "Service role all se_conversations"
    on public.se_conversations for all to service_role
    using (true) with check (true);

create policy "Service role all se_messages"
    on public.se_messages for all to service_role
    using (true) with check (true);

create policy "Service role all se_processed_texts"
    on public.se_processed_texts for all to service_role
    using (true) with check (true);

create policy "Service role all se_embeddings"
    on public.se_embeddings for all to service_role
    using (true) with check (true);

create policy "Service role all se_cluster_assignments"
    on public.se_cluster_assignments for all to service_role
    using (true) with check (true);

create policy "Service role all se_topic_labels"
    on public.se_topic_labels for all to service_role
    using (true) with check (true);

create policy "Service role all se_cluster_centroids"
    on public.se_cluster_centroids for all to service_role
    using (true) with check (true);

-- Read-only for authenticated users (dashboard); tighten per-tenant later
create policy "Authenticated read se_analysis_runs"
    on public.se_analysis_runs for select to authenticated using (true);

create policy "Authenticated read se_conversations"
    on public.se_conversations for select to authenticated using (true);

create policy "Authenticated read se_messages"
    on public.se_messages for select to authenticated using (true);

create policy "Authenticated read se_processed_texts"
    on public.se_processed_texts for select to authenticated using (true);

create policy "Authenticated read se_embeddings"
    on public.se_embeddings for select to authenticated using (true);

create policy "Authenticated read se_cluster_assignments"
    on public.se_cluster_assignments for select to authenticated using (true);

create policy "Authenticated read se_topic_labels"
    on public.se_topic_labels for select to authenticated using (true);

create policy "Authenticated read se_cluster_centroids"
    on public.se_cluster_centroids for select to authenticated using (true);
