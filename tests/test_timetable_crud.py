"""Tests for timetable CRUD endpoints (optimized_schedule table).

Covers: /api/create-class, /api/update-class/<id>, /api/delete-class/<id>,
        /api/list-optimized, /api/optimized-date-range
"""
import json

import pytest
from app import db


# ── helpers ───────────────────────────────────────────────────────────

def _post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload),
                       content_type="application/json")


def _put_json(client, url, payload):
    return client.put(url, data=json.dumps(payload),
                      content_type="application/json")


class _FakeResult:
    def __init__(self, rows=None, scalar_value=None, rowcount=0):
        self._rows = rows or []
        self._scalar_value = scalar_value
        self.rowcount = rowcount

    def mappings(self):
        return self

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._scalar_value


def _fake_execute_factory(overrides=None):
    overrides = overrides or {}

    def _execute(statement, params=None):
        sql = str(statement).lower()
        for key, result in overrides.items():
            if key in sql:
                return result
        # Default: return empty result
        return _FakeResult(rows=[], rowcount=0)

    return _execute


VALID_CLASS = {
    "subject": "COEN",
    "catalog": "243",
    "section": "A",
    "component": "LEC",
    "day": "Monday",
    "startTime": "08:45",
    "endTime": "10:00",
    "building": "H",
    "room": "920",
    "enrollment": 50,
    "capacity": 100,
    "waitlist": 0,
    "waitlistCapacity": 10,
}


# ═══════════════════════════════════════════════════════════════════════
#  Route Registration
# ═══════════════════════════════════════════════════════════════════════

class TestTimetableCrudRoutes:

    def test_create_class_route_registered(self, app):
        rules = {r.rule for r in app.url_map.iter_rules()}
        assert "/api/create-class" in rules

    def test_update_class_route_registered(self, app):
        rules = {r.rule for r in app.url_map.iter_rules()}
        assert "/api/update-class/<int:class_id>" in rules

    def test_delete_class_route_registered(self, app):
        rules = {r.rule for r in app.url_map.iter_rules()}
        assert "/api/delete-class/<int:class_id>" in rules

    def test_list_optimized_route_registered(self, app):
        rules = {r.rule for r in app.url_map.iter_rules()}
        assert "/api/list-optimized" in rules

    def test_optimized_date_range_route_registered(self, app):
        rules = {r.rule for r in app.url_map.iter_rules()}
        assert "/api/optimized-date-range" in rules

    def test_create_class_is_post(self, app):
        rule = next(r for r in app.url_map.iter_rules()
                    if r.rule == "/api/create-class")
        assert "POST" in rule.methods

    def test_update_class_is_put(self, app):
        rule = next(r for r in app.url_map.iter_rules()
                    if r.rule == "/api/update-class/<int:class_id>")
        assert "PUT" in rule.methods

    def test_delete_class_is_delete(self, app):
        rule = next(r for r in app.url_map.iter_rules()
                    if r.rule == "/api/delete-class/<int:class_id>")
        assert "DELETE" in rule.methods


# ═══════════════════════════════════════════════════════════════════════
#  POST /api/create-class
# ═══════════════════════════════════════════════════════════════════════

