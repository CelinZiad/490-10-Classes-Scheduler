import pytest
from helper.db_timetable_export import (
    day_number_to_day_columns,
    minutes_to_time,
    extract_day_numbers,
)
from day import Day


# --- day_number_to_day_columns ---

def test_day_cols_monday_w1():
    result = day_number_to_day_columns(1)
    assert result['mondays'] is True
    assert result['tuesdays'] is False
    assert result['wednesdays'] is False


def test_day_cols_friday_w1():
    result = day_number_to_day_columns(5)
    assert result['fridays'] is True
    assert result['mondays'] is False


def test_day_cols_monday_w2():
    result = day_number_to_day_columns(8)
    assert result['mondays'] is True


def test_day_cols_friday_w2():
    result = day_number_to_day_columns(12)
    assert result['fridays'] is True


def test_day_cols_invalid():
    result = day_number_to_day_columns(99)
    assert all(v is False for v in result.values())


def test_day_cols_all_days_present():
    result = day_number_to_day_columns(1)
    expected_keys = {'mondays', 'tuesdays', 'wednesdays', 'thursdays',
                     'fridays', 'saturdays', 'sundays'}
    assert set(result.keys()) == expected_keys


# --- minutes_to_time ---

def test_time_morning():
    assert minutes_to_time(525) == "08:45:00"


def test_time_afternoon():
    assert minutes_to_time(780) == "13:00:00"


def test_time_midnight():
    assert minutes_to_time(0) == "00:00:00"


# --- extract_day_numbers ---

def test_extract_int():
    assert extract_day_numbers(3) == [3]


def test_extract_int_week2():
    assert extract_day_numbers(10) == [10]


def test_extract_non_matching():
    result = extract_day_numbers("random")
    assert result == []
