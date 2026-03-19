import pytest
from helper.scheduleterm_export import (
    should_exclude_course,
    build_termcode,
    get_previous_year_data,
)
from helper.academic_calendar import (
    get_session_code,
)
from helper.time_utils import (
    minutes_to_time,
    day_number_to_day_columns,
    combine_day_columns,
    extract_day_numbers,
)
from day import Day


# --- should_exclude_course ---

def test_exclude_elec430():
    assert should_exclude_course("ELEC", "430") is True


def test_exclude_elec498():
    assert should_exclude_course("ELEC", "498") is True


def test_not_exclude_coen():
    assert should_exclude_course("COEN", "311") is False


def test_not_exclude_elec273():
    assert should_exclude_course("ELEC", "273") is False


# --- build_termcode ---

def test_termcode_2025_fall():
    assert build_termcode(2025, 2) == "2252"


def test_termcode_2026_winter():
    assert build_termcode(2026, 4) == "2264"


# --- get_session_code ---

def test_session_fall():
    assert get_session_code(2) == "13W"


def test_session_winter():
    assert get_session_code(4) == "13W"


def test_session_year_long():
    assert get_session_code(3) == "26W"


def test_session_summer_with_previous():
    assert get_session_code(1, "26W") == "26W"


def test_session_summer_no_previous():
    assert get_session_code(1) == "13W"


# --- minutes_to_time ---

def test_minutes_morning():
    assert minutes_to_time(525) == "08:45:00"


def test_minutes_midnight():
    assert minutes_to_time(0) == "00:00:00"


# --- day_number_to_day_columns ---

def test_day_cols_mon_w1():
    result = day_number_to_day_columns(1)
    assert result['mondays'] is True
    assert sum(v for v in result.values() if v) == 1


def test_day_cols_fri_w2():
    result = day_number_to_day_columns(12)
    assert result['fridays'] is True


def test_day_cols_invalid():
    result = day_number_to_day_columns(99)
    assert all(v is False for v in result.values())


# --- combine_day_columns ---

def test_combine_two_days():
    result = combine_day_columns([1, 3])
    assert result['mondays'] is True
    assert result['wednesdays'] is True
    assert result['tuesdays'] is False


def test_combine_empty():
    result = combine_day_columns([])
    assert all(v is False for v in result.values())


def test_combine_week1_and_week2():
    result = combine_day_columns([1, 8])
    assert result['mondays'] is True


# --- extract_day_numbers ---

def test_extract_int():
    assert extract_day_numbers(3) == [3]


def test_extract_int_week2():
    assert extract_day_numbers(10) == [10]


# --- get_previous_year_data ---

def test_prev_year_exact_match():
    cache = {
        ('COEN', '311', 'AA', 'TUT'): {
            'classnumber': '12345', 'session': '13W',
            'instructionmodecode': 'P', 'locationcode': 'SGW', 'career': 'UGRD'
        }
    }
    result = get_previous_year_data('COEN', '311', 'AA', 'TUT', cache)
    assert result['classnumber'] == '12345'


def test_prev_year_alt_key():
    cache = {
        ('COEN', '311', 'TUT'): {
            'classnumber': '99999', 'session': '13W',
            'instructionmodecode': 'P', 'locationcode': 'SGW', 'career': 'UGRD'
        }
    }
    result = get_previous_year_data('COEN', '311', 'BB', 'TUT', cache)
    assert result['classnumber'] == '99999'


def test_prev_year_not_found():
    result = get_previous_year_data('COEN', '311', 'AA', 'TUT', {})
    assert result['classnumber'] is None
    assert result['session'] == '13W'
