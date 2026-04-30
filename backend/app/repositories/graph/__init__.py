"""Graph backend abstractions and implementations.

Public entry point: `get_graph_backend()` from .factory, which honours
Config.GRAPH_BACKEND (zep | postgres) and returns a `GraphBackend`.

Default is `zep` so the existing flow keeps working unchanged. The
`postgres` backend is a Phase 0 skeleton; concrete methods raise
NotImplementedError until Fases 1-7 land.
"""

from .protocol import GraphBackend
from .factory import get_graph_backend

__all__ = ["GraphBackend", "get_graph_backend"]
