# Supabase schema & storage

PostgreSQL schema with **pgvector** for embeddings and the **`proofs`** storage bucket for CSV/JSONL uploads.

All application tables use the **`se_`** prefix (sentiment engine).

## Apply migrations

### Supabase hosted (recommended)

```bash
# Install CLI: https://supabase.com/docs/guides/cli
supabase login
supabase link --project-ref <your-project-ref>
supabase db push
```

Or run each file in order via **SQL Editor** in the Supabase dashboard.

### Local Supabase

```bash
supabase start
supabase db reset   # applies all migrations in migrations/
```

## Migration order

| File | Purpose |
|------|---------|
| `20250521000001_enable_extensions.sql` | `vector` (pgvector) |
| `20250521000002_analysis_runs.sql` | `se_analysis_runs` — pipeline / cron runs |
| `20250521000003_conversations.sql` | `se_conversations`, `se_messages`, `se_processed_texts` |
| `20250521000004_embeddings_pgvector.sql` | `se_embeddings`, `se_cluster_centroids`, search RPCs |
| `20250521000005_clusters_and_topics.sql` | `se_cluster_assignments`, `se_topic_labels`, `se_latest_insights` view |
| `20250521000006_storage_proofs_bucket.sql` | Storage bucket `proofs` |
| `20250521000007_rls_policies.sql` | RLS for service_role + authenticated |
| `20250521000008_vector_public_compat.sql` | Legacy placeholder (vector uses `public` schema) |

## Tables

| Table | Purpose |
|-------|---------|
| `se_analysis_runs` | Pipeline job state and summary stats |
| `se_conversations` | Raw conversation records |
| `se_messages` | User / assistant turns |
| `se_processed_texts` | Cleaned user text per run |
| `se_embeddings` | pgvector(1536) per conversation per run |
| `se_cluster_centroids` | Mean embedding per cluster (bot routing) |
| `se_cluster_assignments` | Conversation → cluster_id |
| `se_topic_labels` | GPT labels per cluster |

## Application integration

When `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set:

- `POST /analyze` persists pipeline results to the `se_*` tables
- `GET /insights`, `/topics`, `/clusters` read from the current `se_analysis_runs` row
- `GET /pipeline/status` reads from `se_analysis_runs`
- Bot chat uses `se_match_cluster_centroids` for classification

## pgvector

- Embedding dimension: **1536** (`text-embedding-3-small`)
- Tables: `se_embeddings`, `se_cluster_centroids`
- RPCs:
  - `se_match_cluster_centroids(query_embedding, target_run_id, match_count)` — bot routing
  - `se_match_conversation_embeddings(...)` — nearest conversations

## Storage bucket `proofs`

Private bucket for uploaded `.csv` and `.jsonl` files.

Path convention from the API:

```
uploads/20250521_120000_myfile.jsonl
```

Backend uses `SUPABASE_SERVICE_ROLE_KEY` for uploads (bypasses RLS).

## Environment variables

```bash
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
DATABASE_URL=postgresql://postgres:...@db.<ref>.supabase.co:5432/postgres
EMBEDDING_DIMENSION=1536
STORAGE_BUCKET=proofs
```

Use the **service role** key only on the server, never in the browser.

## If pgvector type errors occur

Enable the extension in Dashboard → Database → Extensions → **vector**, or run:

```sql
create extension if not exists vector;
```

Migrations use `vector(1536)` in the **public** schema (not `extensions.vector`).
