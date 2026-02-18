import random
import pytest
from copy import deepcopy
from course_element import CourseElement
from course import Course
from day import Day
from recombination import (
    times_overlap,
    has_valid_sequence_combination,
    is_core_sequence_course,
    uniform_crossover,
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


# --- times_overlap ---

def test_overlap_true():
    e1 = CourseElement(day=[1], start=525, end=690)
    e2 = CourseElement(day=[1], start=600, end=765)
    assert times_overlap(e1, e2) is True


def test_overlap_none():
    e1 = CourseElement(day=[1], start=525, end=690)
    assert times_overlap(e1, None) is False


def test_overlap_diff_day():
    e1 = CourseElement(day=[1], start=525, end=690)
    e2 = CourseElement(day=[2], start=525, end=690)
    assert times_overlap(e1, e2) is False


# --- has_valid_sequence_combination ---

def test_valid_combo_no_components():
    c1 = _make_course(subject="COEN", catalog="212")
    c2 = _make_course(subject="COEN", catalog="231")
    assert has_valid_sequence_combination([c1, c2], ["COEN212", "COEN231"]) is True


def test_valid_combo_missing():
    c1 = _make_course(subject="COEN", catalog="212")
    assert has_valid_sequence_combination([c1], ["COEN212", "COEN231"]) is False


def test_valid_combo_non_overlap():
    c1 = _make_course(subject="COEN", catalog="212", tut_count=1, tut_duration=50)
    c2 = _make_course(subject="COEN", catalog="231", tut_count=1, tut_duration=50)
    c1.tutorial[0].day = [1]
    c1.tutorial[0].start = 525
    c1.tutorial[0].end = 575
    c2.tutorial[0].day = [2]
    c2.tutorial[0].start = 525
    c2.tutorial[0].end = 575
    assert has_valid_sequence_combination([c1, c2], ["COEN212", "COEN231"]) is True


def test_valid_combo_overlap():
    c1 = _make_course(subject="COEN", catalog="212", tut_count=1, tut_duration=50)
    c2 = _make_course(subject="COEN", catalog="231", tut_count=1, tut_duration=50)
    c1.tutorial[0].day = [1]
    c1.tutorial[0].start = 525
    c1.tutorial[0].end = 575
    c2.tutorial[0].day = [1]
    c2.tutorial[0].start = 550
    c2.tutorial[0].end = 600
    assert has_valid_sequence_combination([c1, c2], ["COEN212", "COEN231"]) is False


# --- is_core_sequence_course ---

def test_is_core_true():
    c = _make_course(subject="COEN", catalog="212")
    is_core, seq = is_core_sequence_course(c, [["COEN212", "COEN231"]])
    assert is_core is True
    assert "COEN212" in seq


def test_is_core_false():
    c = _make_course(subject="COEN", catalog="390")
    is_core, seq = is_core_sequence_course(c, [["COEN212", "COEN231"]])
    assert is_core is False
    assert seq is None


# --- uniform_crossover ---

def test_crossover_same_parents():
    random.seed(42)
    c1 = _make_course(subject="COEN", catalog="212")
    c2 = _make_course(subject="COEN", catalog="212")
    parent1 = [c1]
    parent2 = [c2]
    offspring = uniform_crossover(parent1, parent2, core_sequences=[])
    assert len(offspring) == 1
    assert offspring[0].subject == "COEN"
    assert offspring[0].catalog_nbr == "212"


def test_crossover_preserves_length():
    random.seed(42)
    c1a = _make_course(subject="COEN", catalog="212")
    c1b = _make_course(subject="COEN", catalog="311")
    c2a = _make_course(subject="COEN", catalog="212")
    c2b = _make_course(subject="COEN", catalog="311")
    parent1 = [c1a, c1b]
    parent2 = [c2a, c2b]
    offspring = uniform_crossover(parent1, parent2, core_sequences=[])
    assert len(offspring) == 2


def test_crossover_mismatched_raises():
    c1 = _make_course(subject="COEN", catalog="212")
    c2 = _make_course(subject="COEN", catalog="311")
    with pytest.raises(ValueError, match="mismatched"):
        uniform_crossover([c1], [c2], core_sequences=[])