class TestCreateClass:

    def test_create_success(self, client):
        resp = _post_json(client, "/api/create-class", VALID_CLASS)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "created"

    def test_create_returns_json(self, client):
        resp = _post_json(client, "/api/create-class", VALID_CLASS)
        assert resp.content_type.startswith("application/json")

    def test_create_monday_flag(self, client, monkeypatch):
        """Verify that day='Monday' sets the mondays param to True."""
        captured = {}

        def spy_execute(stmt, params=None):
            sql = str(stmt).lower()
            if "insert into optimized_schedule" in sql:
                captured.update(params or {})
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        _post_json(client, "/api/create-class", VALID_CLASS)
        assert captured.get("monday") is True
        assert captured.get("tuesday") is False

    def test_create_tuesday_flag(self, client, monkeypatch):
        payload = {**VALID_CLASS, "day": "Tuesday"}
        captured = {}

        def spy_execute(stmt, params=None):
            sql = str(stmt).lower()
            if "insert into optimized_schedule" in sql:
                captured.update(params or {})
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        _post_json(client, "/api/create-class", payload)
        assert captured.get("tuesday") is True
        assert captured.get("monday") is False

    def test_create_wednesday_flag(self, client, monkeypatch):
        payload = {**VALID_CLASS, "day": "Wednesday"}
        captured = {}

        def spy_execute(stmt, params=None):
            if "insert into optimized_schedule" in str(stmt).lower():
                captured.update(params or {})
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        _post_json(client, "/api/create-class", payload)
        assert captured.get("wednesday") is True

    def test_create_thursday_flag(self, client, monkeypatch):
        payload = {**VALID_CLASS, "day": "Thursday"}
        captured = {}

        def spy_execute(stmt, params=None):
            if "insert into optimized_schedule" in str(stmt).lower():
                captured.update(params or {})
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        _post_json(client, "/api/create-class", payload)
        assert captured.get("thursday") is True

    def test_create_friday_flag(self, client, monkeypatch):
        payload = {**VALID_CLASS, "day": "Friday"}
        captured = {}

        def spy_execute(stmt, params=None):
            if "insert into optimized_schedule" in str(stmt).lower():
                captured.update(params or {})
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        _post_json(client, "/api/create-class", payload)
        assert captured.get("friday") is True

    def test_create_time_format_fix(self, client, monkeypatch):
        """Backend should append :00 to HH:MM times."""
        captured = {}

        def spy_execute(stmt, params=None):
            if "insert into optimized_schedule" in str(stmt).lower():
                captured.update(params or {})
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        _post_json(client, "/api/create-class", VALID_CLASS)
        assert captured["startTime"] == "08:45:00"
        assert captured["endTime"] == "10:00:00"

    def test_create_already_correct_time(self, client, monkeypatch):
        """If time already has seconds, don't double-append."""
        payload = {**VALID_CLASS, "startTime": "08:45:00", "endTime": "10:00:00"}
        captured = {}

        def spy_execute(stmt, params=None):
            if "insert into optimized_schedule" in str(stmt).lower():
                captured.update(params or {})
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        _post_json(client, "/api/create-class", payload)
        assert captured["startTime"] == "08:45:00"

    def test_create_invalid_day_no_flag_set(self, client, monkeypatch):
        """An invalid day doesn't set any day flag."""
        payload = {**VALID_CLASS, "day": "NotADay"}
        captured = {}

        def spy_execute(stmt, params=None):
            if "insert into optimized_schedule" in str(stmt).lower():
                captured.update(params or {})
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        _post_json(client, "/api/create-class", payload)
        assert captured.get("monday") is False
        assert captured.get("tuesday") is False
        assert captured.get("wednesday") is False
        assert captured.get("thursday") is False
        assert captured.get("friday") is False

    def test_create_db_error_returns_500(self, client, monkeypatch):
        def raise_error(stmt, params=None):
            raise Exception("DB failure")

        monkeypatch.setattr(db.session, "execute", raise_error)
        resp = _post_json(client, "/api/create-class", VALID_CLASS)
        assert resp.status_code == 500
        assert "error" in resp.get_json()


# ═══════════════════════════════════════════════════════════════════════
#  PUT /api/update-class/<id>
# ═══════════════════════════════════════════════════════════════════════

