"""Unit tests for catalog CRUD endpoints:
    GET  /api/search-catalog
    POST /create-course
    POST /update-course
    POST /delete-course
"""

import json
import pytest
from tests.conftest import _FakeResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _post_json(client, url, payload):
    """Send a POST with JSON body and return the response."""
    return client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
    )


def _fake_execute_factory(overrides: dict | None = None):
    """Build a replacement ``db.session.execute`` that merges *overrides*
    into the default _FakeSession behaviour.

    *overrides* maps a SQL substring (lower-cased) to a ``_FakeResult``.
    The first matching substring wins.
    """
    overrides = overrides or {}

    def _execute(statement, params=None):
        sql = str(statement).lower()
        for pattern, result in overrides.items():
            if pattern in sql:
                return result
        # fall through: generic empty result
        return _FakeResult(rows=[], rowcount=0)

    return _execute


# ===================================================================
# Route registration
# ===================================================================

class TestCatalogCrudRouteRegistration:
    """Verify that all four catalog-CRUD routes are registered."""

    def test_search_catalog_route_registered(self, app):
        """GET /api/search-catalog must be a registered route."""
        rules = {r.rule for r in app.url_map.iter_rules()}
        assert "/api/search-catalog" in rules

    def test_search_catalog_allows_get(self, app):
        """The /api/search-catalog endpoint must accept GET."""
        for rule in app.url_map.iter_rules():
            if rule.rule == "/api/search-catalog":
                assert "GET" in rule.methods
                break

    def test_create_course_route_registered(self, app):
        """POST /create-course must be a registered route."""
        rules = {r.rule for r in app.url_map.iter_rules()}
        assert "/create-course" in rules

    def test_create_course_allows_post(self, app):
        """The /create-course endpoint must accept POST."""
        for rule in app.url_map.iter_rules():
            if rule.rule == "/create-course":
                assert "POST" in rule.methods
                break

    def test_update_course_route_registered(self, app):
        """POST /update-course must be a registered route."""
        rules = {r.rule for r in app.url_map.iter_rules()}
        assert "/update-course" in rules

    def test_update_course_allows_post(self, app):
        """The /update-course endpoint must accept POST."""
        for rule in app.url_map.iter_rules():
            if rule.rule == "/update-course":
                assert "POST" in rule.methods
                break

    def test_delete_course_route_registered(self, app):
        """POST /delete-course must be a registered route."""
        rules = {r.rule for r in app.url_map.iter_rules()}
        assert "/delete-course" in rules

    def test_delete_course_allows_post(self, app):
        """The /delete-course endpoint must accept POST."""
        for rule in app.url_map.iter_rules():
            if rule.rule == "/delete-course":
                assert "POST" in rule.methods
                break


# ===================================================================
# GET /api/search-catalog
# ===================================================================

class TestSearchCatalog:
    """Tests for the catalog autocomplete search endpoint."""

    def test_missing_q_returns_empty_list(self, client):
        """When the 'q' param is absent the endpoint returns []."""
        res = client.get("/api/search-catalog")
        assert res.status_code == 200
        assert res.content_type == "application/json"
        data = json.loads(res.get_data(as_text=True))
        assert data == []

    def test_short_q_returns_empty_list(self, client):
        """A single-character query should return [] (min 2 chars)."""
        res = client.get("/api/search-catalog?q=C")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert data == []

    def test_empty_q_returns_empty_list(self, client):
        """An empty string query should return []."""
        res = client.get("/api/search-catalog?q=")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert data == []

    def test_whitespace_only_q_returns_empty_list(self, client):
        """A whitespace-only query should return [] after strip()."""
        res = client.get("/api/search-catalog?q=%20%20")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert data == []

    def test_valid_query_returns_json_array(self, client, monkeypatch):
        """A valid 2+ char query returns a JSON array."""
        from app import db

        fake_rows = [
            {
                "subject": "COEN",
                "catalog": "352",
                "title": "VLSI Design",
                "classunit": "3.50",
            }
        ]
        exe = _fake_execute_factory({"from catalog": _FakeResult(rows=fake_rows)})
        monkeypatch.setattr(db.session, "execute", exe)

        res = client.get("/api/search-catalog?q=COEN")
        assert res.status_code == 200
        assert res.content_type == "application/json"
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, list)
        assert len(data) == 1

    def test_response_objects_have_required_fields(self, client, monkeypatch):
        """Each result must contain subject, catalog, title, classunit."""
        from app import db

        fake_rows = [
            {
                "subject": "COMP",
                "catalog": "248",
                "title": "Object-Oriented Programming",
                "classunit": "3.75",
            },
            {
                "subject": "COMP",
                "catalog": "352",
                "title": "Database Systems",
                "classunit": "4.00",
            },
        ]
        exe = _fake_execute_factory({"from catalog": _FakeResult(rows=fake_rows)})
        monkeypatch.setattr(db.session, "execute", exe)

        res = client.get("/api/search-catalog?q=COMP")
        data = json.loads(res.get_data(as_text=True))
        assert len(data) == 2
        for item in data:
            assert "subject" in item
            assert "catalog" in item
            assert "title" in item
            assert "classunit" in item

    def test_valid_query_no_results_returns_empty_list(self, client):
        """A valid query that matches nothing returns []."""
        res = client.get("/api/search-catalog?q=ZZZZ999")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert data == []

    def test_content_type_is_json(self, client):
        """Response Content-Type should always be application/json."""
        res = client.get("/api/search-catalog?q=EN")
        assert res.content_type == "application/json"


