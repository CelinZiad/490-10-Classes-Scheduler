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


class _FakeResult:
    """Mimic SQLAlchemy Result for the small subset we use in app.py."""

    def __init__(self, rows=None, scalar_value=None):
        self._rows = rows or []
        self._scalar_value = scalar_value

    # Used by: .mappings().all()
    def mappings(self):
        return self

    def all(self):
        return self._rows

    # Used by: .scalars().all()
    def scalars(self):
        return self

    # Used by: .scalar()
    def scalar(self):
        return self._scalar_value


def _install_db_mocks(monkeypatch):
    """
    Patch db.session.execute/commit so API endpoints and pages don't crash in CI
    when Postgres isn't running.
    """

    def fake_execute(statement, params=None):
        sql = str(statement).lower()

        # /health/db
        if "select 1" in sql:
            return _FakeResult(scalar_value=1)

        # /api/events query
        if "from scheduleterm" in sql and "select distinct on" in sql:
            return _FakeResult(rows=[])

        # /api/filters terms query
        if "group by sch.termcode" in sql:
            return _FakeResult(rows=[])

        # /api/filters dropdowns
        if "select distinct sch.subject" in sql:
            return _FakeResult(rows=[])
        if "select distinct sch.componentcode" in sql:
            return _FakeResult(rows=[])
        if "select distinct sch.buildingcode" in sql:
            return _FakeResult(rows=[])

        # /api/filters plans list
        if "from sequenceplan" in sql and "select planid" in sql:
            return _FakeResult(rows=[])

        # /api/plans/<id>/terms
        if "from sequenceterm" in sql and "where planid" in sql:
            return _FakeResult(rows=[])

        # dashboard recent activity + activity page logs
        if "from activitylog" in sql:
            return _FakeResult(rows=[])

        # catalog page queries
        if "from sequenceplan" in sql:
            return _FakeResult(rows=[])
        if "from sequenceterm" in sql:
            return _FakeResult(rows=[])
        if "from sequencecourse" in sql:
            return _FakeResult(rows=[])

        # default: empty result
        return _FakeResult(rows=[])

    monkeypatch.setattr(db.session, "execute", fake_execute)
    monkeypatch.setattr(db.session, "commit", lambda: None)


@pytest.fixture()
def app(monkeypatch):
    flask_app.config.update(TESTING=True)

    # If DB isn't reachable (CI), mock it so endpoints still work.
    if not _db_reachable():
        _install_db_mocks(monkeypatch)

    return flask_app


@pytest.fixture()
def client(app, request):
    """
    Provide a test client.
    - If a test is marked @pytest.mark.integration, skip it when DB is not available.
    - Otherwise, always run (using real DB locally, mocks in CI).
    """
    if "integration" in [m.name for m in request.node.iter_markers()]:
        if not _db_reachable():
            pytest.skip("Database not reachable")
    return app.test_client()
