from unittest.mock import MagicMock
import pytest
import waitlist_algorithm.algorithm.room_busy as mod
from waitlist_algorithm.algorithm.time_block import TimeBlock,m


def test_exec_called_with_correct_params_and_sql_contains_core_parts():
    cur = MagicMock()
    cur.fetchall.return_value = []

    out = mod.load_room_busy_for_course(cur, "COEN", "346")

    assert out == []
    cur.execute.assert_called_once()

    sql_arg, params_arg = cur.execute.call_args.args
    assert params_arg == ("COEN", "346")

    assert "WITH allowed_rooms AS" in sql_arg
    assert "FROM courselabs" in sql_arg
    assert "FROM scheduleterm" in sql_arg
    assert "ORDER BY day, start_time" in sql_arg


def test_builds_timeblocks_from_string_times():
    cur = MagicMock()
    cur.fetchall.return_value = [
        (1, "09:00:00", "10:15:00"),
        (8, "13:30:00", "15:00:00"),
    ]

    out = mod.load_room_busy_for_course(cur, "COEN", "346")

    assert out == [
        TimeBlock(day=1, start=540, end=615),
        TimeBlock(day=8, start=810, end=900),
    ]


def test_day_is_cast_to_int_if_driver_returns_string():
    cur = MagicMock()
    cur.fetchall.return_value = [
        ("2", "08:00:00", "09:00:00"),
    ]

    out = mod.load_room_busy_for_course(cur, "COEN", "346")

    assert out == [TimeBlock(day=2, start=480, end=540)]


def test_builds_timeblocks_from_time_objects_with_hour_minute():
    class FakeTime:
        def __init__(self, hour, minute):
            self.hour = hour
            self.minute = minute

    cur = MagicMock()
    cur.fetchall.return_value = [
        (3, FakeTime(14, 5), FakeTime(16, 0)),
    ]

    out = mod.load_room_busy_for_course(cur, "COEN", "346")

    assert out == [TimeBlock(day=3, start=14 * 60 + 5, end=16 * 60)]


def test_builds_timeblocks_from_int_minutes_directly():
    cur = MagicMock()
    cur.fetchall.return_value = [
        (5, 600, 660),
    ]

    out = mod.load_room_busy_for_course(cur, "COEN", "346")

    assert out == [TimeBlock(day=5, start=600, end=660)]

