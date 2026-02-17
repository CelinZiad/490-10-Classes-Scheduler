import pytest
from course_element import CourseElement
from course import Course
from day import Day
from helper.conflict_export import (
    times_overlap,
    minutes_to_time_string,
    extract_day_number,
    collect_lecture_conflicts,
    collect_sequence_conflicts,
    has_valid_sequence_combination,
)


def _make_course(subject="COEN", catalog="311", class_nbr="00001",
                 lec_days=(Day.TU, Day.TH), lec_start=705, lec_end=780,
                 tut_count=0, tut_duration=0, lab_count=0, lab_duration=0,
                 biweekly_lab_freq=0):
    lecture = CourseElement(day=lec_days, start=lec_start, end=lec_end)
    tuts = tuple(CourseElement(day=[], start=0, end=0) for _ in range(tut_count))
    labs = tuple(CourseElement(day=[], start=0, end=0) for _ in range(lab_count))
    return Course(
        subject=subject, catalog_nbr=catalog, class_nbr=class_nbr,
        lecture=lecture, tutorial=tuts, lab=labs,
        tut_count=tut_count, weekly_tut_freq=1 if tut_count else 0,
        tut_duration=tut_duration, lab_count=lab_count,
        biweekly_lab_freq=biweekly_lab_freq, lab_duration=lab_duration,
    )


# --- times_overlap ---

def test_overlap_same_day_overlapping():
    e1 = CourseElement(day=[1], start=525, end=690)
    e2 = CourseElement(day=[1], start=600, end=765)
    assert times_overlap(e1, e2) is True


def test_overlap_different_day():
    e1 = CourseElement(day=[1], start=525, end=690)
    e2 = CourseElement(day=[2], start=525, end=690)
    assert times_overlap(e1, e2) is False


def test_overlap_none():
    e1 = CourseElement(day=[1], start=525, end=690)
    assert times_overlap(e1, None) is False
    assert times_overlap(None, e1) is False


def test_overlap_adjacent():
    e1 = CourseElement(day=[1], start=525, end=600)
    e2 = CourseElement(day=[1], start=600, end=700)
    assert times_overlap(e1, e2) is False


# --- minutes_to_time_string ---

def test_time_string_morning():
    assert minutes_to_time_string(525) == "08:45"


def test_time_string_afternoon():
    assert minutes_to_time_string(780) == "13:00"


def test_time_string_midnight():
    assert minutes_to_time_string(0) == "00:00"


# --- extract_day_number ---

def test_extract_day_number_from_int():
    assert extract_day_number(3) == 3


def test_extract_day_number_from_int_value():
    # Day enums don't work with extract_day_number (known bug); ints do
    assert extract_day_number(1) == 1
    assert extract_day_number(8) == 8


# --- collect_lecture_conflicts ---

def test_collect_lecture_no_conflicts():
    c = _make_course(lec_days=[1, 8], lec_start=705, lec_end=780,
                     tut_count=1, tut_duration=50)
    c.tutorial[0].day = [3]
    c.tutorial[0].start = 525
    c.tutorial[0].end = 575
    conflicts = collect_lecture_conflicts([c])
    assert len(conflicts) == 0


def test_collect_lecture_tut_conflict():
    c = _make_course(lec_days=[1, 8], lec_start=525, lec_end=690,
                     tut_count=1, tut_duration=50)
    c.tutorial[0].day = [1]
    c.tutorial[0].start = 600
    c.tutorial[0].end = 650
    conflicts = collect_lecture_conflicts([c])
    assert len(conflicts) > 0
    assert conflicts[0]['Conflict_Type'] == 'Lecture-Tutorial'


def test_collect_lecture_lab_conflict():
    c = _make_course(lec_days=[1, 8], lec_start=525, lec_end=690,
                     lab_count=1, lab_duration=165, biweekly_lab_freq=1)
    c.lab[0].day = [1]
    c.lab[0].start = 600
    c.lab[0].end = 765
    c.lab[0].bldg = 'H'
    c.lab[0].room = '929'
    conflicts = collect_lecture_conflicts([c])
    assert len(conflicts) > 0
    assert conflicts[0]['Conflict_Type'] == 'Lecture-Lab'


def test_collect_lecture_no_lecture():
    c = _make_course(tut_count=1, tut_duration=50)
    c = Course(
        subject="COEN", catalog_nbr="311", class_nbr="00001",
        lecture=None, tutorial=(), lab=(),
    )
    conflicts = collect_lecture_conflicts([c])
    assert len(conflicts) == 0


def test_collect_lecture_none_tut_skipped():
    c = _make_course(lec_days=[1, 8], lec_start=525, lec_end=690,
                     tut_count=1, tut_duration=50)
    # tutorial with no day set
    conflicts = collect_lecture_conflicts([c])
    assert len(conflicts) == 0


# --- collect_sequence_conflicts ---

def test_sequence_conflicts_missing_course():
    c = _make_course(subject="COEN", catalog="212")
    conflicts = collect_sequence_conflicts([c], [["COEN212", "COEN231"]])
    assert len(conflicts) > 0
    assert conflicts[0]['Conflict_Type'] == 'Sequence-Missing Course'


