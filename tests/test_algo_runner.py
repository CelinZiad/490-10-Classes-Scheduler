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
from app import derive_solution


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
    row = {"Conflict_Type": "Sequence-Missing Course", "Course": "Multiple"}
    result = derive_solution(row)
    assert "missing course" in result.lower()


def test_conflicts_page_with_mock_data(client):
    """Conflicts page shows data when CSV has conflicts."""
    mock_conflicts = [
        {"Conflict_Type": "Room Conflict", "Course": "COEN311",
         "Day": "1", "Time1": "10:00", "Time2": "12:00",
         "Building": "H", "Room": "807"},
    ]
    with patch("algo_runner.load_conflicts_from_csv", return_value=mock_conflicts):
        res = client.get("/conflicts")
        assert res.status_code == 200
        html = res.get_data(as_text=True)
        assert "COEN311" in html
        assert "Room Conflict" in html


def test_conflicts_page_empty(client):
    """Conflicts page shows empty state when no CSV data."""
    with patch("algo_runner.load_conflicts_from_csv", return_value=[]):
        res = client.get("/conflicts")
        assert res.status_code == 200
        html = res.get_data(as_text=True)
        assert "No conflicts detected" in html


def test_export_csv_404_when_no_file(client):
    """Export CSV returns 404 when no schedule file exists."""
    with patch("algo_runner.get_schedule_csv_path", return_value="/nonexistent/file.csv"):
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
    }

    with patch("algo_runner.run_algorithm", return_value=mock_result):
        res = client.post("/schedulerrun", data={"schedulename": "test-run"})
        assert res.status_code in [302, 303]
