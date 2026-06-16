"""
Simulation API package.

Re-exports simulation_bp from the parent api package and imports all
sub-modules so their routes are registered on the blueprint.
"""

from .. import simulation_bp  # noqa: F401

from . import entities       # noqa: F401
from . import lifecycle      # noqa: F401
from . import profiles       # noqa: F401
from . import execution      # noqa: F401
from . import results        # noqa: F401
from . import interview      # noqa: F401
from . import environment    # noqa: F401