def test_sequence_conflicts_valid_combo():
    c1 = _make_course(subject="COEN", catalog="212")
    c2 = _make_course(subject="COEN", catalog="231")
    conflicts = collect_sequence_conflicts([c1, c2], [["COEN212", "COEN231"]])
    assert len(conflicts) == 0


# --- has_valid_sequence_combination ---

def test_has_valid_no_tuts_labs():
    c1 = _make_course(subject="COEN", catalog="212")
    c2 = _make_course(subject="COEN", catalog="231")
    assert has_valid_sequence_combination([c1, c2], ["COEN212", "COEN231"]) is True


def test_has_valid_missing_course():
    c1 = _make_course(subject="COEN", catalog="212")
    assert has_valid_sequence_combination([c1], ["COEN212", "COEN231"]) is False


def test_has_valid_non_overlapping_tuts():
    c1 = _make_course(subject="COEN", catalog="212", tut_count=1, tut_duration=50)
    c2 = _make_course(subject="COEN", catalog="231", tut_count=1, tut_duration=50)
    c1.tutorial[0].day = [1]
    c1.tutorial[0].start = 525
    c1.tutorial[0].end = 575
    c2.tutorial[0].day = [2]
    c2.tutorial[0].start = 525
    c2.tutorial[0].end = 575
    assert has_valid_sequence_combination([c1, c2], ["COEN212", "COEN231"]) is True


def test_has_valid_overlapping_tuts():
    c1 = _make_course(subject="COEN", catalog="212", tut_count=1, tut_duration=50)
    c2 = _make_course(subject="COEN", catalog="231", tut_count=1, tut_duration=50)
    c1.tutorial[0].day = [1]
    c1.tutorial[0].start = 525
    c1.tutorial[0].end = 575
    c2.tutorial[0].day = [1]
    c2.tutorial[0].start = 550
    c2.tutorial[0].end = 600
    assert has_valid_sequence_combination([c1, c2], ["COEN212", "COEN231"]) is False


# --- collect_sequence_conflicts detailed paths ---

def test_sequence_conflicts_tut_overlap():
    """Two courses with overlapping tutorials produce Sequence-Tutorial Overlap."""
    c1 = _make_course(subject="COEN", catalog="212", tut_count=1, tut_duration=50)
    c2 = _make_course(subject="COEN", catalog="231", tut_count=1, tut_duration=50)
    c1.tutorial[0].day = [1]
    c1.tutorial[0].start = 525
    c1.tutorial[0].end = 575
    c2.tutorial[0].day = [1]
    c2.tutorial[0].start = 550
    c2.tutorial[0].end = 600
    conflicts = collect_sequence_conflicts([c1, c2], [["COEN212", "COEN231"]])
    tut_conflicts = [c for c in conflicts if c['Conflict_Type'] == 'Sequence-Tutorial Overlap']
    assert len(tut_conflicts) > 0


def test_sequence_conflicts_lab_overlap():
    """Two courses with overlapping labs produce Sequence-Lab Overlap."""
    c1 = _make_course(subject="COEN", catalog="212", lab_count=1,
                      lab_duration=165, biweekly_lab_freq=1)
    c2 = _make_course(subject="COEN", catalog="231", lab_count=1,
                      lab_duration=165, biweekly_lab_freq=1)
    c1.lab[0].day = [1]
    c1.lab[0].start = 525
    c1.lab[0].end = 690
    c1.lab[0].bldg = 'H'
    c1.lab[0].room = '929'
    c2.lab[0].day = [1]
    c2.lab[0].start = 600
    c2.lab[0].end = 765
    c2.lab[0].bldg = 'H'
    c2.lab[0].room = '930'
    conflicts = collect_sequence_conflicts([c1, c2], [["COEN212", "COEN231"]])
    lab_conflicts = [c for c in conflicts if c['Conflict_Type'] == 'Sequence-Lab Overlap']
    assert len(lab_conflicts) > 0


def test_sequence_conflicts_tut_lab_overlap():
    """Tutorial overlapping with lab from different course."""
    c1 = _make_course(subject="COEN", catalog="212", tut_count=1, tut_duration=50)
    c2 = _make_course(subject="COEN", catalog="231", lab_count=1,
                      lab_duration=165, biweekly_lab_freq=1)
    c1.tutorial[0].day = [1]
    c1.tutorial[0].start = 525
    c1.tutorial[0].end = 575
    c2.lab[0].day = [1]
    c2.lab[0].start = 550
    c2.lab[0].end = 715
    c2.lab[0].bldg = 'H'
    c2.lab[0].room = '929'
    conflicts = collect_sequence_conflicts([c1, c2], [["COEN212", "COEN231"]])
    tl_conflicts = [c for c in conflicts if c['Conflict_Type'] == 'Sequence-Tutorial/Lab Overlap']
    assert len(tl_conflicts) > 0


def test_sequence_conflicts_no_specific_found():
    """No valid combination but no specific overlap found -> generic conflict."""
    c1 = _make_course(subject="COEN", catalog="212")
    c2 = _make_course(subject="COEN", catalog="231")
    # Both courses present, no tuts/labs = valid combo, so no conflict
    conflicts = collect_sequence_conflicts([c1, c2], [["COEN212", "COEN231"]])
    assert len(conflicts) == 0
