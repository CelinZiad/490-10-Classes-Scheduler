import random
import pytest
from course_element import CourseElement
from course import Course
from day import Day
from initialization import (
    get_lab_days_for_frequency,
    check_room_conflict,
    times_overlap,
    has_valid_lab_tut_combination,
    find_conflict_free_lab_slot,
    insert_tut_into_timetable,
    insert_lab_into_timetable,
    initialize_course_with_validation,
)


def _make_course(subject="COEN", catalog="311", lecture_days=(Day.TU, Day.TH),
                 lec_start=705, lec_end=780, lab_count=0, biweekly_lab_freq=0,
                 lab_duration=0, tut_count=0, weekly_tut_freq=0, tut_duration=0):
    lecture = CourseElement(day=lecture_days, start=lec_start, end=lec_end)
    labs = tuple(CourseElement(day=[], start=0, end=0) for _ in range(lab_count))
    tuts = tuple(CourseElement(day=[], start=0, end=0) for _ in range(tut_count))
    return Course(
        subject=subject, catalog_nbr=catalog, class_nbr="00001",
        lecture=lecture, lab=labs, tutorial=tuts,
        lab_count=lab_count, biweekly_lab_freq=biweekly_lab_freq,
        lab_duration=lab_duration, tut_count=tut_count,
        weekly_tut_freq=weekly_tut_freq, tut_duration=tut_duration,
    )


# --- get_lab_days_for_frequency ---

def test_lab_days_freq_1():
    assert get_lab_days_for_frequency(1, 3) == [3]


def test_lab_days_freq_2_week1():
    assert get_lab_days_for_frequency(2, 3) == [3, 10]


def test_lab_days_freq_2_week2():
    assert get_lab_days_for_frequency(2, 10) == [3, 10]


def test_lab_days_freq_other():
    assert get_lab_days_for_frequency(3, 5) == [5]


# --- check_room_conflict ---

def test_room_conflict_none_timetable():
    assert check_room_conflict(1, 525, 690, None) is False


def test_room_conflict_overlap():
    timetable = {("H", "929"): [{"day": 1, "start": 600, "end": 765}]}
    assert check_room_conflict(1, 700, 865, timetable) is True


def test_room_conflict_no_overlap():
    timetable = {("H", "929"): [{"day": 1, "start": 525, "end": 690}]}
    assert check_room_conflict(1, 700, 865, timetable) is False


def test_room_conflict_different_day():
    timetable = {("H", "929"): [{"day": 1, "start": 525, "end": 690}]}
    assert check_room_conflict(2, 525, 690, timetable) is False


# --- times_overlap ---

def test_times_overlap_true():
    e1 = CourseElement(day=[1], start=525, end=690)
    e2 = CourseElement(day=[1], start=600, end=765)
    assert times_overlap(e1, e2) is True


def test_times_overlap_false_different_day():
    e1 = CourseElement(day=[1], start=525, end=690)
    e2 = CourseElement(day=[2], start=525, end=690)
    assert times_overlap(e1, e2) is False


def test_times_overlap_false_adjacent():
    e1 = CourseElement(day=[1], start=525, end=690)
    e2 = CourseElement(day=[1], start=690, end=855)
    assert times_overlap(e1, e2) is False


# --- has_valid_lab_tut_combination ---

def test_valid_combo_no_labs_no_tuts():
    course = _make_course()
    assert has_valid_lab_tut_combination(course) is True


def test_valid_combo_non_overlapping():
    course = _make_course(lab_count=1, lab_duration=165, tut_count=1, tut_duration=50)
    course.lab[0].day = [1]
    course.lab[0].start = 525
    course.lab[0].end = 690
    course.tutorial[0].day = [2]
    course.tutorial[0].start = 525
    course.tutorial[0].end = 575
    assert has_valid_lab_tut_combination(course) is True


def test_valid_combo_overlapping():
    course = _make_course(lab_count=1, lab_duration=165, tut_count=1, tut_duration=50)
    course.lab[0].day = [1]
    course.lab[0].start = 525
    course.lab[0].end = 690
    course.tutorial[0].day = [1]
    course.tutorial[0].start = 600
    course.tutorial[0].end = 650
    assert has_valid_lab_tut_combination(course) is False


# --- find_conflict_free_lab_slot ---

def test_find_slot_returns_none_when_all_conflict():
    course = _make_course(
        lecture_days=(Day.MO, Day.TU, Day.WE, Day.TH, Day.FR),
        lec_start=0, lec_end=1440,
        lab_count=1, biweekly_lab_freq=1, lab_duration=165,
    )
    result = find_conflict_free_lab_slot(course, 0, max_attempts=10)
    assert result is None


