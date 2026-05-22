# Architecture

Short reference for reviewers. Deeper rationale: [REASONING.md](./REASONING.md).

---

## System context

```mermaid
flowchart LR
  subgraph clients [Clients]
    PM[PM Insights UI]
    BotUI[Support Chat UI]
    Ext[External bot via HTTP]
  end

  subgraph app [FastAPI app]
    API[REST API]
    Pipe[Analysis pipeline]
    Bot[Bot service]
  end

  subgraph external [External services]
    OAI[OpenAI API]
  end

  subgraph data [Supabase]
    PG[(Postgres + pgvector)]
    ST[Storage proofs bucket]
  end

  PM --> API
  BotUI --> API
  Ext --> API
  API --> Pipe
  API --> Bot
  Pipe --> OAI
  Bot --> OAI
  Pipe --> PG
  Bot --> PG
  API --> ST
```

| Layer | Tech | Role |
|-------|------|------|
| UI | React + Vite | Insights dashboard, chat demo, `/integrate` docs |
| API | FastAPI | Orchestration, background jobs, OpenAPI at `/docs` |
| ML | UMAP, HDBSCAN, OpenAI embeddings | Batch topic discovery |
| Data | Supabase Postgres + pgvector + Storage | Durable state and similarity search |

---

## Batch analysis pipeline

Triggered by `POST /analyze`, `POST /analyze/sample`, or `POST /analyze/upload`. Runs in a **background thread**; status via `GET /pipeline/status`.

```mermaid
flowchart TD
  A[Ingest JSONL/CSV or DB rows] --> B[Preprocess user text]
  B --> C[OpenAI embeddings batch]
  C --> D[UMAP cosine 1536 to 10D]
  D --> E[HDBSCAN euclidean]
  E --> F[Save assignments + centroids]
  F --> G[GPT label per cluster]
  G --> H[Mark run completed / is_current]
```

```mermaid
erDiagram
  se_analysis_runs ||--o{ se_conversations : references
  se_conversations ||--o{ se_messages : contains
  se_analysis_runs ||--o{ se_embeddings : has
  se_analysis_runs ||--o{ se_cluster_assignments : has
  se_analysis_runs ||--o{ se_cluster_centroids : has
  se_analysis_runs ||--o{ se_topic_labels : has

  se_analysis_runs {
    uuid id PK
    string status
    string stage
    bool is_current
  }

  se_conversations {
    uuid id PK
    string external_id UK
    string source
  }

  se_messages {
    uuid id PK
    string role
    text content
  }

  se_cluster_centroids {
    int cluster_id
    vector centroid
  }
```

**Read path for PM Insights:** resolve current `analysis_run_id` → load topics, assignments, counts.

**Write path for uploads:** Storage `proofs/uploads/...` + upsert conversations/messages → start pipeline on temp JSONL path.

---

## Real-time bot path

For integrators and the Support Chat UI.

```mermaid
sequenceDiagram
  participant Client
  participant API as FastAPI /bot
  participant Bot as BotChatService
  participant OAI as OpenAI
  participant DB as Postgres pgvector

  Client->>API: POST /bot/classify or /bot/chat
  API->>Bot: classify_and_store / handle_message
  Bot->>OAI: embeddings.create
  Bot->>DB: RPC se_match_cluster_centroids
  alt similarity >= threshold
    Bot->>DB: assign cluster_id
  else below threshold
    Bot->>DB: cluster_id = -1 noise
  end
  opt /bot/chat only
    Bot->>OAI: chat completion agent reply
  end
  Bot->>DB: upsert conversation messages embedding assignment
  Bot-->>Client: classification + conversation_id
```

| Endpoint | Persists | Agent reply |
|----------|----------|---------------|
| `POST /bot/classify` | Yes | No |
| `POST /bot/chat` | Yes | Yes |
| `GET /bot/status` | — | Readiness check |
| `GET /bot/history` | — | Recent `source=bot` turns |

Classification uses **cosine similarity** to stored centroids (`1 - (centroid <=> query)`), not re-running UMAP/HDBSCAN online.

---

## Deployment shape

```mermaid
flowchart TB
  subgraph railway [Railway / Docker]
    IMG[Multi-stage image]
    IMG --> PY[Python 3.11 + FastAPI]
    IMG --> FE[frontend/dist static]
    VOL[Optional DATA_DIR volume]
  end

  IMG --> SB[(Supabase cloud)]
```

- **Dockerfile:** build React → copy `dist` → run `uvicorn` on `$PORT`.
- **Required env:** `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.
- **Bundled sample:** `data/sample_conversations.jsonl` via `POST /analyze/sample`.

---

## Module map

| Path | Responsibility |
|------|----------------|
| `app/ingest/` | JSONL/CSV load, user-text preprocessing |
| `app/embeddings/` | OpenAI embedder, batching, retries |
| `app/clustering/` | UMAP + HDBSCAN; nearest-centroid classify |
| `app/labeling/` | GPT topic names and severity |
| `app/db/` | Supabase repository, RPC classify |
| `app/api/` | Routes, pipeline, job runner, bot, uploads |
| `app/jobs/` | Daily re-analysis script hook |
| `frontend/` | PM Insights, Bot, Integration docs SPAs |
| `supabase/migrations/` | Schema, indexes, RPCs, RLS |

---

## API surface (evaluation focus)

| Area | Paths |
|------|--------|
| Pipeline | `/analyze`, `/analyze/sample`, `/analyze/upload`, `/pipeline/status`, `/insights` |
| Bot integration | `/bot/status`, `/bot/classify`, `/bot/chat`, `/bot/history`, `/bot/docs` |
| Ops | `/health`, `/data/reset` |
| Docs UI | `/integrate` (human), `/docs` (OpenAPI) |

---

## Security notes (Phase 1)

- CORS is permissive for demo UX; production would add auth and tighten origins.
- Service role key is **server-only**; never shipped to the browser.
- RLS policies exist in migrations; backend uses service role for app writes.

See [REASONING.md](./REASONING.md) for rejected alternatives and scaling follow-ups.
