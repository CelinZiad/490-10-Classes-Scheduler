import pytest
from course import Course, parse_time_to_minutes
from course_element import CourseElement
from day import Day


def test_parse_time_colon_format():
    assert parse_time_to_minutes("11:45") == 705


def test_parse_time_dotted_format():
    assert parse_time_to_minutes("13.00.00") == 780


def test_parse_time_with_seconds():
    assert parse_time_to_minutes("8:45:00") == 525


def test_parse_time_empty_raises():
    with pytest.raises(ValueError):
        parse_time_to_minutes("")


def test_parse_time_invalid_raises():
    with pytest.raises(ValueError):
        parse_time_to_minutes("abc")


def test_from_csv_row_basic():
    row = {
        "subject": "COEN",
        "catalog_nbr": "311",
        "class_nbr": "00001",
        "day_of_week": "TuTh",
        "start_time": "11:45",
        "end_time": "13:00",
        "lab_count": "2",
        "biweekly_lab_freq": "1",
        "lab_duration": "165",
        "tut_count": "1",
        "weekly_tut_freq": "1",
        "tut_duration": "50",
    }
    course = Course.from_csv_row(row)
    assert course.subject == "COEN"
    assert course.catalog_nbr == "311"
    assert course.lab_count == 2
    assert course.tut_count == 1
    assert len(course.lab) == 2
    assert len(course.tutorial) == 1
    assert course.lecture.start == 705
    assert course.lecture.end == 780


def test_from_csv_row_no_labs_no_tuts():
    row = {
        "subject": "ENGR",
        "catalog_nbr": "290",
        "class_nbr": "00010",
        "day_of_week": "MoWe",
        "start_time": "8:45",
        "end_time": "10:00",
        "lab_count": "0",
        "biweekly_lab_freq": "0",
        "lab_duration": "0",
        "tut_count": "0",
        "weekly_tut_freq": "0",
        "tut_duration": "0",
    }
    course = Course.from_csv_row(row)
    assert len(course.lab) == 0
    assert len(course.tutorial) == 0


def test_day_codes_property():
    row = {
        "subject": "COEN",
        "catalog_nbr": "212",
        "class_nbr": "00001",
        "day_of_week": "TuTh",
        "start_time": "11:45",
        "end_time": "13:00",
        "lab_count": "0",
        "biweekly_lab_freq": "0",
        "lab_duration": "0",
        "tut_count": "0",
        "weekly_tut_freq": "0",
        "tut_duration": "0",
    }
    course = Course.from_csv_row(row)
    codes = course.day_codes
    assert 2 in codes   # TU week 1
    assert 9 in codes   # TU week 2
    assert 4 in codes   # TH week 1
    assert 11 in codes  # TH week 2
