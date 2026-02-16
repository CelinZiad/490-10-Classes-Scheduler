from unittest.mock import MagicMock
import pytest
import waitlist_algorithm.algorithm.students_busy as mod
from waitlist_algorithm.algorithm.time_block import TimeBlock,m


def test_empty_studyids_returns_empty_dict():
    cur = MagicMock()
    out = mod.load_students_busy_from_db(cur, [])
    assert out == {}
    cur.execute.assert_not_called()


def test_exec_called_with_correct_params_and_sql_contains_core_parts():
    cur = MagicMock()
    cur.fetchall.return_value = []

    out = mod.load_students_busy_from_db(cur, [101, 102])

    assert out == {}
    cur.execute.assert_called_once()

    sql_arg, params_arg = cur.execute.call_args.args
    assert params_arg == ([101, 102],)

    assert "WITH sched AS" in sql_arg
    assert "JOIN studentscheduleclass" in sql_arg
    assert "JOIN scheduleterm" in sql_arg
    assert "ORDER BY studyid, day, start_time" in sql_arg


def test_builds_dict_of_timeblocks_from_string_times():
    cur = MagicMock()
    cur.fetchall.return_value = [
        (101, 1, "09:00:00", "10:15:00"),
        (101, 3, "13:30:00", "15:00:00"),
        (202, 2, "08:00:00", "09:00:00"),
    ]

    out = mod.load_students_busy_from_db(cur, [101, 202])

    assert out == {
        101: [
            TimeBlock(day=1, start=540, end=615),
            TimeBlock(day=3, start=810, end=900),
        ],
        202: [
            TimeBlock(day=2, start=480, end=540),
        ],
    }


def test_day_casts_to_int_if_driver_returns_string():
    cur = MagicMock()
    cur.fetchall.return_value = [
        (101, "2", "08:00:00", "09:00:00"),
    ]

    out = mod.load_students_busy_from_db(cur, [101])