class TestUpdateClass:

    def test_update_success(self, client):
        resp = _put_json(client, "/api/update-class/1", VALID_CLASS)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "success"

    def test_update_returns_json(self, client):
        resp = _put_json(client, "/api/update-class/1", VALID_CLASS)
        assert resp.content_type.startswith("application/json")

    def test_update_time_format_fix(self, client, monkeypatch):
        captured = {}

        def spy_execute(stmt, params=None):
            if "update optimized_schedule" in str(stmt).lower():
                captured.update(params or {})
            return _FakeResult(rows=[], rowcount=1)

        monkeypatch.setattr(db.session, "execute", spy_execute)
        _put_json(client, "/api/update-class/1", VALID_CLASS)
        assert captured["startTime"] == "08:45:00"
        assert captured["endTime"] == "10:00:00"

    def test_update_day_mapping(self, client, monkeypatch):
        payload = {**VALID_CLASS, "day": "Wednesday"}
        captured = {}

        def spy_execute(stmt, params=None):
            if "update optimized_schedule" in str(stmt).lower():
                captured.update(params or {})
            return _FakeResult(rows=[], rowcount=1)

        monkeypatch.setattr(db.session, "execute", spy_execute)
        _put_json(client, "/api/update-class/1", payload)
        assert captured["wednesday"] is True
        assert captured["monday"] is False
        assert captured["friday"] is False

    def test_update_no_day_all_false(self, client, monkeypatch):
        """When day is missing, all day flags should be False."""
        payload = {k: v for k, v in VALID_CLASS.items() if k != "day"}
        captured = {}

        def spy_execute(stmt, params=None):
            if "update optimized_schedule" in str(stmt).lower():
                captured.update(params or {})
            return _FakeResult(rows=[], rowcount=1)

        monkeypatch.setattr(db.session, "execute", spy_execute)
        _put_json(client, "/api/update-class/1", payload)
        for day in ("monday", "tuesday", "wednesday", "thursday", "friday"):
            assert captured[day] is False

    def test_update_sets_correct_id(self, client, monkeypatch):
        captured = {}

        def spy_execute(stmt, params=None):
            if "update optimized_schedule" in str(stmt).lower():
                captured.update(params or {})
            return _FakeResult(rows=[], rowcount=1)

        monkeypatch.setattr(db.session, "execute", spy_execute)
        _put_json(client, "/api/update-class/42", VALID_CLASS)
        assert captured["id"] == 42

    def test_update_db_error_returns_500(self, client, monkeypatch):
        def raise_error(stmt, params=None):
            raise Exception("DB failure")

        monkeypatch.setattr(db.session, "execute", raise_error)
        resp = _put_json(client, "/api/update-class/1", VALID_CLASS)
        assert resp.status_code == 500
        assert "error" in resp.get_json()


# ═══════════════════════════════════════════════════════════════════════
#  DELETE /api/delete-class/<id>
# ═══════════════════════════════════════════════════════════════════════

class TestDeleteClass:

    def test_delete_success(self, client):
        resp = client.delete("/api/delete-class/1")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "deleted"

    def test_delete_returns_json(self, client):
        resp = client.delete("/api/delete-class/1")
        assert resp.content_type.startswith("application/json")

    def test_delete_executes_correct_sql(self, client, monkeypatch):
        captured_sql = []

        def spy_execute(stmt, params=None):
            captured_sql.append(str(stmt).lower())
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        client.delete("/api/delete-class/99")
        assert any("delete from optimized_schedule" in s for s in captured_sql)

    def test_delete_passes_correct_id(self, client, monkeypatch):
        captured_params = {}

        def spy_execute(stmt, params=None):
            if "delete" in str(stmt).lower():
                captured_params.update(params or {})
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        client.delete("/api/delete-class/77")
        assert captured_params.get("id") == 77

    def test_delete_db_error_returns_500(self, client, monkeypatch):
        def raise_error(stmt, params=None):
            raise Exception("DB failure")

        monkeypatch.setattr(db.session, "execute", raise_error)
        resp = client.delete("/api/delete-class/1")
        assert resp.status_code == 500
        assert "error" in resp.get_json()


# ═══════════════════════════════════════════════════════════════════════
#  GET /api/list-optimized
# ═══════════════════════════════════════════════════════════════════════

