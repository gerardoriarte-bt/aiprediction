"""
PostgresGraphMemoryUpdater — Phase 5 of the Zep -> Postgres migration.

Drop-in replacement for ZepGraphMemoryUpdater that persists agent activity
into Postgres+pgvector instead of Zep Cloud. The public API
(start/stop/add_activity/add_activity_from_dict/get_stats and the
BATCH_SIZE/SEND_INTERVAL/MAX_RETRIES knobs) matches ZepGraphMemoryUpdater
1:1 so simulation_runner.py can swap implementations through the
GraphMemoryManager factory without touching its loop.

Internally we batch activities per platform exactly like the Zep version,
but instead of calling `client.graph.add(...)` on each batch we delegate
to GraphIngestService (Phase 2) so each batch goes through:
    embed -> graph_chunks insert -> LLM extract -> upsert nodes/edges.
That way panorama_search/insight_forge see the new memory immediately.

We reuse the AgentActivity dataclass from zep_graph_memory_updater so
to_episode_text() output stays byte-identical.
"""

from __future__ import annotations

import threading
import time
from queue import Empty, Queue
from typing import Any, Dict, List, Optional

from ..repositories.graph import connection
from ..repositories.graph.errors import GraphNotFoundError
from ..repositories.graph.repos import GraphRepository
from ..utils.locale import get_locale, set_locale
from ..utils.logger import get_logger
# Reuse the dataclass and its locale-aware to_episode_text() so neither
# backend invents its own activity language.
from .zep_graph_memory_updater import AgentActivity


logger = get_logger("mirofish.postgres_graph_memory_updater")


