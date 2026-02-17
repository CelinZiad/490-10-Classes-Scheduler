import pytest
from datetime import time
from helper.db_course_extractor import (
    build_termcode,
    parse_time_to_dotted,
    calculate_duration_minutes,
    parse_day_pattern,
    extract_base_section,
    count_unique_sections,
    determine_lab_frequency,
    determine_tutorial_frequency,
    group_by_lecture,
)


# --- build_termcode ---

def test_termcode_2025_fall():
    assert build_termcode(2025, 2) == "2252"


def test_termcode_2026_winter():
    assert build_termcode(2026, 4) == "2264"


def test_termcode_2024_summer():
    assert build_termcode(2024, 6) == "2246"


# --- parse_time_to_dotted ---

def test_parse_time_from_time_obj():
    t = time(11, 45, 0)
    assert parse_time_to_dotted(t) == "11.45.00"


def test_parse_time_from_string():
    assert parse_time_to_dotted("13:00:00") == "13.00.00"


def test_parse_time_from_bad_string():
    assert parse_time_to_dotted("not-a-time") == "00.00.00"


def test_parse_time_from_none():
    assert parse_time_to_dotted(None) == "00.00.00"


# --- calculate_duration_minutes ---

def test_duration_from_time_objects():
    start = time(8, 45, 0)
    end = time(11, 30, 0)
    assert calculate_duration_minutes(start, end) == 165


def test_duration_from_strings():
    assert calculate_duration_minutes("08:45:00", "11:30:00") == 165


def test_duration_one_hour():
    assert calculate_duration_minutes("09:00:00", "10:00:00") == 60


# --- parse_day_pattern ---

def test_day_pattern_moweonly():
    row = {'mondays': True, 'tuesdays': False, 'wednesdays': True,
           'thursdays': False, 'fridays': False, 'saturdays': False, 'sundays': False}
    assert parse_day_pattern(row) == "MoWe"


def test_day_pattern_tuth():
    row = {'mondays': False, 'tuesdays': True, 'wednesdays': False,
           'thursdays': True, 'fridays': False, 'saturdays': False, 'sundays': False}
    assert parse_day_pattern(row) == "TuTh"


def test_day_pattern_string_true():
    row = {'mondays': 'true', 'tuesdays': 'false', 'wednesdays': 'false',
           'thursdays': 'false', 'fridays': 'true', 'saturdays': 'false', 'sundays': 'false'}
    assert parse_day_pattern(row) == "MoFr"


def test_day_pattern_empty():
    row = {'mondays': False, 'tuesdays': False, 'wednesdays': False,
           'thursdays': False, 'fridays': False, 'saturdays': False, 'sundays': False}
    assert parse_day_pattern(row) == ""


# --- extract_base_section ---

def test_base_section_lec():
    assert extract_base_section("AA", "LEC") == "AA"


def test_base_section_tut_space():
    assert extract_base_section("AA T1", "TUT") == "AA"


def test_base_section_tut_dash():
    assert extract_base_section("AA-T1", "TUT") == "A"


def test_base_section_lab_no_separator():
    assert extract_base_section("AA", "LAB") == "AA"


# --- count_unique_sections ---

def test_count_unique_two():
    components = [{'section': 'T1'}, {'section': 'T2'}, {'section': 'T1'}]
    assert count_unique_sections(components) == 2


def test_count_unique_empty():
    assert count_unique_sections([]) == 0


# --- determine_lab_frequency / determine_tutorial_frequency ---

def test_lab_freq_with_labs():
    assert determine_lab_frequency([{'section': 'L1'}]) == 1


def test_lab_freq_no_labs():
    assert determine_lab_frequency([]) == 0


def test_tut_freq_with_tuts():
    assert determine_tutorial_frequency([{'section': 'T1'}]) == 1


def test_tut_freq_no_tuts():
    assert determine_tutorial_frequency([]) == 0


# --- group_by_lecture ---

def test_group_basic():
    records = [
        {'subject': 'COEN', 'catalog': '311', 'section': 'AA', 'componentcode': 'LEC'},
        {'subject': 'COEN', 'catalog': '311', 'section': 'AA T1', 'componentcode': 'TUT'},
        {'subject': 'COEN', 'catalog': '311', 'section': 'AA L1', 'componentcode': 'LAB'},
    ]
    grouped = group_by_lecture(records)
    key = ('COEN', '311', 'AA')
    assert key in grouped
    assert grouped[key]['lecture'] is not None
    assert len(grouped[key]['tutorials']) == 1
    assert len(grouped[key]['labs']) == 1


def test_group_filters_math():
    records = [
        {'subject': 'MATH', 'catalog': '201', 'section': 'AA', 'componentcode': 'LEC'},
    ]
    grouped = group_by_lecture(records)
    assert len(grouped) == 0
