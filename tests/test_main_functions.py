import os
import csv
import random
import pytest
from main import should_include_course, read_courses_from_csv, initialize_population


def _write_data_csv(path, rows):
    fieldnames = [
        'subject', 'catalog_nbr', 'class_nbr', 'day_of_week',
        'start_time', 'end_time', 'lab_count', 'biweekly_lab_freq',
        'lab_duration', 'tut_count', 'weekly_tut_freq', 'tut_duration'
    ]
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _sample_row(subject="COEN", catalog="311", class_nbr="AA",
                day="MoWe", start="11.45.00", end="13.00.00"):
    return {
        'subject': subject, 'catalog_nbr': catalog, 'class_nbr': class_nbr,
        'day_of_week': day, 'start_time': start, 'end_time': end,
        'lab_count': '', 'biweekly_lab_freq': '', 'lab_duration': '',
        'tut_count': '', 'weekly_tut_freq': '', 'tut_duration': ''
    }


# --- should_include_course ---

def test_should_include_coen():
    assert should_include_course("COEN", "311") is True


def test_should_include_elec():
    assert should_include_course("ELEC", "273") is True


def test_should_include_engr_290():
    assert should_include_course("ENGR", "290") is True


def test_should_exclude_engr_other():
    assert should_include_course("ENGR", "391") is False


def test_should_exclude_random():
    assert should_include_course("MATH", "201") is False


# --- read_courses_from_csv ---

def test_read_csv_basic(tmp_path):
    csv_path = str(tmp_path / "Data.csv")
    _write_data_csv(csv_path, [_sample_row()])
    courses = read_courses_from_csv(csv_path)
    assert len(courses) == 1
    assert courses[0].subject == "COEN"
    assert courses[0].catalog_nbr == "311"


def test_read_csv_filters_non_included(tmp_path):
    csv_path = str(tmp_path / "Data.csv")
    _write_data_csv(csv_path, [
        _sample_row(subject="COEN", catalog="311"),
        _sample_row(subject="MATH", catalog="201"),
    ])
    courses = read_courses_from_csv(csv_path)
    assert len(courses) == 1
    assert courses[0].subject == "COEN"


def test_read_csv_file_not_found():
    with pytest.raises(FileNotFoundError):
        read_courses_from_csv("/nonexistent/path/Data.csv")


def test_read_csv_empty_file(tmp_path):
    csv_path = str(tmp_path / "Data.csv")
    _write_data_csv(csv_path, [])
    courses = read_courses_from_csv(csv_path)
    assert len(courses) == 0


def test_read_csv_with_labs(tmp_path):
    csv_path = str(tmp_path / "Data.csv")
    row = _sample_row()
    row['lab_count'] = '2'
    row['biweekly_lab_freq'] = '1'
    row['lab_duration'] = '165'
    _write_data_csv(csv_path, [row])
    courses = read_courses_from_csv(csv_path)
    assert len(courses) == 1
    assert courses[0].lab_count == 2


# --- initialize_population ---

def test_initialize_population_size(tmp_path):
    random.seed(42)
    csv_path = str(tmp_path / "Data.csv")
    _write_data_csv(csv_path, [_sample_row()])
    courses = read_courses_from_csv(csv_path)
    pop = initialize_population(courses, population_size=3)
    assert len(pop) == 3
    for individual in pop:
        assert len(individual) == 1


def test_initialize_population_empty_courses():
    random.seed(42)
    pop = initialize_population([], population_size=2)
    assert len(pop) == 2
    for individual in pop:
        assert len(individual) == 0
