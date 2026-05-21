#!/usr/bin/env bash
#
# Deploy Sentiment Engine to Railway.
#
# Prerequisites:
#   npm i -g @railway/cli   OR   brew install railway
#   railway login
#
# Usage:
#   ./scripts/deploy_railway.sh              # deploy linked project
#   ./scripts/deploy_railway.sh --init       # railway init first
#   ./scripts/deploy_railway.sh --env        # open variables setup guide
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

INIT=false
ENV_HELP=false
SERVICE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --init)
      INIT=true
      shift
      ;;
    --env)
      ENV_HELP=true
      shift
      ;;
    --service)
      SERVICE="${2:-}"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [--init] [--env] [--service NAME]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if ! command -v railway >/dev/null 2>&1; then
  echo "Railway CLI not found. Install with:" >&2
  echo "  npm install -g @railway/cli" >&2
  echo "  # or: brew install railway" >&2
  exit 1
fi

if ! railway whoami >/dev/null 2>&1; then
  echo "Not logged in to Railway. Run: railway login" >&2
  exit 1
fi

print_env_guide() {
  cat <<'EOF'

Set these variables in Railway (Dashboard → Service → Variables):

  Required:
    OPENAI_API_KEY=sk-...

  Recommended:
    EMBEDDING_MODEL=text-embedding-3-small
    LABELING_MODEL=gpt-4o-mini
  Supabase (required):
    SUPABASE_URL=https://<ref>.supabase.co
    SUPABASE_SERVICE_ROLE_KEY=...

  Optional temp uploads dir (Volume at /data):
    DATA_DIR=/data/data

  Optional tuning:
    HDBSCAN_MIN_CLUSTER_SIZE=5
    UMAP_N_NEIGHBORS=15

After deploy, open the generated URL and run POST /analyze once (or use the UI).

EOF
}

if [[ "$ENV_HELP" == true ]]; then
  print_env_guide
  exit 0
fi

echo "==> Deploying from $ROOT"

if [[ "$INIT" == true ]]; then
  echo "==> Initializing Railway project (interactive)..."
  railway init
fi

if [[ ! -f railway.toml ]]; then
  echo "railway.toml not found in project root." >&2
  exit 1
fi

DEPLOY_ARGS=(up --detach)
if [[ -n "$SERVICE" ]]; then
  DEPLOY_ARGS+=(--service "$SERVICE")
fi

echo "==> Building and deploying (Dockerfile)..."
railway "${DEPLOY_ARGS[@]}"

echo ""
echo "==> Deploy triggered."
railway status 2>/dev/null || true

DOMAIN=$(railway domain 2>/dev/null || true)
if [[ -n "$DOMAIN" ]]; then
  echo ""
  echo "Public URL: https://${DOMAIN}"
  echo "  Dashboard:  https://${DOMAIN}/"
  echo "  Bot chat:   https://${DOMAIN}/bot"
  echo "  Health:     https://${DOMAIN}/health"
fi

print_env_guide

echo "Tip: nightly re-analysis — add a Railway Cron service or use:"
echo "  railway run python scripts/run_daily_analysis.py"
