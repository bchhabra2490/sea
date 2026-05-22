# Sentiment Engine

A modular conversational intelligence engine for PM analytics. Phase 1 ingests user support conversations, preprocesses user messages, generates OpenAI embeddings, clusters semantically similar threads, and labels topics with GPT.

## Architecture

For reviewers:

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** — diagrams, data flow, module map (1–2 pages).
- **[REASONING.md](./REASONING.md)** — why Postgres/pgvector, UMAP+HDBSCAN, OpenAI/Supabase SDKs, and rejected alternatives.

```
JSONL / DB ingest → preprocess → OpenAI embeddings → UMAP → HDBSCAN → GPT topic labels → Supabase
                                                                                      ↓
                                                                              FastAPI (sync)
```

| Module | Responsibility |
|--------|----------------|
| `app/ingest/` | Load JSONL, preprocess user messages |
| `app/embeddings/` | Batch OpenAI embeddings |
| `app/db/` | Supabase repository (Postgres + pgvector) |
| `app/clustering/` | UMAP (cosine) + HDBSCAN (euclidean) |
| `app/labeling/` | GPT topic names, summaries, severity |
| `app/insights/` | Phase 2 placeholder |
| `app/api/` | Pipeline orchestration + REST endpoints |

## Requirements

- Python 3.11+
- OpenAI API key with access to embeddings and chat completions

## Setup

```bash
cd sentiment-engine
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | **Required.** OpenAI API key |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `LABELING_MODEL` | `gpt-4o-mini` | Chat model for topic labels |
| `EMBEDDING_BATCH_SIZE` | `64` | Texts per embedding API call |
| `EMBEDDING_MAX_RETRIES` | `3` | Retries per batch |
| `UMAP_N_NEIGHBORS` | `15` | UMAP neighborhood size |
| `UMAP_N_COMPONENTS` | `10` | Reduced dimensions |
| `UMAP_MIN_DIST` | `0.0` | UMAP minimum distance |
| `UMAP_METRIC` | `cosine` | Metric on raw embeddings |
| `HDBSCAN_MIN_CLUSTER_SIZE` | `5` | Minimum cluster size |
| `HDBSCAN_MIN_SAMPLES` | — | Optional HDBSCAN `min_samples` |
| `SAMPLES_PER_CLUSTER` | `5` | Representative messages sent to GPT |
| `APP_ROOT` | project root | App root in Docker/Railway (`/app`) |
| `DATA_DIR` | `{APP_ROOT}/data` | Temp upload dir (optional Railway volume) |
| `SUPABASE_URL` | **required** | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | **required** | Server-side DB + Storage key |
| `DATABASE_URL` | — | Postgres connection string (Supabase → Settings → Database) |
| `STORAGE_BUCKET` | `proofs` | Bucket for CSV/JSONL uploads |
| `EMBEDDING_DIMENSION` | `1536` | pgvector column size (`text-embedding-3-small`) |

## Supabase (PostgreSQL + pgvector + Storage)

Database schema lives in `supabase/migrations/`. File uploads go to the **`proofs`** storage bucket.

### Schema overview

```
se_analysis_runs          ← pipeline / cron jobs
se_conversations          ← raw records (external_id, source)
se_messages               ← user / assistant turns
se_processed_texts        ← cleaned user text per run
se_embeddings             ← pgvector(1536) per run
se_cluster_centroids      ← mean vectors per cluster (bot search)
se_cluster_assignments    ← conversation → cluster_id
se_topic_labels           ← GPT labels per cluster per run
```

**Search RPCs (pgvector):**

- `se_match_cluster_centroids(query_embedding, run_id)` — bot topic routing
- `se_match_conversation_embeddings(query_embedding, run_id)` — nearest conversations

### Setup

1. Create a [Supabase](https://supabase.com) project.
2. Apply migrations:

```bash
chmod +x scripts/apply_supabase_migrations.sh
./scripts/apply_supabase_migrations.sh
# or: supabase link && supabase db push
```

3. Set env vars in `.env` (see `.env.example`).
4. Enable **pgvector** in Dashboard → Database → Extensions if not already enabled.

### Uploads → `proofs` bucket

When `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set, `POST /analyze/upload` stores the raw file at:

```
proofs/uploads/<timestamp>_<filename>
```

A local JSONL copy is still written under `data/uploads/` for processing.

The app requires Supabase: pipeline, insights, bot, and job status use **Postgres + pgvector** and the **`proofs`** storage bucket.

See `supabase/README.md` for migration details and RLS notes.

## Deploy on Railway

Production deploy uses a **multi-stage Dockerfile** (builds the React UI, runs FastAPI on `$PORT`).

### 1. Install Railway CLI

```bash
npm install -g @railway/cli
# or: brew install railway
railway login
```

### 2. Deploy

