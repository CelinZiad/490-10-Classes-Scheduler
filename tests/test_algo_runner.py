"""Tests for algo_runner module and solution derivation."""

import csv
from unittest.mock import patch

import pytest

from algo_runner import (
    _read_csv_file,
    get_schedule_csv_path,
    get_conflicts_csv_path,
    get_room_csv_path,
    load_schedule_from_csv,
    load_conflicts_from_csv,
)
from app import derive_solution, conflict_detail
from conftest import _FakeResult


def test_read_csv_file_missing():
    assert _read_csv_file("/nonexistent/file.csv") == []


def test_read_csv_file_valid(tmp_path):
    csv_path = str(tmp_path / "test.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["A", "B"])
        writer.writeheader()
        writer.writerow({"A": "1", "B": "2"})
    rows = _read_csv_file(csv_path)
    assert len(rows) == 1
    assert rows[0]["A"] == "1"


def test_get_schedule_csv_path():
    path = get_schedule_csv_path()
    assert path.endswith("best_course_timetable.csv")
    assert "genetic_algo" in path


def test_get_conflicts_csv_path():
    path = get_conflicts_csv_path()
    assert path.endswith("conflicts.csv")


def test_get_room_csv_path():
    path = get_room_csv_path()
    assert path.endswith("best_room_timetable.csv")


def test_load_schedule_no_file():
    assert load_schedule_from_csv() == [] or isinstance(load_schedule_from_csv(), list)


def test_load_conflicts_no_file():
    assert load_conflicts_from_csv() == [] or isinstance(load_conflicts_from_csv(), list)


def test_derive_solution_lecture_tutorial():
    row = {"Conflict_Type": "Lecture-Tutorial", "Course": "COEN311"}
    result = derive_solution(row)
    assert "COEN311" in result
    assert "tutorial" in result.lower()


def test_derive_solution_room_conflict():
    row = {"Conflict_Type": "Room Conflict", "Course": "COEN311 & COEN212"}
    result = derive_solution(row)
    assert "room" in result.lower()


def test_derive_solution_unknown_type():
    row = {"Conflict_Type": "SomethingNew", "Course": "COEN311"}
    result = derive_solution(row)
    assert "COEN311" in result


def test_derive_solution_missing_course():
    row = {
        "Conflict_Type": "Sequence-Missing Course",
        "Course": "Multiple",
        "Component1": "Semester 3",
        "Component2": "['COEN490']",
    }
    result = derive_solution(row)
    assert "COEN490" in result
    assert "Semester 3" in result


def test_derive_solution_missing_course_with_labels():
    row = {
        "Conflict_Type": "Sequence-Missing Course",
        "Course": "Multiple",
        "Component1": "Semester 3",
        "Component2": "['COEN490']",
    }
    labels = {"3": "Fall Year 2 (COEN)"}
    result = derive_solution(row, semester_labels=labels)
    assert "COEN490" in result
    assert "Fall Year 2 (COEN)" in result
    assert "Semester 3" not in result


def test_conflict_detail_missing_course():
    row = {
        "Conflict_Type": "Sequence-Missing Course",
        "Course": "Multiple",
        "Component1": "Semester 3",
        "Component2": "['COEN490']",
    }
    result = conflict_detail(row)
    assert "Semester 3" in result
    assert "COEN490" in result


def test_conflict_detail_missing_course_with_labels():
    row = {
        "Conflict_Type": "Sequence-Missing Course",
        "Course": "Multiple",
        "Component1": "Semester 3",
        "Component2": "['COEN490']",
    }
    labels = {"3": "Fall Year 2 (COEN)"}
    result = conflict_detail(row, semester_labels=labels)
    assert "Fall Year 2 (COEN)" in result
    assert "COEN490" in result


def test_conflict_detail_lecture_tutorial():
    row = {
        "Conflict_Type": "Lecture-Tutorial",
        "Course": "COEN311",
        "Component1": "Lecture",
        "Component2": "Tutorial",
        "Day": "3",
        "Time1": "08:45",
        "Time2": "10:00",
    }
    result = conflict_detail(row)
    assert "COEN311" in result
    assert "08:45" in result


def test_conflict_detail_room_conflict():
    row = {
        "Conflict_Type": "Room Conflict",
        "Course": "COEN311",
        "Building": "H",
        "Room": "807",
    }
    result = conflict_detail(row)
    assert "H-807" in result


def test_conflicts_page_empty(client):
    """Conflicts page shows empty state when DB has no active conflicts."""
    res = client.get("/conflicts")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "No conflicts detected" in html


def test_conflicts_page_with_db_data(app, monkeypatch):
    """Conflicts page renders data from DB with enriched detail column."""
    import json as _json
    from app import db as _db

    conflict_data = _json.dumps({
        "type": "Room Conflict",
        "course": "COEN311",
        "detail": "COEN311 both assigned H-807 \u2014 10:00 vs 12:00",
    })

    class _ConflictSession:
        def execute(self, statement, params=None):
            sql = str(statement).lower()
            if "from conflict" in sql:
                return _FakeResult(rows=[{
                    "conflictid": 1,
                    "status": "active",
                    "description": conflict_data,
                    "createdat": "2026-01-01 00:00",
                }])
            return _FakeResult(rows=[])

        def commit(self):
            return None

        def rollback(self):
            return None

        def remove(self):
            return None

    monkeypatch.setattr(_db, "session", _ConflictSession(), raising=False)
    monkeypatch.setattr(_db, "_session", _ConflictSession(), raising=False)

    client = app.test_client()
    res = client.get("/conflicts")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Room Conflict" in html
    assert "COEN311" in html
    assert "H-807" in html


def test_export_csv_404_when_no_data(client):
    """Export CSV returns 404 when DB has no schedule data."""
    res = client.get("/api/export-csv")
    assert res.status_code == 404


def test_api_generate_with_mock(client):
    """Test the scheduler run with a mocked algorithm."""
    mock_result = {
        "status": "success",
        "best_fitness": 42.5,
        "generations": 10,
        "termination_reason": "generation_limit",
        "schedule": [{"Type": "Lecture", "Subject": "COEN", "Catalog_Nbr": "311"}],
        "conflicts": [{"Conflict_Type": "Lecture-Tutorial", "Course": "COEN311",
                        "Time1": "08:45-11:15", "Time2": "10:00-10:50"}],
        "num_conflicts": 1,
        "duration_seconds": 5.0,
        "num_courses": 15,
        "semester_labels": {},
    }

    with patch("algo_runner.run_algorithm", return_value=mock_result):
        res = client.post("/schedulerrun", data={"schedulename": "test-run"})
        assert res.status_code in [302, 303]