# ===================================================================
# POST /create-course
# ===================================================================

class TestCreateCourse:
    """Tests for adding a course to a sequence term."""

    def test_missing_termid_returns_400(self, client):
        """Omitting termid should yield a 400."""
        res = _post_json(client, "/create-course", {
            "subject": "COEN",
            "catalog": "352",
        })
        assert res.status_code == 400
        data = json.loads(res.get_data(as_text=True))
        assert "error" in data

    def test_missing_subject_returns_400(self, client):
        """Omitting subject should yield a 400."""
        res = _post_json(client, "/create-course", {
            "termid": 1,
            "catalog": "352",
        })
        assert res.status_code == 400
        data = json.loads(res.get_data(as_text=True))
        assert "error" in data

    def test_missing_catalog_returns_400(self, client):
        """Omitting catalog should yield a 400."""
        res = _post_json(client, "/create-course", {
            "termid": 1,
            "subject": "COEN",
        })
        assert res.status_code == 400
        data = json.loads(res.get_data(as_text=True))
        assert "error" in data

    def test_empty_body_returns_400(self, client):
        """A completely empty payload should yield 400."""
        res = _post_json(client, "/create-course", {})
        assert res.status_code == 400

    def test_term_not_found_returns_404(self, client):
        """If the sequence term doesn't exist, expect 404."""
        # Default _FakeSession returns empty rows for sequenceterm queries,
        # so the term-existence check fails.
        res = _post_json(client, "/create-course", {
            "termid": 999,
            "subject": "COEN",
            "catalog": "352",
        })
        assert res.status_code == 404
        data = json.loads(res.get_data(as_text=True))
        assert "not found" in data["error"].lower()

    def test_course_not_in_catalog_returns_404(self, client, monkeypatch):
        """If the course is not in the UGRD catalog, expect 404."""
        from app import db

        exe = _fake_execute_factory({
            # Term exists
            "from sequenceterm": _FakeResult(rows=[{"sequencetermid": 1}]),
            # Catalog lookup returns nothing
            "from catalog": _FakeResult(rows=[]),
        })
        monkeypatch.setattr(db.session, "execute", exe)

        res = _post_json(client, "/create-course", {
            "termid": 1,
            "subject": "FAKE",
            "catalog": "000",
        })
        assert res.status_code == 404
        data = json.loads(res.get_data(as_text=True))
        assert "not found" in data["error"].lower()

    def test_duplicate_course_returns_409(self, client, monkeypatch):
        """If the course already exists in the term, expect 409."""
        from app import db

        exe = _fake_execute_factory({
            "from sequenceterm": _FakeResult(rows=[{"sequencetermid": 1}]),
            "from catalog": _FakeResult(rows=[{"subject": "COEN", "catalog": "352"}]),
            "from sequencecourse": _FakeResult(rows=[{"1": 1}]),
        })
        monkeypatch.setattr(db.session, "execute", exe)

        res = _post_json(client, "/create-course", {
            "termid": 1,
            "subject": "COEN",
            "catalog": "352",
        })
        assert res.status_code == 409
        data = json.loads(res.get_data(as_text=True))
        assert "already exists" in data["error"].lower()

    def test_successful_create_returns_201(self, client, monkeypatch):
        """A valid create should return 201 with a success message."""
        from app import db

        call_log = []

        def _execute(statement, params=None):
            sql = str(statement).lower()
            call_log.append(sql)
            if "from sequenceterm" in sql:
                return _FakeResult(rows=[{"sequencetermid": 1}])
            if "from catalog" in sql:
                return _FakeResult(rows=[{"subject": "COEN", "catalog": "352"}])
            if "from sequencecourse" in sql:
                return _FakeResult(rows=[])  # no duplicate
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", _execute)

        res = _post_json(client, "/create-course", {
            "termid": 1,
            "subject": "COEN",
            "catalog": "352",
        })
        assert res.status_code == 201
        data = json.loads(res.get_data(as_text=True))
        assert "message" in data
        assert "COEN" in data["message"]
        assert "352" in data["message"]

    def test_successful_create_with_elective_flag(self, client, monkeypatch):
        """Creating a course with iselective=true should succeed."""
        from app import db

        def _execute(statement, params=None):
            sql = str(statement).lower()
            if "from sequenceterm" in sql:
                return _FakeResult(rows=[{"sequencetermid": 1}])
            if "from catalog" in sql:
                return _FakeResult(rows=[{"subject": "ELEC", "catalog": "275"}])
            if "from sequencecourse" in sql:
                return _FakeResult(rows=[])
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", _execute)

        res = _post_json(client, "/create-course", {
            "termid": 1,
            "subject": "ELEC",
            "catalog": "275",
            "iselective": True,
        })
        assert res.status_code == 201

    def test_create_response_content_type_is_json(self, client):
        """All responses must be application/json."""
        res = _post_json(client, "/create-course", {})
        assert res.content_type == "application/json"

    def test_subject_is_uppercased(self, client, monkeypatch):
        """Lowercase subject should be uppercased by the endpoint."""
        from app import db

        captured_params = []

        def _execute(statement, params=None):
            sql = str(statement).lower()
            if params:
                captured_params.append(params)
            if "from sequenceterm" in sql:
                return _FakeResult(rows=[{"sequencetermid": 1}])
            if "from catalog" in sql:
                return _FakeResult(rows=[{"subject": "COEN", "catalog": "352"}])
            if "from sequencecourse" in sql:
                return _FakeResult(rows=[])
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", _execute)

        res = _post_json(client, "/create-course", {
            "termid": 1,
            "subject": "coen",
            "catalog": "352",
        })
        assert res.status_code == 201
        # The catalog-check params should have the uppercased subject
        catalog_params = [p for p in captured_params if "s" in p and p.get("s") == "COEN"]
        assert len(catalog_params) > 0