class PostgresGraphMemoryUpdater:
    """Postgres memory updater (parity with ZepGraphMemoryUpdater)."""

    BATCH_SIZE = 5
    PLATFORM_DISPLAY_NAMES = {
        "twitter": "world-1",
        "reddit": "world-2",
    }
    SEND_INTERVAL = 0.5
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    def __init__(self, graph_id: str) -> None:
        self.graph_id = graph_id

        # Verify the target graph exists; surface misconfig early.
        with connection.get_pool().connection() as conn:
            if not GraphRepository.exists(conn, graph_id):
                raise GraphNotFoundError(graph_id)

        # Lazy import keeps boot-time cost low for callers who only run
        # the Zep flow.
        from .graph_ingest import GraphIngestService

        self._ingest = GraphIngestService()

        # Activity queue + per-platform buffers
        self._activity_queue: Queue = Queue()
        self._platform_buffers: Dict[str, List[AgentActivity]] = {
            "twitter": [],
            "reddit": [],
        }
        self._buffer_lock = threading.Lock()

        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

        self._total_activities = 0
        self._total_sent = 0
        self._total_items_sent = 0
        self._failed_count = 0
        self._skipped_count = 0

        logger.info(
            f"PostgresGraphMemoryUpdater initialised: graph_id={graph_id}, "
            f"batch_size={self.BATCH_SIZE}"
        )

    # ---- Public API (matches ZepGraphMemoryUpdater) ---------------------

    def start(self) -> None:
        if self._running:
            return
        current_locale = get_locale()
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            args=(current_locale,),
            daemon=True,
            name=f"PgMemoryUpdater-{self.graph_id[:8]}",
        )
        self._worker_thread.start()
        logger.info(f"PostgresGraphMemoryUpdater started: graph_id={self.graph_id}")

    def stop(self) -> None:
        self._running = False
        self._flush_remaining()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=10)
        logger.info(
            f"PostgresGraphMemoryUpdater stopped: graph_id={self.graph_id}, "
            f"total_activities={self._total_activities}, "
            f"batches_sent={self._total_sent}, "
            f"items_sent={self._total_items_sent}, "
            f"failed={self._failed_count}, "
            f"skipped={self._skipped_count}"
        )

    def add_activity(self, activity: AgentActivity) -> None:
        if activity.action_type == "DO_NOTHING":
            self._skipped_count += 1
            return
        self._activity_queue.put(activity)
        self._total_activities += 1
        logger.debug(
            f"queued activity: {activity.agent_name} - {activity.action_type}"
        )

    def add_activity_from_dict(self, data: Dict[str, Any], platform: str) -> None:
        if "event_type" in data:
            return
        from datetime import datetime as _dt

        activity = AgentActivity(
            platform=platform,
            agent_id=data.get("agent_id", 0),
            agent_name=data.get("agent_name", ""),
            action_type=data.get("action_type", ""),
            action_args=data.get("action_args", {}),
            round_num=data.get("round", 0),
            timestamp=data.get("timestamp", _dt.now().isoformat()),
        )
        self.add_activity(activity)

    def get_stats(self) -> Dict[str, Any]:
        with self._buffer_lock:
            buffer_sizes = {p: len(b) for p, b in self._platform_buffers.items()}
        return {
            "graph_id": self.graph_id,
            "backend": "postgres",
            "batch_size": self.BATCH_SIZE,
            "total_activities": self._total_activities,
            "batches_sent": self._total_sent,
            "items_sent": self._total_items_sent,
            "failed_count": self._failed_count,
            "skipped_count": self._skipped_count,
            "queue_size": self._activity_queue.qsize(),
            "buffer_sizes": buffer_sizes,
            "running": self._running,
        }

    # ---- Internals ------------------------------------------------------

    def _get_platform_display_name(self, platform: str) -> str:
        return self.PLATFORM_DISPLAY_NAMES.get(platform.lower(), platform)

    def _worker_loop(self, locale: str) -> None:
        set_locale(locale)
        while self._running or not self._activity_queue.empty():
            try:
                try:
                    activity = self._activity_queue.get(timeout=1)
                    platform = (activity.platform or "").lower()
                    with self._buffer_lock:
                        self._platform_buffers.setdefault(platform, []).append(activity)
                        if len(self._platform_buffers[platform]) >= self.BATCH_SIZE:
                            batch = self._platform_buffers[platform][: self.BATCH_SIZE]
                            self._platform_buffers[platform] = (
                                self._platform_buffers[platform][self.BATCH_SIZE :]
                            )
                            self._send_batch_activities(batch, platform)
                            time.sleep(self.SEND_INTERVAL)
                except Empty:
                    pass
            except Exception as e:
                logger.error(f"worker loop exception: {e}")
                time.sleep(1)

    def _flush_remaining(self) -> None:
        # Drain queue into buffers first.
        while not self._activity_queue.empty():
            try:
                activity = self._activity_queue.get_nowait()
                platform = (activity.platform or "").lower()
                with self._buffer_lock:
                    self._platform_buffers.setdefault(platform, []).append(activity)
            except Empty:
                break
        # Send whatever is left, even if below BATCH_SIZE.
        with self._buffer_lock:
            for platform, buffer in self._platform_buffers.items():
                if buffer:
                    display_name = self._get_platform_display_name(platform)
                    logger.info(
                        f"flushing {len(buffer)} remaining activities for {display_name}"
                    )
                    self._send_batch_activities(buffer, platform)
            for platform in self._platform_buffers:
                self._platform_buffers[platform] = []

    def _send_batch_activities(
        self, activities: List[AgentActivity], platform: str
    ) -> None:
        if not activities:
            return

        episode_texts = [a.to_episode_text() for a in activities]
        combined_text = "\n".join(episode_texts)

        # Pull the current ontology so the LLM extraction stays inside the
        # types defined for this graph.
        with connection.get_pool().connection() as conn:
            row = GraphRepository.get(conn, self.graph_id)
        if not row:
            logger.error(f"graph {self.graph_id} disappeared mid-run; aborting batch")
            self._failed_count += 1
            return
        ontology = row.get("ontology_json") or {}
        if isinstance(ontology, str):
            import json as _json
            try:
                ontology = _json.loads(ontology)
            except Exception:
                ontology = {}

        for attempt in range(self.MAX_RETRIES):
            try:
                self._ingest.ingest(
                    conn_factory=connection.get_pool().connection,
                    graph_id=self.graph_id,
                    chunks=[combined_text],
                    ontology=ontology,
                    progress_callback=None,
                )
                self._total_sent += 1
                self._total_items_sent += len(activities)
                display_name = self._get_platform_display_name(platform)
                logger.info(
                    f"persisted {len(activities)} {display_name} activities "
                    f"into postgres graph {self.graph_id}"
                )
                logger.debug(f"batch preview: {combined_text[:200]}...")
                return
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(
                        f"postgres ingest failed (attempt "
                        f"{attempt + 1}/{self.MAX_RETRIES}): {e}"
                    )
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(
                        f"postgres ingest failed after {self.MAX_RETRIES} attempts: {e}"
                    )
                    self._failed_count += 1
