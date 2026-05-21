"""Table and RPC names matching supabase/migrations (se_ prefix)."""

# Tables
ANALYSIS_RUNS = "se_analysis_runs"
CONVERSATIONS = "se_conversations"
MESSAGES = "se_messages"
PROCESSED_TEXTS = "se_processed_texts"
EMBEDDINGS = "se_embeddings"
CLUSTER_ASSIGNMENTS = "se_cluster_assignments"
TOPIC_LABELS = "se_topic_labels"
CLUSTER_CENTROIDS = "se_cluster_centroids"

# Views
LATEST_INSIGHTS = "se_latest_insights"

# Storage
STORAGE_BUCKET_PROOFS = "proofs"

# RPCs
RPC_MATCH_CLUSTER_CENTROIDS = "se_match_cluster_centroids"
RPC_MATCH_CONVERSATION_EMBEDDINGS = "se_match_conversation_embeddings"

# Embedding vector size for text-embedding-3-small
DEFAULT_EMBEDDING_DIMENSION = 1536