```bash
chmod +x scripts/deploy_railway.sh scripts/start.sh
./scripts/deploy_railway.sh --init    # first time only (links project)
./scripts/deploy_railway.sh           # build + deploy
```

Or manually:

```bash
railway up --detach
```

### 3. Configure variables

```bash
./scripts/deploy_railway.sh --env
```

Set at minimum `OPENAI_API_KEY` in the Railway dashboard. See `railway.env.example`.

### 4. Persistent storage (optional)

Analysis results live in Supabase. An optional Railway **Volume** is only needed if you want `data/uploads/` temp files to survive redeploys:

- `DATA_DIR=/data/data` (mount volume at `/data`)

### 5. Generate a public URL

```bash
railway domain
```

Open `https://<your-domain>/` for the dashboard and `/bot` for the chatbot.

### Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Node frontend build + Python runtime |
| `railway.toml` | Railway build/deploy settings |
| `scripts/deploy_railway.sh` | One-command deploy script |
| `scripts/start.sh` | Production uvicorn entrypoint |
| `railway.env.example` | Variable template for Railway |

### Daily cron on Railway

Run re-analysis as a **scheduled Railway service** or manually:

```bash
railway run python scripts/run_daily_analysis.py
```

## Input format

Place JSONL files under `data/`. Each line is one conversation:

```json
{
  "conversation_id": "123",
  "messages": [
    {"role": "user", "content": "My refund hasn't arrived"},
    {"role": "assistant", "content": "Checking that for you"}
  ],
  "timestamp": "2026-05-21"
}
```

A sample file is provided at `data/sample_conversations.jsonl` (25 conversations across refund, login, billing, and shipping themes).

### CSV upload format

Upload a `.csv` with **two columns** — user messages and bot/assistant replies. Each row becomes one conversation. Headers are detected automatically (`user` / `bot`, or synonyms like `customer` / `assistant`). Without headers, the first column is treated as user and the second as bot.

```csv
user,bot
"My refund hasn't arrived","I'll check that for you"
"Can't log in","Try resetting your password"
```

A sample CSV is at `data/sample_conversations.csv`. CSV uploads are converted to JSONL under `data/uploads/` before analysis.

### Preprocessing behavior

- Extracts **only** `role: "user"` messages
- Strips common greetings and filler phrases
- Concatenates user turns into one text block
- Normalizes whitespace
- Drops conversations with no usable user text

## Clustering pipeline

1. **Embeddings** — `text-embedding-3-small` produces dense vectors per conversation.
2. **UMAP** — Reduces dimensionality using **cosine** distance on embeddings.
3. **HDBSCAN** — Clusters reduced points using **euclidean** distance. Label `-1` marks noise/outliers.

Tune `HDBSCAN_MIN_CLUSTER_SIZE` for your dataset size; smaller corpora may need `3` to discover topics.

## Daily re-analysis (cron)

A cron job can re-run the full pipeline every day at midnight so clusters and topics reflect new bot messages and uploads stored in Supabase.

### Manual run

```bash
source .venv/bin/activate
python scripts/run_daily_analysis.py
```

By default analyzes **all conversations in Supabase** (`force_recompute=True`). Pass a file path to `run_daily_reanalysis(path)` to ingest a specific JSONL only.

### Install midnight cron

```bash
chmod +x scripts/cron_daily_analysis.sh
crontab -e
```

Add this line (replace with your project path):

```cron
0 0 * * * /Users/you/Desktop/projects/sentiment-engine/scripts/cron_daily_analysis.sh
```

See `crontab.example` for UTC and logging notes.

**Logs:**

- `logs/cron.log` — cron wrapper stdout/stderr
- `logs/daily_analysis.log` — pipeline job details

The API server does not need to be running; the script invokes the pipeline directly.

## Insights UI (React + Tailwind + shadcn)

The dashboard is a React SPA built with Vite, Tailwind CSS, and shadcn-style components. FastAPI serves the production build from `frontend/dist/` at the root URL.

### Build the frontend

```bash
./scripts/build_frontend.sh
# or manually:
cd frontend && npm install && npm run build
```

### Run API + UI together

```bash
source .venv/bin/activate
./scripts/build_frontend.sh   # once, or after UI changes
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser (PM Insights dashboard) or **http://localhost:8000/bot** for the standalone Topic Bot UI. Use **Run analysis** to execute the pipeline; the dashboard shows:

- Summary stats (conversations, topics, clusters, noise)
- Topic cards with severity badges (click to filter)
- Cluster distribution chart
- Conversation table with preprocessed user text

### Frontend development (optional)

For hot reload during UI work, run Vite on port 5173 with API proxy:

```bash
cd frontend && npm run dev
```

Vite proxies `/analyze`, `/insights`, `/topics`, and `/clusters` to `http://localhost:8000` (configure in `frontend/vite.config.ts` if needed).

