import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")

import pytest  # noqa: E402
from app import app as flask_app, db  # noqa: E402


def _db_reachable() -> bool:
    """True if the database accepts connections."""
    try:
        with flask_app.app_context():
            db.session.execute(db.text("SELECT 1"))
        return True
    except Exception:
        return False


class _FakeResult:
    def __init__(self, rows=None, scalar_value=None):
        self._rows = rows or []
        self._scalar_value = scalar_value

    def mappings(self):
        return self

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def scalar(self):
        return self._scalar_value


class _FakeSession:
    def execute(self, statement, params=None):
        sql = str(statement).lower()

        # Used only by _db_reachable() when it runs under mocks (harmless)
        if "select 1" in sql:
            return _FakeResult(scalar_value=1)

        # /api/events
        if "from scheduleterm" in sql and "select distinct on" in sql:
            return _FakeResult(rows=[])

        # /api/filters: terms query
        if "group by sch.termcode" in sql:
            return _FakeResult(rows=[])

        # /api/filters dropdowns
        if "select distinct sch.subject" in sql:
            return _FakeResult(rows=[])
        if "select distinct sch.componentcode" in sql:
            return _FakeResult(rows=[])
        if "select distinct sch.buildingcode" in sql:
            return _FakeResult(rows=[])

        # /api/filters plans
        if "from sequenceplan" in sql and "select planid" in sql:
            return _FakeResult(rows=[])

        # /api/plans/<id>/terms
        if "from sequenceterm" in sql and "where planid" in sql:
            return _FakeResult(rows=[])

        # pages that query activitylog/catalog
        if "from activitylog" in sql:
            return _FakeResult(rows=[])
        if "from sequencecourse" in sql:
            return _FakeResult(rows=[])

        return _FakeResult(rows=[])

    def commit(self):
        return None

    def rollback(self):
        return None


def _install_db_mocks(monkeypatch):
    # Patch the whole session (more reliable than patching execute on scoped_session)
    monkeypatch.setattr(db, "session", _FakeSession())


@pytest.fixture()
def app(monkeypatch):
    flask_app.config.update(TESTING=True)

    # If DB isn't reachable (CI), mock it so endpoints still work.
    if not _db_reachable():
        _install_db_mocks(monkeypatch)

    return flask_app


@pytest.fixture()
def client(app, request):
    # Skip only tests explicitly marked "integration" when no DB exists
    if "integration" in [m.name for m in request.node.iter_markers()]:
        if not _db_reachable():
            pytest.skip("Database not reachable")
    return app.test_client()
