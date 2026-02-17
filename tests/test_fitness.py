from course_element import CourseElement
from course import Course
from day import Day
from fitness import (
    calculate_variety_score,
    times_overlap,
    count_lecture_conflicts,
    get_course_by_code,
    has_valid_sequence_combination,
    fitness_function,
    evaluate_population,
    count_sequence_conflicts,
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


# --- calculate_variety_score ---

def test_variety_score_single_element():
    elements = [CourseElement(day=[1], start=525, end=690)]
    assert calculate_variety_score(elements) == 1.0


def test_variety_score_empty():
    assert calculate_variety_score([]) == 1.0


def test_variety_score_varied():
    elements = [
        CourseElement(day=[1], start=525, end=690),
        CourseElement(day=[2], start=705, end=870),
    ]
    score = calculate_variety_score(elements)
    assert score > 0.5


def test_variety_score_identical():
    elements = [
        CourseElement(day=[1], start=525, end=690),
        CourseElement(day=[1], start=525, end=690),
    ]
    score = calculate_variety_score(elements)
    assert score < 1.0


# --- times_overlap ---

def test_times_overlap_true():
    e1 = CourseElement(day=[1], start=525, end=690)
    e2 = CourseElement(day=[1], start=600, end=765)
    assert times_overlap(e1, e2) is True


def test_times_overlap_none_element():
    e1 = CourseElement(day=[1], start=525, end=690)
    assert times_overlap(e1, None) is False
    assert times_overlap(None, e1) is False


# --- count_lecture_conflicts ---

def test_no_lecture_conflicts():
    course = _make_course(
        lecture_days=(Day.MO,), lec_start=705, lec_end=780,
        tut_count=1, weekly_tut_freq=1, tut_duration=50,
    )
    course.tutorial[0].day = [2]
    course.tutorial[0].start = 525
    course.tutorial[0].end = 575
    assert count_lecture_conflicts(course) == 0


def test_lecture_tut_conflict_same_day_type():
    """Lecture and tut use same day type (both ints) to detect overlap."""
    course = _make_course(
        lecture_days=[1, 8], lec_start=705, lec_end=780,
        tut_count=1, weekly_tut_freq=1, tut_duration=50,
    )
    course.tutorial[0].day = [1]
    course.tutorial[0].start = 720
    course.tutorial[0].end = 770
    assert count_lecture_conflicts(course) == 1


def test_lecture_lab_conflict_same_day_type():
    """Lecture and lab use same day type (both ints) to detect overlap."""
    course = _make_course(
        lecture_days=[2, 9], lec_start=705, lec_end=780,
        lab_count=1, biweekly_lab_freq=1, lab_duration=165,
    )
    course.lab[0].day = [2]
    course.lab[0].start = 700
    course.lab[0].end = 865
    assert count_lecture_conflicts(course) == 1


# --- get_course_by_code ---

def test_get_course_found():
    c = _make_course(subject="COEN", catalog="311")
    schedule = [c]
    assert get_course_by_code(schedule, "COEN311") is c


def test_get_course_not_found():
    c = _make_course(subject="COEN", catalog="311")
    schedule = [c]
    assert get_course_by_code(schedule, "COEN212") is None


# --- fitness_function ---

def test_fitness_no_conflicts():
    c = _make_course(tut_count=2, weekly_tut_freq=1, tut_duration=50)
    c.tutorial[0].day = [1]
    c.tutorial[0].start = 525
    c.tutorial[0].end = 575
    c.tutorial[1].day = [3]
    c.tutorial[1].start = 705
    c.tutorial[1].end = 755
    score = fitness_function([c])
    assert score > 0


def test_fitness_empty_schedule():
    assert fitness_function([]) == 0.0


def test_fitness_with_conflicts():
    """Use int days for both lecture and tut so times_overlap detects the conflict."""
    c = _make_course(
        lecture_days=[1, 8], lec_start=525, lec_end=690,
        tut_count=1, weekly_tut_freq=1, tut_duration=50,
    )
    c.tutorial[0].day = [1]
    c.tutorial[0].start = 600
    c.tutorial[0].end = 650
    score = fitness_function([c])
    assert score < 0


# --- has_valid_sequence_combination ---

def test_sequence_combo_no_components():
    c1 = _make_course(subject="COEN", catalog="212")
    c2 = _make_course(subject="COEN", catalog="231")
    assert has_valid_sequence_combination([c1, c2], ["COEN212", "COEN231"]) is True


def test_sequence_combo_non_overlapping_tuts():
    c1 = _make_course(subject="COEN", catalog="212", tut_count=1, tut_duration=50)
    c2 = _make_course(subject="COEN", catalog="231", tut_count=1, tut_duration=50)
    c1.tutorial[0].day = [1]
    c1.tutorial[0].start = 525
    c1.tutorial[0].end = 575
    c2.tutorial[0].day = [2]
    c2.tutorial[0].start = 525
    c2.tutorial[0].end = 575
    assert has_valid_sequence_combination([c1, c2], ["COEN212", "COEN231"]) is True


def test_sequence_combo_overlapping_tuts():
    c1 = _make_course(subject="COEN", catalog="212", tut_count=1, tut_duration=50)
    c2 = _make_course(subject="COEN", catalog="231", tut_count=1, tut_duration=50)
    c1.tutorial[0].day = [1]
    c1.tutorial[0].start = 525
    c1.tutorial[0].end = 575
    c2.tutorial[0].day = [1]
    c2.tutorial[0].start = 550
    c2.tutorial[0].end = 600
    assert has_valid_sequence_combination([c1, c2], ["COEN212", "COEN231"]) is False


def test_sequence_combo_non_overlapping_labs():
    c1 = _make_course(subject="COEN", catalog="212", lab_count=1, lab_duration=165)
    c2 = _make_course(subject="COEN", catalog="231", lab_count=1, lab_duration=165)
    c1.lab[0].day = [1]
    c1.lab[0].start = 525
    c1.lab[0].end = 690
    c2.lab[0].day = [2]
    c2.lab[0].start = 525
    c2.lab[0].end = 690
    assert has_valid_sequence_combination([c1, c2], ["COEN212", "COEN231"]) is True


def test_sequence_combo_tut_lab_overlap():
    c1 = _make_course(subject="COEN", catalog="212", tut_count=1, tut_duration=50)
    c2 = _make_course(subject="COEN", catalog="231", lab_count=1, lab_duration=165)
    c1.tutorial[0].day = [1]
    c1.tutorial[0].start = 525
    c1.tutorial[0].end = 575
    c2.lab[0].day = [1]
    c2.lab[0].start = 525
    c2.lab[0].end = 690
    assert has_valid_sequence_combination([c1, c2], ["COEN212", "COEN231"]) is False


# --- count_sequence_conflicts ---

def test_sequence_conflicts_missing_course():
    c = _make_course(subject="COEN", catalog="212")
    conflicts = count_sequence_conflicts([c], [["COEN212", "COEN231"]])
    assert conflicts == 1


def test_sequence_conflicts_no_conflicts():
    c1 = _make_course(subject="COEN", catalog="212")
    c2 = _make_course(subject="COEN", catalog="231")
    conflicts = count_sequence_conflicts([c1, c2], [["COEN212", "COEN231"]])
    assert conflicts == 0


# --- evaluate_population ---

def test_evaluate_population_length():
    c1 = _make_course(subject="COEN", catalog="311")
    c2 = _make_course(subject="COEN", catalog="212")
    population = [[c1], [c2], [c1, c2]]
    scores = evaluate_population(population)
    assert len(scores) == 3