# ===================================================================
# POST /update-course
# ===================================================================

class TestUpdateCourse:
    """Tests for updating a course with cascading."""

    def test_missing_old_subject_returns_400(self, client):
        """Omitting old_subject should yield 400."""
        res = _post_json(client, "/update-course", {
            "old_catalog": "352",
            "old_termid": 1,
            "new_subject": "COMP",
            "new_catalog": "248",
        })
        assert res.status_code == 400
        data = json.loads(res.get_data(as_text=True))
        assert "error" in data

    def test_missing_old_catalog_returns_400(self, client):
        """Omitting old_catalog should yield 400."""
        res = _post_json(client, "/update-course", {
            "old_subject": "COEN",
            "old_termid": 1,
            "new_subject": "COMP",
            "new_catalog": "248",
        })
        assert res.status_code == 400

    def test_missing_old_termid_returns_400(self, client):
        """Omitting old_termid should yield 400."""
        res = _post_json(client, "/update-course", {
            "old_subject": "COEN",
            "old_catalog": "352",
            "new_subject": "COMP",
            "new_catalog": "248",
        })
        assert res.status_code == 400

    def test_missing_new_subject_returns_400(self, client):
        """Omitting new_subject should yield 400."""
        res = _post_json(client, "/update-course", {
            "old_subject": "COEN",
            "old_catalog": "352",
            "old_termid": 1,
            "new_catalog": "248",
        })
        assert res.status_code == 400

    def test_missing_new_catalog_returns_400(self, client):
        """Omitting new_catalog should yield 400."""
        res = _post_json(client, "/update-course", {
            "old_subject": "COEN",
            "old_catalog": "352",
            "old_termid": 1,
            "new_subject": "COMP",
        })
        assert res.status_code == 400

    def test_original_course_not_found_returns_404(self, client):
        """If the original course isn't in sequencecourse, expect 404."""
        # Default _FakeSession returns empty for sequencecourse queries
        res = _post_json(client, "/update-course", {
            "old_subject": "COEN",
            "old_catalog": "352",
            "old_termid": 1,
            "new_subject": "COMP",
            "new_catalog": "248",
        })
        assert res.status_code == 404
        data = json.loads(res.get_data(as_text=True))
        assert "not found" in data["error"].lower()

    def test_new_course_not_in_catalog_returns_404(self, client, monkeypatch):
        """If the new course doesn't exist in the catalog, expect 404."""
        from app import db

        exe = _fake_execute_factory({
            "from sequencecourse": _FakeResult(rows=[{"1": 1}]),
            "from catalog": _FakeResult(rows=[]),
        })
        monkeypatch.setattr(db.session, "execute", exe)

        res = _post_json(client, "/update-course", {
            "old_subject": "COEN",
            "old_catalog": "352",
            "old_termid": 1,
            "new_subject": "FAKE",
            "new_catalog": "000",
        })
        assert res.status_code == 404
        data = json.loads(res.get_data(as_text=True))
        assert "not found" in data["error"].lower()

    def test_successful_course_change_returns_200(self, client, monkeypatch):
        """A valid course-change update should return 200 with cascade info."""
        from app import db

        def _execute(statement, params=None):
            sql = str(statement).lower()
            if "from sequencecourse" in sql:
                return _FakeResult(rows=[{"1": 1}])
            if "from catalog" in sql:
                return _FakeResult(rows=[{"subject": "COMP", "catalog": "248"}])
            if sql.strip().startswith("update"):
                return _FakeResult(rows=[], rowcount=2)
            if sql.strip().startswith("delete"):
                return _FakeResult(rows=[], rowcount=1)
            if sql.strip().startswith("insert"):
                return _FakeResult(rows=[])
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", _execute)

        res = _post_json(client, "/update-course", {
            "old_subject": "COEN",
            "old_catalog": "352",
            "old_termid": 1,
            "new_subject": "COMP",
            "new_catalog": "248",
        })
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert "message" in data
        assert "cascaded" in data
        assert isinstance(data["cascaded"], list)

    def test_elective_only_update_returns_200(self, client, monkeypatch):
        """Changing only iselective (same course) should skip catalog validation."""
        from app import db

        catalog_checked = []

        def _execute(statement, params=None):
            sql = str(statement).lower()
            if "from catalog" in sql:
                catalog_checked.append(True)
                return _FakeResult(rows=[])
            if "from sequencecourse" in sql:
                return _FakeResult(rows=[{"1": 1}])
            if sql.strip().startswith("delete"):
                return _FakeResult(rows=[], rowcount=1)
            if sql.strip().startswith("insert"):
                return _FakeResult(rows=[])
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", _execute)

        res = _post_json(client, "/update-course", {
            "old_subject": "COEN",
            "old_catalog": "352",
            "old_termid": 1,
            "new_subject": "COEN",
            "new_catalog": "352",
            "iselective": True,
        })
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert "message" in data
        # Catalog should NOT be checked when course identity hasn't changed
        assert len(catalog_checked) == 0

    def test_cascade_includes_table_names(self, client, monkeypatch):
        """When rows are updated in cascade tables, their names appear."""
        from app import db

        def _execute(statement, params=None):
            sql = str(statement).lower()
            if "from sequencecourse" in sql:
                return _FakeResult(rows=[{"1": 1}])
            if "from catalog" in sql:
                return _FakeResult(rows=[{"subject": "COMP", "catalog": "248"}])
            if sql.strip().startswith("update"):
                # Simulate rows being updated in cascaded tables
                return _FakeResult(rows=[], rowcount=3)
            if sql.strip().startswith("delete"):
                return _FakeResult(rows=[], rowcount=1)
            if sql.strip().startswith("insert"):
                return _FakeResult(rows=[])
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", _execute)

        res = _post_json(client, "/update-course", {
            "old_subject": "COEN",
            "old_catalog": "352",
            "old_termid": 1,
            "new_subject": "COMP",
            "new_catalog": "248",
        })
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        # Each cascade target with rowcount > 0 should appear
        assert len(data["cascaded"]) > 0
        # Format is "tablename(count)"
        for entry in data["cascaded"]:
            assert "(" in entry and ")" in entry

    def test_no_cascade_when_same_course(self, client, monkeypatch):
        """Updating without changing subject/catalog should yield empty cascade."""
        from app import db

        update_called = []

        def _execute(statement, params=None):
            sql = str(statement).lower()
            if sql.strip().startswith("update"):
                update_called.append(sql)
                return _FakeResult(rows=[], rowcount=0)
            if "from sequencecourse" in sql:
                return _FakeResult(rows=[{"1": 1}])
            if sql.strip().startswith("delete"):
                return _FakeResult(rows=[], rowcount=1)
            if sql.strip().startswith("insert"):
                return _FakeResult(rows=[])
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", _execute)

        res = _post_json(client, "/update-course", {
            "old_subject": "COEN",
            "old_catalog": "352",
            "old_termid": 1,
            "new_subject": "COEN",
            "new_catalog": "352",
        })
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        # No UPDATE statements should have been issued (course_changed is False)
        assert len(update_called) == 0
        assert data["cascaded"] == []

    def test_update_response_content_type_is_json(self, client):
        """All responses must be application/json."""
        res = _post_json(client, "/update-course", {})
        assert res.content_type == "application/json"

    def test_update_message_contains_arrow(self, client, monkeypatch):
        """Success message should show old -> new course."""
        from app import db

        def _execute(statement, params=None):
            sql = str(statement).lower()
            if "from sequencecourse" in sql:
                return _FakeResult(rows=[{"1": 1}])
            if "from catalog" in sql:
                return _FakeResult(rows=[{"subject": "COMP", "catalog": "248"}])
            if sql.strip().startswith("update"):
                return _FakeResult(rows=[], rowcount=0)
            if sql.strip().startswith("delete"):
                return _FakeResult(rows=[], rowcount=1)
            if sql.strip().startswith("insert"):
                return _FakeResult(rows=[])
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", _execute)

        res = _post_json(client, "/update-course", {
            "old_subject": "COEN",
            "old_catalog": "352",
            "old_termid": 1,
            "new_subject": "COMP",
            "new_catalog": "248",
        })
        data = json.loads(res.get_data(as_text=True))
        # The message uses the unicode arrow →
        assert "\u2192" in data["message"] or "->" in data["message"]


