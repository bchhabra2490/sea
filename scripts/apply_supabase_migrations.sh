#!/usr/bin/env bash
# Apply supabase/migrations to a linked Supabase project.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v supabase >/dev/null 2>&1; then
  echo "Install Supabase CLI: https://supabase.com/docs/guides/cli" >&2
  exit 1
fi

echo "==> Pushing migrations from supabase/migrations/"
supabase db push

echo "==> Done. Verify tables in Dashboard → Database → Tables"
echo "    Storage bucket: proofs"
