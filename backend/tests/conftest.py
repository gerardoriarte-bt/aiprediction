"""
Shared pytest fixtures.

Tests use the project venv (`backend/.venv`); run them with:
    cd backend && .venv/bin/pytest

The Flask app is *not* booted by default — only the modules under test are
imported, which keeps the suite fast and unaware of DATABASE_URL / Zep / etc.
Tests that need the app spin up their own minimal Flask via the
`flask_app` fixture below.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


# Make the `app` package importable from anywhere in the suite without
# relying on PYTHONPATH manipulations in the user's shell.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def flask_app():
    """A barebones Flask app with the report blueprint registered.

    Used by API-level tests so we exercise the full multipart parsing
    path without standing up the rest of the project.
    """
    from flask import Flask
    from app.api import report_bp
    from app.utils.limiter import limiter

    app = Flask(__name__)
    app.register_blueprint(report_bp, url_prefix="/api/report")
    app.config.update(TESTING=True, RATELIMIT_ENABLED=False)
    limiter.init_app(app)
    return app


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()
