import pytest
import sys
from pathlib import Path
from flask import Flask

# Ensure project root is importable in CI (so `backend` package resolves).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import ProductionConfig


def _make_app(secret_key=None, db_url=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    return app


def test_production_config_rejects_default_secret():
    app = _make_app("dev-secret-key", "sqlite:///tmp.db")
    with pytest.raises(RuntimeError, match="Unsafe SECRET_KEY"):
        ProductionConfig.init_app(app)


def test_production_config_requires_database_url():
    app = _make_app("very-strong-secret", None)
    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        ProductionConfig.init_app(app)


def test_production_config_sets_secure_cookie_flag():
    app = _make_app("very-strong-secret", "sqlite:///tmp.db")
    ProductionConfig.init_app(app)
    assert app.config["SESSION_COOKIE_SECURE"] is True

