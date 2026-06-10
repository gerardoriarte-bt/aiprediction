"""
Shared Flask-Limiter instance.

Import and call `limiter.init_app(app)` in the app factory.
Use `@limiter.limit(...)` on individual routes to set per-endpoint caps.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["200 per hour", "60 per minute"],
    strategy="fixed-window",
)
