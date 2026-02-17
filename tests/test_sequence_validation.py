from course_element import CourseElement
from course import Course
from day import Day
from sequence import Sequence
from sequence_validation import (
    times_overlap,
    get_course_by_code,
    check_elements_overlap,
    has_valid_sequence_combination,
    validate_all_sequences,
)


def _make_course(subject="COEN", catalog="311", lec_start=705, lec_end=780,
                 tut_count=0, tut_duration=0, lab_count=0, lab_duration=0):
    lecture = CourseElement(day=(Day.TU, Day.TH), start=lec_start, end=lec_end)
    tuts = tuple(CourseElement(day=[], start=0, end=0) for _ in range(tut_count))
    labs = tuple(CourseElement(day=[], start=0, end=0) for _ in range(lab_count))
    return Course(
        subject=subject, catalog_nbr=catalog, class_nbr="00001",
        lecture=lecture, tutorial=tuts, lab=labs,
        tut_count=tut_count, weekly_tut_freq=1 if tut_count else 0,
        tut_duration=tut_duration, lab_count=lab_count,
        biweekly_lab_freq=1 if lab_count else 0, lab_duration=lab_duration,
    )


def test_get_course_by_code_found():
    c = _make_course(subject="COEN", catalog="212")
    schedule = [c]
    assert get_course_by_code(schedule, "COEN212") is c


def test_get_course_by_code_not_found():
    c = _make_course(subject="COEN", catalog="212")
    schedule = [c]
    assert get_course_by_code(schedule, "COEN311") is None


def test_check_elements_overlap_true():
    e = CourseElement(day=[1], start=525, end=690)
    others = [CourseElement(day=[1], start=600, end=765)]
    assert check_elements_overlap(e, others) is True


def test_check_elements_overlap_false():
    e = CourseElement(day=[1], start=525, end=690)
    others = [CourseElement(day=[2], start=525, end=690)]
    assert check_elements_overlap(e, others) is False


def test_valid_sequence_no_tuts_no_labs():
    c1 = _make_course(subject="COEN", catalog="212")
    c2 = _make_course(subject="COEN", catalog="231")
    schedule = [c1, c2]
    assert has_valid_sequence_combination(schedule, ["COEN212", "COEN231"]) is True


def test_valid_sequence_missing_course():
    c1 = _make_course(subject="COEN", catalog="212")
    schedule = [c1]
    assert has_valid_sequence_combination(schedule, ["COEN212", "COEN231"]) is False


def test_valid_sequence_non_overlapping_tuts():
    c1 = _make_course(subject="COEN", catalog="212", tut_count=1, tut_duration=50)
    c2 = _make_course(subject="COEN", catalog="231", tut_count=1, tut_duration=50)
    c1.tutorial[0].day = [1]
    c1.tutorial[0].start = 525
    c1.tutorial[0].end = 575
    c2.tutorial[0].day = [2]
    c2.tutorial[0].start = 525
    c2.tutorial[0].end = 575
    schedule = [c1, c2]
    assert has_valid_sequence_combination(schedule, ["COEN212", "COEN231"]) is True


def test_valid_sequence_overlapping_tuts():
    c1 = _make_course(subject="COEN", catalog="212", tut_count=1, tut_duration=50)
    c2 = _make_course(subject="COEN", catalog="231", tut_count=1, tut_duration=50)
    c1.tutorial[0].day = [1]
    c1.tutorial[0].start = 525
    c1.tutorial[0].end = 575
    c2.tutorial[0].day = [1]
    c2.tutorial[0].start = 550
    c2.tutorial[0].end = 600
    schedule = [c1, c2]
    assert has_valid_sequence_combination(schedule, ["COEN212", "COEN231"]) is False


# --- Sequence class ---

def test_sequence_data():
    assert len(Sequence.year) == 2
    assert "COEN212" in Sequence.year[0]
    assert "COEN311" in Sequence.year[1]


# --- validate_all_sequences ---

def test_validate_all_sequences_all_present():
    courses = []
    for code in ["COEN212", "COEN231", "COEN243", "COEN244", "COEN311", "ELEC273"]:
        subject = ''.join(c for c in code if c.isalpha())
        catalog = ''.join(c for c in code if c.isdigit())
        courses.append(_make_course(subject=subject, catalog=catalog))
    results = validate_all_sequences(courses, Sequence)
    assert results["Semester 1"] is True
    assert results["Semester 2"] is True


def test_validate_all_sequences_missing_course():
    c1 = _make_course(subject="COEN", catalog="212")
    results = validate_all_sequences([c1], Sequence)
    assert results["Semester 1"] is False
    assert results["Semester 2"] is False
