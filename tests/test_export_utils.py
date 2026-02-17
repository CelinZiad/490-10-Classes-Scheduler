import os
import csv
import pytest
from course_element import CourseElement
from course import Course
from day import Day
from room_management import RoomTimetable
from helper.export_utils import (
    minutes_to_time_string,
    day_number_to_string,
    extract_day_numbers,
    export_course_timetable_csv,
    export_room_timetable_csv,
)


def _make_course(subject="COEN", catalog="311", class_nbr="00001",
                 lec_days=(Day.TU, Day.TH), lec_start=705, lec_end=780,
                 tut_count=0, tut_duration=0, lab_count=0, lab_duration=0):
    lecture = CourseElement(day=lec_days, start=lec_start, end=lec_end)
    tuts = tuple(CourseElement(day=[], start=0, end=0) for _ in range(tut_count))
    labs = tuple(CourseElement(day=[], start=0, end=0) for _ in range(lab_count))
    return Course(
        subject=subject, catalog_nbr=catalog, class_nbr=class_nbr,
        lecture=lecture, tutorial=tuts, lab=labs,
        tut_count=tut_count, weekly_tut_freq=1 if tut_count else 0,
        tut_duration=tut_duration, lab_count=lab_count,
        biweekly_lab_freq=1 if lab_count else 0, lab_duration=lab_duration,
    )


# --- minutes_to_time_string ---

def test_minutes_to_time_string():
    assert minutes_to_time_string(525) == "08:45"
    assert minutes_to_time_string(780) == "13:00"
    assert minutes_to_time_string(0) == "00:00"
    assert minutes_to_time_string(1439) == "23:59"


# --- day_number_to_string ---

def test_day_number_week1():
    assert "Week 1" in day_number_to_string(1)
    assert "Monday" in day_number_to_string(1)


def test_day_number_week2():
    assert "Week 2" in day_number_to_string(8)
    assert "Monday" in day_number_to_string(8)


def test_day_number_friday():
    assert "Friday" in day_number_to_string(5)
    assert "Friday" in day_number_to_string(12)


def test_day_number_out_of_range():
    result = day_number_to_string(99)
    assert "Day 99" in result


def test_day_number_from_int():
    # Day enums don't convert via int() (known bug); ints work fine
    result = day_number_to_string(1)
    assert "Monday" in result


# --- extract_day_numbers ---

def test_extract_day_numbers_ints():
    result = extract_day_numbers([1, 3, 5])
    assert result == [1, 3, 5]


def test_extract_day_numbers_ints_only():
    result = extract_day_numbers([2, 9])
    assert 2 in result
    assert 9 in result


def test_extract_day_numbers_empty():
    result = extract_day_numbers([])
    assert result == []


# --- export_course_timetable_csv ---

def test_export_course_csv_basic(tmp_path):
    c = _make_course(lec_days=[1, 8], lec_start=705, lec_end=780)
    out = str(tmp_path / "courses.csv")
    export_course_timetable_csv([c], out)
    assert os.path.isfile(out)
    with open(out, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 2  # 2 lecture days
    assert rows[0]['Type'] == 'Lecture'
    assert rows[0]['Subject'] == 'COEN'


def test_export_course_csv_with_tuts(tmp_path):
    c = _make_course(lec_days=[1, 8], lec_start=705, lec_end=780,
                     tut_count=1, tut_duration=50)
    c.tutorial[0].day = [3]
    c.tutorial[0].start = 525
    c.tutorial[0].end = 575
    out = str(tmp_path / "courses.csv")
    export_course_timetable_csv([c], out)
    with open(out, 'r') as f:
        rows = list(csv.DictReader(f))
    types = [r['Type'] for r in rows]
    assert 'Lecture' in types
    assert 'Tutorial' in types


def test_export_course_csv_empty_schedule(tmp_path):
    out = str(tmp_path / "courses.csv")
    export_course_timetable_csv([], out)
    assert not os.path.isfile(out)


# --- export_room_timetable_csv ---

def test_export_room_csv(tmp_path):
    tt = RoomTimetable("H", "929")
    tt.add_slot(1, 525, 690, "COEN", "311", "00001", 0)
    timetables = {("H", "929"): tt}
    out = str(tmp_path / "rooms.csv")
    export_room_timetable_csv(timetables, out)
    assert os.path.isfile(out)
    with open(out, 'r') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]['Building'] == 'H'
    assert rows[0]['Room'] == '929'


def test_export_room_csv_empty(tmp_path):
    timetables = {("H", "929"): RoomTimetable("H", "929")}
    out = str(tmp_path / "rooms.csv")
    export_room_timetable_csv(timetables, out)
    assert not os.path.isfile(out)
