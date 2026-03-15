from unittest.mock import MagicMock
import pytest
import importlib


@pytest.fixture
def mod():
    return importlib.import_module("waitlist_algorithm.algorithm.main")


def test_main_happy_path_calls_everything_and_commits(mod):
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur

    mod.get_conn = MagicMock(return_value=conn)

    mod.get_waitlisted_students_and_course_from_user = MagicMock(
        return_value=([101, 202], ("COEN", "352"))
    )

    students_busy = {101: [], 202: []}
    week1 = "2026-02-16"
    room_busy = ["rb1"]

    mod.load_students_busy_from_db = MagicMock(return_value=students_busy)
    mod.get_two_week_anchor_monday = MagicMock(return_value=week1)
    mod.load_room_busy_for_course = MagicMock(return_value=room_busy)

    results = {(2, 600): [202], (1, 525): [101, 202]}
    mod.propose_waitlist_slots = MagicMock(return_value=results)

    mod.save_lab_results_to_db = MagicMock()
    mod.format_time = MagicMock(side_effect=lambda x: f"T{x}")

    mod.main()

    mod.get_conn.assert_called_once()
    conn.cursor.assert_called_once()

    mod.get_waitlisted_students_and_course_from_user.assert_called_once_with(cur)
    mod.load_students_busy_from_db.assert_called_once_with(cur, [101, 202])
    mod.get_two_week_anchor_monday.assert_called_once_with(cur, [101, 202])
    mod.load_room_busy_for_course.assert_called_once_with(cur, "COEN", "352", week1)

    assert mod.propose_waitlist_slots.call_count == 1
    _, kwargs = mod.propose_waitlist_slots.call_args
    assert kwargs["waitlisted_students"] == [101, 202]
    assert kwargs["students_busy"] == students_busy
    assert kwargs["room_busy"] == room_busy
    assert kwargs["lab_start_times"] == [mod.m(8, 45), mod.m(11, 45), mod.m(14, 45), mod.m(17, 45)]

    mod.save_lab_results_to_db.assert_called_once_with(cur, "COEN", "352", 180, results)
    conn.commit.assert_called_once()


def test_main_prints_sorted_results(mod, capsys):
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur

    mod.get_conn = MagicMock(return_value=conn)
    mod.get_waitlisted_students_and_course_from_user = MagicMock(
        return_value=([1, 2], ("COEN", "352"))
    )
    mod.load_students_busy_from_db = MagicMock(return_value={})
    mod.get_two_week_anchor_monday = MagicMock(return_value="2026-02-16")
    mod.load_room_busy_for_course = MagicMock(return_value=[])

    results = {(2, 600): [2], (1, 525): [1, 2]}
    mod.propose_waitlist_slots = MagicMock(return_value=results)

    mod.save_lab_results_to_db = MagicMock()
    mod.format_time = MagicMock(side_effect=lambda x: f"{x}")

    mod.main()

    out = capsys.readouterr().out.strip().splitlines()

    assert "--- Proposed Lab Slots ---" in out[0]
    assert out[1] == "1,525,1,2"
    assert out[2] == "2,600,2"
