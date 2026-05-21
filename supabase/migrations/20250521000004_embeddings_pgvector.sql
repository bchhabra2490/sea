-- Embeddings and vector search (text-embedding-3-small = 1536 dimensions)
create table if not exists public.se_embeddings (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references public.se_conversations (id) on delete cascade,
    analysis_run_id uuid not null references public.se_analysis_runs (id) on delete cascade,
    embedding vector(1536) not null,
    created_at timestamptz not null default now(),
    constraint se_embeddings_run_conversation_key
        unique (conversation_id, analysis_run_id)
);

create index if not exists idx_se_embeddings_run
    on public.se_embeddings (analysis_run_id);

-- HNSW index for cosine similarity search (pgvector)
create index if not exists idx_se_embeddings_hnsw_cosine
    on public.se_embeddings
    using hnsw (embedding vector_cosine_ops);

-- Precomputed cluster centroids per run (for fast bot classification)
create table if not exists public.se_cluster_centroids (
    id uuid primary key default gen_random_uuid(),
    analysis_run_id uuid not null references public.se_analysis_runs (id) on delete cascade,
    cluster_id integer not null,
    centroid vector(1536) not null,
    member_count integer not null default 0,
    created_at timestamptz not null default now(),
    constraint se_cluster_centroids_run_cluster_key
        unique (analysis_run_id, cluster_id)
);

create index if not exists idx_se_cluster_centroids_run
    on public.se_cluster_centroids (analysis_run_id);

create index if not exists idx_se_cluster_centroids_hnsw
    on public.se_cluster_centroids
    using hnsw (centroid vector_cosine_ops);

-- Match nearest topic cluster centroids for a query embedding (bot)
create or replace function public.se_match_cluster_centroids(
    query_embedding vector(1536),
    target_run_id uuid,
    match_count integer default 3
)
returns table (
    cluster_id integer,
    similarity double precision,
    member_count integer
)
language sql
stable
as $$
    select
        cc.cluster_id,
        1 - (cc.centroid <=> query_embedding) as similarity,
        cc.member_count
    from public.se_cluster_centroids cc
    where cc.analysis_run_id = target_run_id
      and cc.cluster_id >= 0
    order by cc.centroid <=> query_embedding
    limit match_count;
$$;

-- Match individual conversation embeddings (optional inspection)
create or replace function public.se_match_conversation_embeddings(
    query_embedding vector(1536),
    target_run_id uuid,
    match_count integer default 10
)
returns table (
    conversation_id uuid,
    external_id text,
    similarity double precision
)
language sql
stable
as $$
    select
        e.conversation_id,
        c.external_id,
        1 - (e.embedding <=> query_embedding) as similarity
    from public.se_embeddings e
    join public.se_conversations c on c.id = e.conversation_id
    where e.analysis_run_id = target_run_id
    order by e.embedding <=> query_embedding
    limit match_count;
$$;

comment on function public.se_match_cluster_centroids is
    'Cosine similarity search against cluster centroids for real-time bot routing';