## Running the API

```bash
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### API documentation

| URL | Format | Description |
|-----|--------|-------------|
| [/integrate](/integrate) | UI | Bot integration API guide (real-time messages) |
| [/bot/docs](/bot/docs) | JSON | Bot API catalog for integrators |
| [/docs](/docs) | OpenAPI | Full platform Swagger UI |

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Insights dashboard (when `frontend/dist` exists) |
| `GET` | `/health` | Health check |
| `GET` | `/integrate` | Bot integration docs UI |
| `GET` | `/bot/docs` | Bot API catalog JSON |
| `GET` | `/insights` | Aggregated dashboard payload |
| `GET` | `/bot/status` | Whether real-time classification is available |
| `POST` | `/bot/classify` | Classify a user message and persist to Supabase (no agent reply) |
| `POST` | `/bot/chat` | Classify, agent reply, and persist turn to Supabase |
| `GET` | `/pipeline/status` | Background pipeline job status (poll while running) |
| `POST` | `/analyze` | Start full pipeline in background |
| `POST` | `/analyze/sample` | Load `data/sample_conversations.jsonl` into DB, then run pipeline |
| `POST` | `/analyze/upload` | Upload JSONL or CSV and start pipeline in background |
| `GET` | `/topics` | Topic labels per cluster |
| `GET` | `/clusters` | Per-conversation cluster IDs |

### Example: run analysis (background)

```bash
# Start job (returns immediately)
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"input_path": "data/sample_conversations.jsonl", "force_recompute": true}'

# Poll status
curl http://localhost:8000/pipeline/status
```

Start response:

```json
{
  "job_id": "a1b2c3d4-...",
  "status": "queued",
  "message": "Pipeline started in background"
}
```

Status response includes `stage`, `progress_percent`, `steps`, and `result` when `stage` is `completed`. State is stored in `se_analysis_runs`.

### Topic bot (real-time classification)

After a pipeline run, classify new user messages against existing clusters:

```bash
curl -X POST http://localhost:8000/bot/classify \
  -H "Content-Type: application/json" \
  -d '{"message": "My refund is still missing"}'
```

The message is preprocessed, embedded with the same OpenAI model, and matched to the nearest **cluster centroid** (mean embedding per cluster) using cosine similarity. Returns topic name, summary, severity, and alternative matches.

**Bot UI:** [http://localhost:8000/bot](http://localhost:8000/bot) — support chatbot: agent replies, classifies via `se_match_cluster_centroids`, persists to Supabase.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/bot/chat` | Chat turn: classify, agent reply, append JSONL, update clusters |
| `GET` | `/bot/history` | Recent bot turns from sample JSONL |

### Example: fetch topics

```bash
curl http://localhost:8000/topics
```

```json
{
  "topics": [
    {
      "cluster_id": 0,
      "topic": "Refund Processing Delays",
      "summary": "Users report slow or missing refunds after returns or duplicate charges.",
      "severity": "high"
    }
  ]
}
```

### Example: fetch cluster assignments

```bash
curl http://localhost:8000/clusters
```

## Output artifacts

Results live in `se_analysis_runs`, `se_conversations`, `se_embeddings`, `se_cluster_centroids`, `se_cluster_assignments`, and `se_topic_labels`. The API reads from the current run (`is_current = true`) or the latest completed run with data.

`POST /analyze` with no `input_path` re-clusters **all conversations in Supabase**. Pass `input_path` to analyze a specific uploaded JSONL file only.

## Programmatic usage

```python
from app.api.pipeline import AnalysisPipeline

pipeline = AnalysisPipeline()
result = pipeline.run(force_recompute=True)  # all conversations in Supabase
# result = pipeline.run("data/sample_conversations.jsonl", force_recompute=True)
print(result)
```

## Project layout

```
sentiment-engine/
├── app/
│   ├── ingest/          # loader, preprocess
│   ├── embeddings/      # OpenAI embedder
│   ├── clustering/      # UMAP + HDBSCAN
│   ├── labeling/        # GPT topic labeler
│   ├── insights/        # Phase 2 (stub)
│   ├── api/             # pipeline, routes, static serving
│   ├── db/              # Supabase client, repository (Postgres + pgvector)
│   ├── storage/         # proofs bucket uploads
│   ├── models/          # Pydantic schemas
│   └── utils/           # config, logging
├── frontend/            # React + Tailwind + shadcn UI
├── scripts/             # build_frontend.sh
├── data/
├── main.py
├── requirements.txt
└── README.md
```

## Future improvements (TODOs in code)

- Structured PM insight reports (`app/insights/`)
- Async job queue for long-running analysis
- Vector database for similarity search at scale
- Authentication and multi-tenant data paths
- Dashboard and streaming analytics

## License

MIT (add your license as needed).
