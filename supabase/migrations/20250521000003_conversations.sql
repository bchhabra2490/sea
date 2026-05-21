-- Raw and processed conversation data
create table if not exists public.se_conversations (
    id uuid primary key default gen_random_uuid(),
    external_id text not null,
    source text not null default 'jsonl'
        check (source in ('jsonl', 'csv', 'bot', 'upload', 'sample')),
    conversation_timestamp date,
    storage_path text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint se_conversations_external_id_key unique (external_id)
);

create table if not exists public.se_messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references public.se_conversations (id) on delete cascade,
    role text not null check (role in ('user', 'assistant', 'system')),
    content text not null,
    position smallint not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_se_messages_conversation_id
    on public.se_messages (conversation_id);

create table if not exists public.se_processed_texts (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references public.se_conversations (id) on delete cascade,
    analysis_run_id uuid not null references public.se_analysis_runs (id) on delete cascade,
    text text not null,
    created_at timestamptz not null default now(),
    constraint se_processed_texts_run_conversation_key
        unique (conversation_id, analysis_run_id)
);

create index if not exists idx_se_processed_texts_run
    on public.se_processed_texts (analysis_run_id);

comment on table public.se_processed_texts is 'Cleaned user-only text per conversation per analysis run';
