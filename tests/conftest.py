import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env first so real DB creds are available locally.
# In CI (no .env file), fall back to dummy values for import safety.
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")

import pytest  # noqa: E402
from app import app as flask_app, db  # noqa: E402


def _db_reachable() -> bool:
    """Return True if the database accepts connections."""
    try:
        with flask_app.app_context():
            db.session.execute(db.text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture()
def app():
    flask_app.config.update(TESTING=True)
    return flask_app


@pytest.fixture()
def client(app, request):
    """Provide a test client; skip integration tests when no DB is available."""
    if "integration" in [m.name for m in request.node.iter_markers()]:
        if not _db_reachable():
            pytest.skip("Database not reachable")
    return app.test_client()