# ===================================================================
# POST /delete-course
# ===================================================================

class TestDeleteCourse:
    """Tests for deleting a course from a sequence term."""

    def test_missing_subject_returns_400(self, client):
        """Omitting subject should yield 400."""
        res = _post_json(client, "/delete-course", {
            "catalog": "352",
            "termid": 1,
        })
        assert res.status_code == 400
        data = json.loads(res.get_data(as_text=True))
        assert "error" in data

    def test_missing_catalog_returns_400(self, client):
        """Omitting catalog should yield 400."""
        res = _post_json(client, "/delete-course", {
            "subject": "COEN",
            "termid": 1,
        })
        assert res.status_code == 400

    def test_missing_termid_returns_400(self, client):
        """Omitting termid should yield 400."""
        res = _post_json(client, "/delete-course", {
            "subject": "COEN",
            "catalog": "352",
        })
        assert res.status_code == 400

    def test_empty_body_returns_400(self, client):
        """An empty JSON body should yield 400."""
        res = _post_json(client, "/delete-course", {})
        assert res.status_code == 400

    def test_successful_delete_returns_200(self, client, monkeypatch):
        """A valid delete should return 200 with a message."""
        from app import db

        def _execute(statement, params=None):
            sql = str(statement).lower()
            if sql.strip().startswith("delete"):
                return _FakeResult(rows=[], rowcount=1)
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", _execute)

        res = _post_json(client, "/delete-course", {
            "subject": "COEN",
            "catalog": "352",
            "termid": 1,
        })
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert "message" in data

    def test_delete_message_includes_count(self, client, monkeypatch):
        """The response message should mention how many rows were deleted."""
        from app import db

        def _execute(statement, params=None):
            sql = str(statement).lower()
            if sql.strip().startswith("delete"):
                return _FakeResult(rows=[], rowcount=1)
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", _execute)

        res = _post_json(client, "/delete-course", {
            "subject": "COEN",
            "catalog": "352",
            "termid": 1,
        })
        data = json.loads(res.get_data(as_text=True))
        assert "1" in data["message"]

    def test_delete_nonexistent_course_returns_200(self, client, monkeypatch):
        """Deleting a course that doesn't exist still returns 200 (0 rows)."""
        from app import db

        def _execute(statement, params=None):
            return _FakeResult(rows=[], rowcount=0)

        monkeypatch.setattr(db.session, "execute", _execute)

        res = _post_json(client, "/delete-course", {
            "subject": "ZZZZ",
            "catalog": "000",
            "termid": 999,
        })
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert "0" in data["message"]

    def test_delete_response_content_type_is_json(self, client):
        """All responses must be application/json."""
        res = _post_json(client, "/delete-course", {})
        assert res.content_type == "application/json"

    def test_delete_returns_json_response(self, client, monkeypatch):
        """The response body should be valid JSON regardless of outcome."""
        from app import db

        def _execute(statement, params=None):
            return _FakeResult(rows=[], rowcount=0)

        monkeypatch.setattr(db.session, "execute", _execute)

        res = _post_json(client, "/delete-course", {
            "subject": "COEN",
            "catalog": "352",
            "termid": 1,
        })
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, dict)


