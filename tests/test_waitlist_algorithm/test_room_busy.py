import datetime as dt
from unittest.mock import MagicMock

import pytest

from waitlist_algorithm.algorithm.room_busy import load_room_busy_for_course
from waitlist_algorithm.algorithm.time_block import TimeBlock, to_minutes


def test_load_room_busy_for_course_executes_query_with_params():
    cur = MagicMock()
    cur.fetchall.return_value = []

    subject = "COEN"
    catalog = "352"
    week1_monday = dt.date(2026, 2, 16)

    result = load_room_busy_for_course(cur, subject, catalog, week1_monday)

    assert result == []

    cur.execute.assert_called_once()

    _sql, params = cur.execute.call_args[0]
    assert params == (subject, catalog, week1_monday)

    assert "WITH allowed_rooms AS" in _sql
    assert "generate_series(0, 13)" in _sql
    assert "ORDER BY day, start_time" in _sql


def test_load_room_busy_for_course_maps_rows_to_timeblocks():
    cur = MagicMock()

    cur.fetchall.return_value = [
        (1, dt.time(8, 45), dt.time(10, 0)),
        (3, dt.time(14, 45), dt.time(16, 30)),
    ]

    result = load_room_busy_for_course(cur, "COEN", "352", dt.date(2026, 2, 16))

    assert result == [
        TimeBlock(day=1, start=to_minutes(dt.time(8, 45)), end=to_minutes(dt.time(10, 0))),
        TimeBlock(day=3, start=to_minutes(dt.time(14, 45)), end=to_minutes(dt.time(16, 30))),
    ]


def test_load_room_busy_for_course_casts_day_to_int():
    cur = MagicMock()

    cur.fetchall.return_value = [
        ("2", dt.time(11, 45), dt.time(12, 35)),
    ]

    result = load_room_busy_for_course(cur, "COEN", "352", dt.date(2026, 2, 16))

    assert len(result) == 1
    assert result[0].day == 2
    assert result[0].start == to_minutes(dt.time(11, 45))
    assert result[0].end == to_minutes(dt.time(12, 35))


def test_load_room_busy_for_course_multiple_rows_order_preserved():
    cur = MagicMock()

    cur.fetchall.return_value = [
        (1, dt.time(9, 0), dt.time(10, 0)),
        (1, dt.time(10, 0), dt.time(11, 0)),
        (2, dt.time(8, 45), dt.time(9, 35)),
    ]

    result = load_room_busy_for_course(cur, "COEN", "352", dt.date(2026, 2, 16))

    assert [tb.day for tb in result] == [1, 1, 2]
    assert [(tb.start, tb.end) for tb in result] == [
        (to_minutes(dt.time(9, 0)), to_minutes(dt.time(10, 0))),
        (to_minutes(dt.time(10, 0)), to_minutes(dt.time(11, 0))),
        (to_minutes(dt.time(8, 45)), to_minutes(dt.time(9, 35))),
    ]
