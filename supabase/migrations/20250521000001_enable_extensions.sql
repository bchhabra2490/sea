-- Extensions required for UUIDs, vectors, and timestamps
create extension if not exists "uuid-ossp";

-- pgvector in public schema (Supabase default; avoids extensions.vector type errors)
create extension if not exists vector;

comment on extension vector is 'pgvector for conversation embeddings and similarity search';
