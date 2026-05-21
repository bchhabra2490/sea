"""Supabase/Postgres persistence for analysis pipeline and bot."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any
import numpy as np

from app.db.client import get_supabase_client
from app.db.schema import (
    ANALYSIS_RUNS,
    CLUSTER_ASSIGNMENTS,
    CLUSTER_CENTROIDS,
    CONVERSATIONS,
    DEFAULT_EMBEDDING_DIMENSION,
    EMBEDDINGS,
    MESSAGES,
    PROCESSED_TEXTS,
    RPC_MATCH_CLUSTER_CENTROIDS,
    TOPIC_LABELS,
)
from app.models.conversation import Conversation, Message, ProcessedConversation
from app.models.topic import ClusterAssignment, TopicLabel
from app.utils.config import Settings, get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

BATCH_UPSERT_CHUNK = 200
BATCH_INSERT_CHUNK = 500


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _vector_literal(vec: np.ndarray | list[float]) -> list[float]:
    if isinstance(vec, np.ndarray):
        return vec.astype(float).tolist()
    return list(vec)


class AnalysisRepository:
    """Read/write analysis data in Supabase Postgres."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = get_supabase_client()
        self.dim = self.settings.embedding_dimension or DEFAULT_EMBEDDING_DIMENSION

    # --- Analysis runs ---

    def resolve_run_id(self) -> str | None:
        """
        Find the analysis run to use for reads.

        Prefer is_current + completed; fall back to latest completed run,
        then the newest run referenced in cluster/topic tables (e.g. manual DB seed).
        """
        row = (
            self.client.table(ANALYSIS_RUNS)
            .select("id")
            .eq("is_current", True)
            .eq("status", "completed")
            .limit(1)
            .execute()
        )
        if row.data:
            return row.data[0]["id"]

        row = (
            self.client.table(ANALYSIS_RUNS)
            .select("id")
            .eq("status", "completed")
            .order("completed_at", desc=True)
            .limit(1)
            .execute()
        )
        if row.data:
            run_id = row.data[0]["id"]
            logger.info("Using latest completed analysis run %s (is_current not set)", run_id)
            return run_id

        for table in (TOPIC_LABELS, CLUSTER_ASSIGNMENTS, CLUSTER_CENTROIDS):
            row = self.client.table(table).select("analysis_run_id").order("created_at", desc=True).limit(1).execute()
            if row.data:
                run_id = row.data[0]["analysis_run_id"]
                logger.info("Resolved analysis run %s from %s", run_id, table)
                return run_id

        return None

    def has_current_analysis(self) -> bool:
        return self.resolve_run_id() is not None

    def get_current_run_id(self) -> str | None:
        return self.resolve_run_id()

    def clear_current_runs(self) -> None:
        self.client.table(ANALYSIS_RUNS).update({"is_current": False}).eq("is_current", True).execute()

    def create_run(
        self,
        input_source: str,
        storage_path: str | None = None,
        status: str = "running",
        stage: str = "queued",
    ) -> str:
        self.clear_current_runs()
        payload = {
            "status": status,
            "stage": stage,
            "progress_percent": 0,
            "message": "Pipeline started",
            "input_source": input_source,
            "storage_path": storage_path,
            "started_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
            "is_current": False,
        }
        row = self.client.table(ANALYSIS_RUNS).insert(payload).execute()
        return row.data[0]["id"]

    def update_run_progress(
        self,
        run_id: str,
        stage: str,
        message: str,
        progress_percent: int,
        status: str = "running",
    ) -> None:
        self.client.table(ANALYSIS_RUNS).update(
            {
                "stage": stage,
                "message": message,
                "progress_percent": progress_percent,
                "status": status,
                "updated_at": _utc_now_iso(),
            }
        ).eq("id", run_id).execute()

    def complete_run(
        self,
        run_id: str,
        conversations_processed: int,
        clusters_found: int,
        noise_points: int,
        topics_labeled: int,
        message: str = "Analysis completed successfully",
    ) -> None:
        now = _utc_now_iso()
        self.client.table(ANALYSIS_RUNS).update(
            {
                "status": "completed",
                "stage": "completed",
                "message": message,
                "progress_percent": 100,
                "conversations_processed": conversations_processed,
                "clusters_found": clusters_found,
                "noise_points": noise_points,
                "topics_labeled": topics_labeled,
                "completed_at": now,
                "updated_at": now,
                "is_current": True,
                "error": None,
            }
        ).eq("id", run_id).execute()

    def fail_run(self, run_id: str, error: str) -> None:
        now = _utc_now_iso()
        self.client.table(ANALYSIS_RUNS).update(
            {
                "status": "failed",
                "stage": "failed",
                "message": "Pipeline failed",
                "error": error,
                "completed_at": now,
                "updated_at": now,
                "is_current": False,
            }
        ).eq("id", run_id).execute()

    def get_run_for_status(self, run_id: str | None) -> dict | None:
        if run_id:
            row = self.client.table(ANALYSIS_RUNS).select("*").eq("id", run_id).limit(1).execute()
            return row.data[0] if row.data else None
        row = self.client.table(ANALYSIS_RUNS).select("*").order("created_at", desc=True).limit(1).execute()
        return row.data[0] if row.data else None

    # --- Conversations ---

    def upsert_conversations(
        self,
        raw: list[Conversation],
        source: str = "jsonl",
    ) -> dict[str, str]:
        """Insert/update conversations and messages; return external_id -> uuid."""
        if not raw:
            return {}

        now = _utc_now_iso()
        id_map: dict[str, str] = {}

        for start in range(0, len(raw), BATCH_UPSERT_CHUNK):
            chunk = raw[start : start + BATCH_UPSERT_CHUNK]
            payloads = [
                {
                    "external_id": conv.conversation_id,
                    "source": source,
                    "conversation_timestamp": conv.timestamp,
                    "updated_at": now,
                }
                for conv in chunk
            ]
            rows = self.client.table(CONVERSATIONS).upsert(payloads, on_conflict="external_id").execute()
            for row in rows.data or []:
                id_map[row["external_id"]] = row["id"]

        conv_uuids = list(id_map.values())
        if conv_uuids:
            self.client.table(MESSAGES).delete().in_("conversation_id", conv_uuids).execute()

        msg_rows: list[dict] = []
        for conv in raw:
            conv_uuid = id_map.get(conv.conversation_id)
            if not conv_uuid:
                continue
            msg_rows.extend(
                {
                    "conversation_id": conv_uuid,
                    "role": m.role,
                    "content": m.content,
                    "position": idx,
                }
                for idx, m in enumerate(conv.messages)
            )

        for start in range(0, len(msg_rows), BATCH_INSERT_CHUNK):
            batch = msg_rows[start : start + BATCH_INSERT_CHUNK]
            if batch:
                self.client.table(MESSAGES).insert(batch).execute()

        return id_map

    def load_all_conversations(self, page_size: int = 500) -> list[Conversation]:
        """Load every conversation and its messages from Supabase."""
        offset = 0
        all_rows: list[dict] = []

        while True:
            batch = (
                self.client.table(CONVERSATIONS)
                .select(f"external_id, conversation_timestamp, {MESSAGES}(role, content, position)")
                .order("created_at")
                .range(offset, offset + page_size - 1)
                .execute()
            )
            rows = batch.data or []
            if not rows:
                break
            all_rows.extend(rows)
            if len(rows) < page_size:
                break
            offset += page_size

        conversations: list[Conversation] = []
        for row in all_rows:
            msgs = sorted(row.get(MESSAGES) or [], key=lambda m: m["position"])
            ts = row.get("conversation_timestamp")
            conversations.append(
                Conversation(
                    conversation_id=row["external_id"],
                    messages=[Message(role=m["role"], content=m["content"]) for m in msgs],
                    timestamp=str(ts) if ts is not None else None,
                )
            )
        return conversations

    def upsert_bot_conversation(
        self,
        external_id: str,
        user_text: str,
        agent_text: str,
        timestamp: str | None = None,
    ) -> str:
        conv = Conversation(
            conversation_id=external_id,
            messages=[
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": agent_text},
            ],
            timestamp=timestamp,
        )
        return self.upsert_conversations([conv], source="bot")[external_id]

    # --- Pipeline artifacts per run ---

    def save_processed_texts(
        self,
        run_id: str,
        processed: list[ProcessedConversation],
        id_map: dict[str, str],
    ) -> None:
        rows = [
            {
                "conversation_id": id_map[p.conversation_id],
                "analysis_run_id": run_id,
                "text": p.text,
            }
            for p in processed
            if p.conversation_id in id_map
        ]
        if rows:
            self.client.table(PROCESSED_TEXTS).upsert(
                rows,
                on_conflict="conversation_id,analysis_run_id",
            ).execute()

    def save_embeddings(
        self,
        run_id: str,
        embeddings: np.ndarray,
        processed: list[ProcessedConversation],
        id_map: dict[str, str],
    ) -> None:
        rows = []
        for idx, proc in enumerate(processed):
            if proc.conversation_id not in id_map:
                continue
            rows.append(
                {
                    "conversation_id": id_map[proc.conversation_id],
                    "analysis_run_id": run_id,
                    "embedding": _vector_literal(embeddings[idx]),
                }
            )
        for chunk_start in range(0, len(rows), 100):
            chunk = rows[chunk_start : chunk_start + 100]
            self.client.table(EMBEDDINGS).upsert(
                chunk,
                on_conflict="conversation_id,analysis_run_id",
            ).execute()

    def save_cluster_assignments(
        self,
        run_id: str,
        processed: list[ProcessedConversation],
        labels: list[int],
        id_map: dict[str, str],
    ) -> None:
        rows = []
        for proc, label in zip(processed, labels, strict=True):
            if proc.conversation_id not in id_map:
                continue
            rows.append(
                {
                    "conversation_id": id_map[proc.conversation_id],
                    "analysis_run_id": run_id,
                    "cluster_id": int(label),
                    "processed_text": proc.text,
                }
            )
        if rows:
            self.client.table(CLUSTER_ASSIGNMENTS).upsert(
                rows,
                on_conflict="conversation_id,analysis_run_id",
            ).execute()

    def save_topic_labels(self, run_id: str, topics: list[TopicLabel]) -> None:
        rows = [
            {
                "analysis_run_id": run_id,
                "cluster_id": t.cluster_id,
                "topic": t.topic,
                "summary": t.summary,
                "severity": t.severity,
            }
            for t in topics
        ]
        if rows:
            self.client.table(TOPIC_LABELS).upsert(
                rows,
                on_conflict="analysis_run_id,cluster_id",
            ).execute()

    def save_cluster_centroids(
        self,
        run_id: str,
        embeddings: np.ndarray,
        processed: list[ProcessedConversation],
        labels: list[int],
        id_map: dict[str, str],
    ) -> None:
        """Compute mean embedding per cluster and persist centroids."""
        ext_to_idx = {p.conversation_id: i for i, p in enumerate(processed)}
        by_cluster: dict[int, list[int]] = {}
        for proc, label in zip(processed, labels, strict=True):
            if label < 0:
                continue
            idx = ext_to_idx.get(proc.conversation_id)
            if idx is None:
                continue
            by_cluster.setdefault(int(label), []).append(idx)

        rows = []
        for cluster_id, indices in by_cluster.items():
            vectors = embeddings[indices]
            centroid = vectors.mean(axis=0)
            rows.append(
                {
                    "analysis_run_id": run_id,
                    "cluster_id": cluster_id,
                    "centroid": _vector_literal(centroid),
                    "member_count": len(indices),
                }
            )
        if rows:
            self.client.table(CLUSTER_CENTROIDS).delete().eq("analysis_run_id", run_id).execute()
            self.client.table(CLUSTER_CENTROIDS).insert(rows).execute()

    # --- Reads for API ---

    def get_topics(self, run_id: str | None = None) -> list[TopicLabel]:
        run_id = run_id or self.get_current_run_id()
        if not run_id:
            return []
        rows = self.client.table(TOPIC_LABELS).select("*").eq("analysis_run_id", run_id).order("cluster_id").execute()
        return [
            TopicLabel(
                cluster_id=r["cluster_id"],
                topic=r["topic"],
                summary=r["summary"],
                severity=r["severity"],
            )
            for r in rows.data
        ]

    def get_cluster_assignments(
        self,
        run_id: str | None = None,
    ) -> tuple[list[ClusterAssignment], dict[str, int]]:
        run_id = run_id or self.get_current_run_id()
        if not run_id:
            return [], {}

        rows = (
            self.client.table(CLUSTER_ASSIGNMENTS)
            .select("cluster_id, processed_text, conversation_id")
            .eq("analysis_run_id", run_id)
            .execute()
        )
        if not rows.data:
            return [], {}

        conv_ids = list({r["conversation_id"] for r in rows.data if r.get("conversation_id")})
        ext_by_id: dict[str, str] = {}
        if conv_ids:
            conv_rows = self.client.table(CONVERSATIONS).select("id, external_id").in_("id", conv_ids).execute()
            ext_by_id = {c["id"]: c["external_id"] for c in conv_rows.data or []}

        assignments: list[ClusterAssignment] = []
        counts: Counter[int] = Counter()
        for r in rows.data:
            cid = int(r["cluster_id"])
            counts[cid] += 1
            conv_uuid = r.get("conversation_id")
            ext_id = ext_by_id.get(conv_uuid, str(conv_uuid) if conv_uuid else "unknown")
            assignments.append(
                ClusterAssignment(
                    conversation_id=ext_id,
                    cluster_id=cid,
                    text=r.get("processed_text"),
                )
            )
        return assignments, {str(k): v for k, v in counts.items()}

    def get_insights_summary(self, run_id: str | None = None) -> dict | None:
        run_id = run_id or self.get_current_run_id()
        if not run_id:
            return None

        topics = self.get_topics(run_id)
        _, counts = self.get_cluster_assignments(run_id)
        n_noise = counts.get("-1", 0)
        cluster_ids = {int(k) for k in counts if k != "-1"}

        row = self.client.table(ANALYSIS_RUNS).select("*").eq("id", run_id).limit(1).execute()
        if row.data:
            r = row.data[0]
            conv_processed = r.get("conversations_processed") or 0
            clusters_found = r.get("clusters_found") or 0
            noise_points = r.get("noise_points") or 0
            topics_labeled = r.get("topics_labeled") or 0
            if conv_processed or clusters_found or topics_labeled:
                return {
                    "conversations_processed": conv_processed,
                    "clusters_found": clusters_found,
                    "noise_points": noise_points,
                    "topics_labeled": topics_labeled,
                    "status": "ready",
                }

        return {
            "conversations_processed": sum(counts.values()) or len(topics),
            "clusters_found": len(cluster_ids) or len({t.cluster_id for t in topics}),
            "noise_points": n_noise,
            "topics_labeled": len(topics),
            "status": "ready",
        }

    # --- Bot: pgvector search ---

    def classify_message(
        self,
        message: str,
        processed_text: str,
        vector: np.ndarray,
        top_k: int = 3,
        min_similarity: float | None = None,
    ) -> dict:
        min_similarity = min_similarity if min_similarity is not None else self.settings.min_cluster_similarity
        run_id = self.get_current_run_id()
        if not run_id:
            raise ValueError("No completed analysis run in database")

        topics = {t.cluster_id: t for t in self.get_topics(run_id)}
        matches = self.client.rpc(
            RPC_MATCH_CLUSTER_CENTROIDS,
            {
                "query_embedding": _vector_literal(vector),
                "target_run_id": run_id,
                "match_count": top_k + 1,
            },
        ).execute()

        results = matches.data or []
        if not results:
            raise ValueError("No cluster centroids found for current run")

        def to_match(row: dict) -> dict:
            cid = int(row["cluster_id"])
            t = topics.get(cid)
            return {
                "cluster_id": cid,
                "similarity": round(float(row["similarity"]), 4),
                "topic": t.topic if t else None,
                "summary": t.summary if t else None,
                "severity": t.severity if t else None,
            }

        nearest = to_match(results[0])
        is_noise = nearest["similarity"] < min_similarity
        if is_noise:
            nearest = {
                **nearest,
                "cluster_id": -1,
                "topic": "Unclustered (low confidence)",
                "summary": (
                    f"Best match {(nearest['similarity'] * 100):.0f}% is below "
                    f"{min_similarity * 100:.0f}% threshold (unclustered)"
                ),
                "severity": None,
            }
        alternatives = [to_match(r) for r in results[1 : top_k + 1]]

        return {
            "message": message,
            "processed_text": processed_text,
            "nearest": nearest,
            "alternatives": alternatives,
            "is_noise": is_noise,
            "min_similarity": min_similarity,
            "run_id": run_id,
            "vector": vector,
        }

    def register_classified_message(
        self,
        run_id: str,
        external_id: str,
        user_text: str,
        processed_text: str,
        vector: np.ndarray,
        cluster_id: int,
        agent_text: str | None = None,
        timestamp: str | None = None,
    ) -> str:
        """Persist a bot turn: user message, optional assistant reply, embedding, and cluster."""
        messages = [Message(role="user", content=user_text)]
        if agent_text is not None:
            messages.append(Message(role="assistant", content=agent_text))

        conv = Conversation(
            conversation_id=external_id,
            messages=messages,
            timestamp=timestamp,
        )
        conv_uuid = self.upsert_conversations([conv], source="bot")[external_id]
        id_map = {external_id: conv_uuid}
        proc = ProcessedConversation(
            conversation_id=external_id,
            text=processed_text,
            timestamp=timestamp,
        )
        self.save_processed_texts(run_id, [proc], id_map)
        self.save_embeddings(run_id, vector.reshape(1, -1), [proc], id_map)
        self.save_cluster_assignments(run_id, [proc], [cluster_id], id_map)
        return conv_uuid

    def register_bot_message(
        self,
        run_id: str,
        external_id: str,
        user_text: str,
        agent_text: str,
        processed_text: str,
        vector: np.ndarray,
        cluster_id: int,
        timestamp: str | None = None,
    ) -> str:
        return self.register_classified_message(
            run_id,
            external_id,
            user_text,
            processed_text,
            vector,
            cluster_id,
            agent_text=agent_text,
            timestamp=timestamp,
        )

    def get_bot_history(self, limit: int = 50) -> list[dict]:
        rows = (
            self.client.table(CONVERSATIONS)
            .select(f"id, external_id, conversation_timestamp, {MESSAGES}(role, content, position)")
            .eq("source", "bot")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        items: list[dict] = []
        for r in reversed(rows.data or []):
            msgs = sorted(r.get(MESSAGES) or [], key=lambda m: m["position"])
            user_msg = next((m["content"] for m in msgs if m["role"] == "user"), "")
            agent_msg = next((m["content"] for m in msgs if m["role"] == "assistant"), "")
            items.append(
                {
                    "conversation_id": r["external_id"],
                    "timestamp": r.get("conversation_timestamp"),
                    "user_message": user_msg,
                    "agent_message": agent_msg,
                }
            )
        return items

    def cluster_count(self) -> int:
        run_id = self.get_current_run_id()
        if not run_id:
            return 0
        result = (
            self.client.table(CLUSTER_CENTROIDS).select("id", count="exact").eq("analysis_run_id", run_id).execute()
        )
        return result.count or len(result.data or [])

    def _delete_all_rows(self, table: str) -> int:
        """Delete every row in a table (PostgREST requires a filter)."""
        sentinel = "00000000-0000-0000-0000-000000000000"
        result = self.client.table(table).delete().neq("id", sentinel).execute()
        return len(result.data) if result.data else 0

    def reset_all_data(self) -> dict[str, int]:
        """
        Remove all conversations, messages, analysis runs, and cluster artifacts.

        Deletes in FK-safe order. Does not remove Storage bucket files.
        """
        deleted: dict[str, int] = {}
        order = [
            (MESSAGES, "messages"),
            (CLUSTER_ASSIGNMENTS, "cluster_assignments"),
            (PROCESSED_TEXTS, "processed_texts"),
            (EMBEDDINGS, "embeddings"),
            (TOPIC_LABELS, "topic_labels"),
            (CLUSTER_CENTROIDS, "cluster_centroids"),
            (ANALYSIS_RUNS, "analysis_runs"),
            (CONVERSATIONS, "conversations"),
        ]
        for table, label in order:
            count = self._delete_all_rows(table)
            deleted[label] = count
            if count:
                logger.info("Reset: deleted %d rows from %s", count, table)

        global _repo  # noqa: PLW0603
        _repo = None

        return deleted


_repo: AnalysisRepository | None = None


def get_repository() -> AnalysisRepository:
    global _repo  # noqa: PLW0603
    if _repo is None:
        _repo = AnalysisRepository()
    return _repo
