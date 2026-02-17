import random
from course_element import CourseElement
from course import Course
from day import Day
from mutation import (
    times_overlap,
    is_core_sequence_course,
    has_internal_overlap,
    reschedule_course_safely,
    mutate,
    mutate_population,
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


# --- times_overlap ---

def test_times_overlap_true():
    e1 = CourseElement(day=[1], start=525, end=690)
    e2 = CourseElement(day=[1], start=600, end=765)
    assert times_overlap(e1, e2) is True


def test_times_overlap_none():
    e1 = CourseElement(day=[1], start=525, end=690)
    assert times_overlap(e1, None) is False


# --- is_core_sequence_course ---

def test_is_core_true():
    c = _make_course(subject="COEN", catalog="212")
    sequences = [["COEN212", "COEN231", "COEN243"]]
    assert is_core_sequence_course(c, sequences) is True


def test_is_core_false():
    c = _make_course(subject="COEN", catalog="311")
    sequences = [["COEN212", "COEN231", "COEN243"]]
    assert is_core_sequence_course(c, sequences) is False


def test_is_core_empty_sequences():
    c = _make_course(subject="COEN", catalog="212")
    assert is_core_sequence_course(c, []) is False


# --- has_internal_overlap ---

def test_no_internal_overlap():
    c = _make_course(tut_count=1, weekly_tut_freq=1, tut_duration=50)
    c.tutorial[0].day = [3]
    c.tutorial[0].start = 525
    c.tutorial[0].end = 575
    assert has_internal_overlap(c) is False


def test_internal_overlap_tut_lab():
    c = _make_course(
        tut_count=1, weekly_tut_freq=1, tut_duration=50,
        lab_count=1, biweekly_lab_freq=1, lab_duration=165,
    )
    c.tutorial[0].day = [1]
    c.tutorial[0].start = 525
    c.tutorial[0].end = 575
    c.lab[0].day = [1]
    c.lab[0].start = 525
    c.lab[0].end = 690
    assert has_internal_overlap(c) is True


def test_no_internal_overlap_different_days():
    c = _make_course(
        tut_count=1, weekly_tut_freq=1, tut_duration=50,
        lab_count=1, biweekly_lab_freq=1, lab_duration=165,
    )
    c.tutorial[0].day = [1]
    c.tutorial[0].start = 525
    c.tutorial[0].end = 575
    c.lab[0].day = [2]
    c.lab[0].start = 525
    c.lab[0].end = 690
    assert has_internal_overlap(c) is False


# --- reschedule_course_safely ---

def test_reschedule_returns_course():
    random.seed(42)
    c = _make_course(
        lecture_days=(Day.MO,), lec_start=705, lec_end=780,
        tut_count=1, weekly_tut_freq=1, tut_duration=50,
    )
    result = reschedule_course_safely(c, max_attempts=50)
    assert result.subject == "COEN"
    assert result.tutorial[0].end > 0


# --- mutate ---

def test_mutate_non_core_course():
    random.seed(42)
    c1 = _make_course(subject="COEN", catalog="311",
                      tut_count=1, weekly_tut_freq=1, tut_duration=50)
    c2 = _make_course(subject="COEN", catalog="390",
                      tut_count=1, weekly_tut_freq=1, tut_duration=50)
    core_seqs = [["COEN212", "COEN231"]]
    result = mutate([c1, c2], core_seqs, mutation_count=1)
    assert len(result) == 2


def test_mutate_all_core_no_change():
    c = _make_course(subject="COEN", catalog="212")
    core_seqs = [["COEN212"]]
    result = mutate([c], core_seqs, mutation_count=1)
    assert result == [c]


# --- mutate_population ---

def test_mutate_population_preserves_size():
    random.seed(42)
    c1 = _make_course(subject="COEN", catalog="311")
    c2 = _make_course(subject="COEN", catalog="390")
    population = [[c1, c2], [c1, c2], [c1, c2]]
    core_seqs = [["COEN212"]]
    result = mutate_population(population, core_seqs, mutation_rate=0.5)
    assert len(result) == 3


def test_mutate_population_zero_rate():
    c = _make_course(subject="COEN", catalog="311")
    population = [[c]]
    core_seqs = [["COEN212"]]
    result = mutate_population(population, core_seqs, mutation_rate=0.0)
    assert result[0][0] is c