# ===================================================================
# Error-handling / edge cases
# ===================================================================

class TestCatalogCrudEdgeCases:
    """Edge-case and error-handling tests across endpoints."""

    def test_create_course_db_error_returns_500(self, client, monkeypatch):
        """A database exception during create should return 500."""
        from app import db

        def _execute(statement, params=None):
            sql = str(statement).lower()
            if "from sequenceterm" in sql:
                return _FakeResult(rows=[{"sequencetermid": 1}])
            if "from catalog" in sql:
                return _FakeResult(rows=[{"subject": "COEN", "catalog": "352"}])
            if "from sequencecourse" in sql:
                return _FakeResult(rows=[])
            if sql.strip().startswith("insert"):
                raise RuntimeError("simulated DB failure")
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", _execute)

        res = _post_json(client, "/create-course", {
            "termid": 1,
            "subject": "COEN",
            "catalog": "352",
        })
        assert res.status_code == 500
        data = json.loads(res.get_data(as_text=True))
        assert "error" in data

    def test_update_course_db_error_returns_500(self, client, monkeypatch):
        """A database exception during update should return 500."""
        from app import db

        def _execute(statement, params=None):
            sql = str(statement).lower()
            if "from sequencecourse" in sql:
                return _FakeResult(rows=[{"1": 1}])
            if "from catalog" in sql:
                return _FakeResult(rows=[{"subject": "COMP", "catalog": "248"}])
            if sql.strip().startswith("update"):
                raise RuntimeError("simulated DB failure")
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", _execute)

        res = _post_json(client, "/update-course", {
            "old_subject": "COEN",
            "old_catalog": "352",
            "old_termid": 1,
            "new_subject": "COMP",
            "new_catalog": "248",
        })
        assert res.status_code == 500
        data = json.loads(res.get_data(as_text=True))
        assert "error" in data

    def test_delete_course_db_error_returns_500(self, client, monkeypatch):
        """A database exception during delete should return 500."""
        from app import db

        def _execute(statement, params=None):
            raise RuntimeError("simulated DB failure")

        monkeypatch.setattr(db.session, "execute", _execute)

        res = _post_json(client, "/delete-course", {
            "subject": "COEN",
            "catalog": "352",
            "termid": 1,
        })
        assert res.status_code == 500
        data = json.loads(res.get_data(as_text=True))
        assert "error" in data

    def test_search_catalog_two_char_boundary(self, client, monkeypatch):
        """Exactly 2 characters should trigger a real query, not []."""
        from app import db

        query_executed = []

        def _execute(statement, params=None):
            sql = str(statement).lower()
            if "from catalog" in sql:
                query_executed.append(True)
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", _execute)

        res = client.get("/api/search-catalog?q=CO")
        assert res.status_code == 200
        assert len(query_executed) == 1  # query was actually issued

    def test_create_course_strips_subject_whitespace(self, client, monkeypatch):
        """Leading/trailing whitespace in subject should be stripped."""
        from app import db

        captured = []

        def _execute(statement, params=None):
            sql = str(statement).lower()
            if params:
                captured.append(params)
            if "from sequenceterm" in sql:
                return _FakeResult(rows=[{"sequencetermid": 1}])
            if "from catalog" in sql:
                return _FakeResult(rows=[{"subject": "COEN", "catalog": "352"}])
            if "from sequencecourse" in sql:
                return _FakeResult(rows=[])
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", _execute)

        res = _post_json(client, "/create-course", {
            "termid": 1,
            "subject": "  coen  ",
            "catalog": "352",
        })
        assert res.status_code == 201
        # Check that the subject was stripped and uppercased
        catalog_params = [p for p in captured if p.get("s") == "COEN"]
        assert len(catalog_params) > 0
