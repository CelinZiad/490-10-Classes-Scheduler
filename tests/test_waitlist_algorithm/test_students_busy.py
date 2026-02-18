# tests/test_students_busy.py

import datetime as dt
from unittest.mock import MagicMock

import pytest

from waitlist_algorithm.algorithm.students_busy import (
    get_two_week_anchor_monday,
    load_students_busy_from_db,
)
from waitlist_algorithm.algorithm.time_block import TimeBlock, to_minutes


def test_get_two_week_anchor_monday_executes_and_returns_date():
    cur = MagicMock()
    expected = dt.date(2026, 2, 16)
    cur.fetchone.return_value = (expected,)

    studyids = [101, 202]

    week1 = get_two_week_anchor_monday(cur, studyids)

    assert week1 == expected
    cur.execute.assert_called_once()

    sql, params = cur.execute.call_args[0]
    assert params == (studyids,)  # IMPORTANT: tuple containing the list
    assert "date_trunc('week'" in sql
    assert "WHERE ss.studyid = ANY(%s)" in sql


def test_load_students_busy_from_db_empty_ids_returns_empty_and_no_db_calls():
    cur = MagicMock()

    result = load_students_busy_from_db(cur, [])

    assert result == {}
    cur.execute.assert_not_called()
    cur.fetchall.assert_not_called()
    cur.fetchone.assert_not_called()


def test_load_students_busy_from_db_executes_anchor_then_main_query():
    cur = MagicMock()

    week1_monday = dt.date(2026, 2, 16)
    cur.fetchone.return_value = (week1_monday,)

    # no rows
    cur.fetchall.return_value = []

    studyids = [1, 2, 3]
    result = load_students_busy_from_db(cur, studyids)

    assert result == {}

    # 2 executes: anchor + main
    assert cur.execute.call_count == 2

    # 1) anchor params
    anchor_sql, anchor_params = cur.execute.call_args_list[0][0]
    assert anchor_params == (studyids,)
    assert "week1_monday" in anchor_sql

    # 2) main params
    main_sql, main_params = cur.execute.call_args_list[1][0]
    assert main_params == (studyids, week1_monday)
    assert "FROM generate_series(0, 13)" in main_sql
    assert "ORDER BY c.studyid, day, start_time" in main_sql


def test_load_students_busy_from_db_maps_rows_to_timeblocks_grouped_by_student():
    cur = MagicMock()
    week1_monday = dt.date(2026, 2, 16)
    cur.fetchone.return_value = (week1_monday,)

    # rows: (studyid, componentcode, classstartdate, day, start_time, end_time)
    cur.fetchall.return_value = [
        (10, "LEC", dt.date(2026, 2, 16), 1, dt.time(8, 45), dt.time(10, 0)),
        (10, "TUT", dt.date(2026, 2, 17), 2, dt.time(11, 45), dt.time(12, 35)),
        (20, "LEC", dt.date(2026, 2, 18), 3, dt.time(14, 45), dt.time(16, 0)),
    ]

    result = load_students_busy_from_db(cur, [10, 20])

    assert result.keys() == {10, 20}

    assert result[10] == [
        TimeBlock(day=1, start=to_minutes(dt.time(8, 45)), end=to_minutes(dt.time(10, 0))),
        TimeBlock(day=2, start=to_minutes(dt.time(11, 45)), end=to_minutes(dt.time(12, 35))),
    ]
    assert result[20] == [
        TimeBlock(day=3, start=to_minutes(dt.time(14, 45)), end=to_minutes(dt.time(16, 0))),
    ]


def test_load_students_busy_from_db_lab_filter_week1_keeps_only_days_1_to_7_for_that_student():
    """
    If min LAB startdate is the earliest LAB date among all students,
    then any student whose LAB startdate == min_lab_date is treated as lab_week=1.
    For lab_week=1, LAB entries with day > 7 are skipped.
    """
    cur = MagicMock()
    cur.fetchone.return_value = (dt.date(2026, 2, 16),)

    earliest_lab_date = dt.date(2026, 2, 18)

    cur.fetchall.return_value = [
        # Student 111 has LAB on earliest date => lab_week=1
        (111, "LAB", earliest_lab_date, 6, dt.time(9, 0), dt.time(10, 0)),   # keep (<=7)
        (111, "LAB", earliest_lab_date, 9, dt.time(9, 0), dt.time(10, 0)),   # drop (>7)

        # Non-lab entries should always be kept
        (111, "LEC", dt.date(2026, 2, 16), 2, dt.time(8, 0), dt.time(9, 0)), # keep
    ]

    result = load_students_busy_from_db(cur, [111])

    assert result[111] == [
        TimeBlock(day=6, start=to_minutes(dt.time(9, 0)), end=to_minutes(dt.time(10, 0))),
        TimeBlock(day=2, start=to_minutes(dt.time(8, 0)), end=to_minutes(dt.time(9, 0))),
    ]


def test_load_students_busy_from_db_lab_filter_week2_keeps_only_days_8_to_14_for_that_student():
    """
    If a student's LAB startdate is later than the global earliest LAB date,
    they are treated as lab_week=2.
    For lab_week=2, LAB entries with day <= 7 are skipped.
    """
    cur = MagicMock()
    cur.fetchone.return_value = (dt.date(2026, 2, 16),)

    earliest_lab_date = dt.date(2026, 2, 18)
    later_lab_date = dt.date(2026, 2, 25)

    cur.fetchall.return_value = [
        # Student 111 has the earliest LAB date => lab_week=1
        (111, "LAB", earliest_lab_date, 6, dt.time(9, 0), dt.time(10, 0)),

        # Student 222 has a later LAB date => lab_week=2
        (222, "LAB", later_lab_date, 4, dt.time(9, 0), dt.time(10, 0)),   # drop (<=7)
        (222, "LAB", later_lab_date, 10, dt.time(9, 0), dt.time(10, 0)),  # keep (>7)

        # Student 222 non-lab should remain
        (222, "LEC", dt.date(2026, 2, 16), 3, dt.time(8, 0), dt.time(9, 0)),
    ]

    result = load_students_busy_from_db(cur, [111, 222])

    assert result[222] == [
        TimeBlock(day=10, start=to_minutes(dt.time(9, 0)), end=to_minutes(dt.time(10, 0))),
        TimeBlock(day=3, start=to_minutes(dt.time(8, 0)), end=to_minutes(dt.time(9, 0))),
    ]
    assert result[111] == [
        TimeBlock(day=6, start=to_minutes(dt.time(9, 0)), end=to_minutes(dt.time(10, 0))),
    ]


def test_load_students_busy_from_db_no_lab_rows_no_lab_filtering_applied():
    cur = MagicMock()
    cur.fetchone.return_value = (dt.date(2026, 2, 16),)

    cur.fetchall.return_value = [
        (1, "LEC", dt.date(2026, 2, 16), 8, dt.time(13, 0), dt.time(14, 0)),
        (1, "TUT", dt.date(2026, 2, 17), 2, dt.time(9, 0), dt.time(10, 0)),
    ]

    result = load_students_busy_from_db(cur, [1])

    assert result[1] == [
        TimeBlock(day=8, start=to_minutes(dt.time(13, 0)), end=to_minutes(dt.time(14, 0))),
        TimeBlock(day=2, start=to_minutes(dt.time(9, 0)), end=to_minutes(dt.time(10, 0))),
    ]
