"""
Backend-agnostic Report Agent tool factory.

Returns a Zep- or Postgres-backed tools service depending on
Config.GRAPH_BACKEND. Both expose the same public surface used by
report_agent.py (insight_forge, panorama_search, quick_search,
get_graph_statistics, get_entity_summary, get_entities_by_type,
get_simulation_context, interview_agents).

interview_agents only has a real implementation on Zep today; the
Postgres tools service raises NotImplementedError for it. The
ReportAgent's `interview_agents` branch only runs when the user asks for
that capability, so the rest of the report still works on Postgres.
"""

from __future__ import annotations

from ..config import Config
from ..utils.logger import get_logger
# Re-export the legacy class for type-only callers.
from .zep_tools import ZepToolsService

__all__ = ["ZepToolsService", "get_graph_tools"]


_logger = get_logger("mirofish.graph_tools.factory")


def get_graph_tools():
    """Return the tools service matching Config.GRAPH_BACKEND.

    Not memoised — instances are cheap and we want hot-reload during dev
    to pick up flag changes. report_agent.py keeps its own per-agent
    reference once constructed.
    """
    backend = (Config.GRAPH_BACKEND or "zep").lower()
    if backend == "postgres":
        from .postgres_tools import PostgresToolsService
        _logger.debug("graph_tools factory -> PostgresToolsService")
        return PostgresToolsService()
    _logger.debug("graph_tools factory -> ZepToolsService")
    return ZepToolsService()