def test_find_slot_returns_valid_tuple():
    random.seed(42)
    course = _make_course(
        lecture_days=(Day.MO,), lec_start=705, lec_end=780,
        lab_count=1, biweekly_lab_freq=1, lab_duration=165,
    )
    result = find_conflict_free_lab_slot(course, 0, max_attempts=100)
    assert result is not None
    days, start, end = result
    assert isinstance(days, list)
    assert end - start == 165


# --- insert_tut_into_timetable (loop termination) ---

def test_insert_tut_terminates(monkeypatch):
    course = _make_course(
        lecture_days=(Day.MO, Day.TU, Day.WE, Day.TH, Day.FR),
        lec_start=0, lec_end=1440,
        tut_count=1, weekly_tut_freq=1, tut_duration=50,
    )
    random.seed(0)
    insert_tut_into_timetable(course)
    assert course.tutorial[0].end > 0


def test_insert_tut_sets_day_and_time():
    random.seed(42)
    course = _make_course(
        lecture_days=(Day.MO,), lec_start=705, lec_end=780,
        tut_count=1, weekly_tut_freq=1, tut_duration=50,
    )
    insert_tut_into_timetable(course)
    assert len(course.tutorial[0].day) == 2
    assert course.tutorial[0].end - course.tutorial[0].start == 50


# --- insert_lab_into_timetable (loop termination) ---

def test_insert_lab_terminates():
    course = _make_course(
        lecture_days=(Day.MO, Day.TU, Day.WE, Day.TH, Day.FR),
        lec_start=0, lec_end=1440,
        lab_count=1, biweekly_lab_freq=1, lab_duration=165,
    )
    random.seed(0)
    insert_lab_into_timetable(course)
    assert course.lab[0].end > 0


def test_insert_lab_sets_day_and_time():
    random.seed(42)
    course = _make_course(
        lecture_days=(Day.MO,), lec_start=705, lec_end=780,
        lab_count=1, biweekly_lab_freq=1, lab_duration=165,
    )
    insert_lab_into_timetable(course)
    assert len(course.lab[0].day) >= 1
    assert course.lab[0].end - course.lab[0].start == 165


# --- insert_tut 100-minute variant ---

def test_insert_tut_100min():
    random.seed(42)
    course = _make_course(
        lecture_days=(Day.MO,), lec_start=705, lec_end=780,
        tut_count=1, weekly_tut_freq=1, tut_duration=100,
    )
    insert_tut_into_timetable(course)
    assert course.tutorial[0].end - course.tutorial[0].start == 100


def test_insert_tut_different_day_no_conflict():
    random.seed(10)
    course = _make_course(
        lecture_days=(Day.MO,), lec_start=705, lec_end=780,
        tut_count=1, weekly_tut_freq=1, tut_duration=50,
    )
    insert_tut_into_timetable(course)
    assert course.tutorial[0].end > 0


# --- insert_lab 100-minute variant ---

def test_insert_lab_100min():
    random.seed(42)
    course = _make_course(
        lecture_days=(Day.MO,), lec_start=705, lec_end=780,
        lab_count=1, biweekly_lab_freq=1, lab_duration=100,
    )
    insert_lab_into_timetable(course)
    assert course.lab[0].end - course.lab[0].start == 100


# --- find_conflict_free_lab_slot with 100min labs ---

def test_find_slot_100min():
    random.seed(42)
    course = _make_course(
        lecture_days=(Day.MO,), lec_start=705, lec_end=780,
        lab_count=1, biweekly_lab_freq=1, lab_duration=100,
    )
    result = find_conflict_free_lab_slot(course, 0, max_attempts=100)
    assert result is not None
    days, start, end = result
    assert end - start == 100


# --- find_conflict_free_lab_slot with room timetable ---

def test_find_slot_with_room_conflict():
    random.seed(42)
    course = _make_course(
        lecture_days=(Day.MO,), lec_start=705, lec_end=780,
        lab_count=1, biweekly_lab_freq=2, lab_duration=165,
    )
    room_timetable = {("H", "929"): [
        {"day": d, "start": 0, "end": 1440} for d in range(1, 13)
    ]}
    result = find_conflict_free_lab_slot(course, 0, room_timetable, max_attempts=10)
    assert result is None


# --- initialize_course_with_validation ---

def test_initialize_course_with_validation_simple():
    random.seed(42)
    course = _make_course(
        lecture_days=(Day.MO,), lec_start=705, lec_end=780,
        tut_count=1, weekly_tut_freq=1, tut_duration=50,
        lab_count=1, biweekly_lab_freq=1, lab_duration=165,
    )
    result = initialize_course_with_validation(course, max_attempts=50)
    assert result is True


def test_initialize_course_no_labs_no_tuts():
    course = _make_course(lecture_days=(Day.MO,), lec_start=705, lec_end=780)
    result = initialize_course_with_validation(course, max_attempts=10)
    assert result is True