class TestListOptimized:

    def test_list_returns_200(self, client):
        resp = client.get("/api/list-optimized")
        assert resp.status_code == 200

    def test_list_returns_json(self, client):
        resp = client.get("/api/list-optimized")
        assert resp.content_type.startswith("application/json")

    def test_list_returns_day_keys(self, client):
        resp = client.get("/api/list-optimized")
        data = resp.get_json()
        for day in ("Monday", "Tuesday", "Wednesday", "Thursday",
                     "Friday", "Saturday", "Sunday"):
            assert day in data

    def test_list_empty_result(self, client):
        resp = client.get("/api/list-optimized")
        data = resp.get_json()
        # With mock returning empty rows, all days should be empty
        for day in data:
            assert data[day] == []

    def test_list_with_subject_filter(self, client, monkeypatch):
        captured_params = {}

        def spy_execute(stmt, params=None):
            if "from optimized_schedule" in str(stmt).lower():
                captured_params.update(params or {})
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        client.get("/api/list-optimized?subject=COEN")
        assert captured_params.get("subject") == "COEN"

    def test_list_with_multiple_subjects(self, client, monkeypatch):
        captured_params = {}

        def spy_execute(stmt, params=None):
            if "from optimized_schedule" in str(stmt).lower():
                captured_params.update(params or {})
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        client.get("/api/list-optimized?subject=COEN,ELEC")
        assert captured_params.get("subj_0") == "COEN"
        assert captured_params.get("subj_1") == "ELEC"

    def test_list_with_component_filter(self, client, monkeypatch):
        captured_params = {}

        def spy_execute(stmt, params=None):
            if "from optimized_schedule" in str(stmt).lower():
                captured_params.update(params or {})
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        client.get("/api/list-optimized?component=LEC")
        assert captured_params.get("component") == "LEC"

    def test_list_with_building_filter(self, client, monkeypatch):
        captured_params = {}

        def spy_execute(stmt, params=None):
            if "from optimized_schedule" in str(stmt).lower():
                captured_params.update(params or {})
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        client.get("/api/list-optimized?building=H")
        assert captured_params.get("building") == "H"

    def test_list_groups_by_day(self, client, monkeypatch):
        """When rows have day flags, they appear under the correct day."""
        rows = [
            {
                "id": 1, "subject": "COEN", "catalog": "243",
                "section": "A", "componentcode": "LEC",
                "classnumber": 1000,
                "buildingcode": "H", "room": "920",
                "classstarttime": "08:45:00", "classendtime": "10:00:00",
                "mondays": True, "tuesdays": False, "wednesdays": True,
                "thursdays": False, "fridays": False,
                "saturdays": False, "sundays": False,
                "currentenrollment": 50, "enrollmentcapacity": 100,
                "currentwaitlisttotal": 0, "waitlistcapacity": 10,
                "coursetitle": "Intro to Software"
            }
        ]

        def spy_execute(stmt, params=None):
            if "from optimized_schedule" in str(stmt).lower():
                return _FakeResult(rows=rows)
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        resp = client.get("/api/list-optimized")
        data = resp.get_json()
        assert len(data["Monday"]) == 1
        assert len(data["Wednesday"]) == 1
        assert len(data["Tuesday"]) == 0

    def test_list_entry_fields(self, client, monkeypatch):
        rows = [
            {
                "id": 5, "subject": "ELEC", "catalog": "311",
                "section": "B", "componentcode": "LAB",
                "classnumber": 2000,
                "buildingcode": "EV", "room": "3.309",
                "classstarttime": "14:00:00", "classendtime": "16:00:00",
                "mondays": False, "tuesdays": True, "wednesdays": False,
                "thursdays": False, "fridays": False,
                "saturdays": False, "sundays": False,
                "currentenrollment": 20, "enrollmentcapacity": 25,
                "currentwaitlisttotal": 3, "waitlistcapacity": 5,
                "coursetitle": "Circuits Lab"
            }
        ]

        def spy_execute(stmt, params=None):
            if "from optimized_schedule" in str(stmt).lower():
                return _FakeResult(rows=rows)
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        resp = client.get("/api/list-optimized")
        entry = resp.get_json()["Tuesday"][0]
        assert entry["id"] == 5
        assert entry["subject"] == "ELEC"
        assert entry["catalog"] == "311"
        assert entry["component"] == "LAB"
        assert entry["building"] == "EV"
        assert entry["enrollment"] == 20
        assert entry["waitlistCapacity"] == 5


# ═══════════════════════════════════════════════════════════════════════
#  GET /api/optimized-date-range
# ═══════════════════════════════════════════════════════════════════════

class TestOptimizedDateRange:

    def test_date_range_returns_200(self, client):
        resp = client.get("/api/optimized-date-range")
        assert resp.status_code == 200

    def test_date_range_returns_json(self, client):
        resp = client.get("/api/optimized-date-range")
        assert resp.content_type.startswith("application/json")

    def test_date_range_with_data(self, client, monkeypatch):
        rows = [{"min_date": "2026-01-05", "max_date": "2026-04-15"}]

        def spy_execute(stmt, params=None):
            if "min(os.classstartdate)" in str(stmt).lower():
                return _FakeResult(rows=rows)
            return _FakeResult(rows=[])

        monkeypatch.setattr(db.session, "execute", spy_execute)
        resp = client.get("/api/optimized-date-range")
        data = resp.get_json()
        assert data["startDate"] == "2026-01-05"
        assert data["endDate"] == "2026-04-15"

    def test_date_range_empty(self, client):
        resp = client.get("/api/optimized-date-range")
        data = resp.get_json()
        assert data.get("startDate") is None or data.get("startDate") == ""
