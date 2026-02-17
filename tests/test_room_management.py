import os
import csv
import pytest
from course_element import CourseElement
from course import Course
from day import Day
from room_management import (
    RoomAssignment,
    RoomTimetable,
    find_room_for_course,
    validate_room_timetables,
    create_room_timetables,
    count_room_conflicts,
    load_room_assignments,
)


def _make_course(subject="COEN", catalog="311", lab_count=0, lab_duration=0,
                 biweekly_lab_freq=0):
    lecture = CourseElement(day=(Day.TU, Day.TH), start=705, end=780)
    labs = tuple(CourseElement(day=[], start=0, end=0) for _ in range(lab_count))
    return Course(
        subject=subject, catalog_nbr=catalog, class_nbr="00001",
        lecture=lecture, lab=labs, lab_count=lab_count,
        lab_duration=lab_duration, biweekly_lab_freq=biweekly_lab_freq,
    )


# --- RoomAssignment ---

def test_room_assignment_matches():
    assignment = RoomAssignment(bldg="H", room="929", subject="COEN", catalog_nbrs=["311", "212"])
    course = _make_course(subject="COEN", catalog="311")
    assert assignment.matches_course(course) is True


def test_room_assignment_wrong_subject():
    assignment = RoomAssignment(bldg="H", room="929", subject="ELEC", catalog_nbrs=["311"])
    course = _make_course(subject="COEN", catalog="311")
    assert assignment.matches_course(course) is False


def test_room_assignment_wrong_catalog():
    assignment = RoomAssignment(bldg="H", room="929", subject="COEN", catalog_nbrs=["212"])
    course = _make_course(subject="COEN", catalog="311")
    assert assignment.matches_course(course) is False


# --- RoomTimetable ---

def test_timetable_add_slot_success():
    tt = RoomTimetable("H", "929")
    result = tt.add_slot(1, 525, 690, "COEN", "311", "00001", 0)
    assert result is True
    assert len(tt.slots) == 1


def test_timetable_add_slot_conflict():
    tt = RoomTimetable("H", "929")
    tt.add_slot(1, 525, 690, "COEN", "311", "00001", 0)
    result = tt.add_slot(1, 600, 765, "COEN", "212", "00002", 0)
    assert result is False
    assert len(tt.slots) == 1


def test_timetable_no_conflict_different_day():
    tt = RoomTimetable("H", "929")
    tt.add_slot(1, 525, 690, "COEN", "311", "00001", 0)
    result = tt.add_slot(2, 525, 690, "COEN", "212", "00002", 0)
    assert result is True
    assert len(tt.slots) == 2


def test_timetable_has_conflict():
    tt = RoomTimetable("H", "929")
    tt.add_slot(1, 525, 690, "COEN", "311", "00001", 0)
    assert tt.has_conflict(1, 600, 765) is True
    assert tt.has_conflict(1, 700, 865) is False
    assert tt.has_conflict(2, 525, 690) is False


def test_timetable_get_slots_sorted():
    tt = RoomTimetable("H", "929")
    tt.add_slot(2, 705, 870, "COEN", "212", "00002", 0)
    tt.add_slot(1, 525, 690, "COEN", "311", "00001", 0)
    sorted_slots = tt.get_slots_sorted()
    assert sorted_slots[0].day == 1
    assert sorted_slots[1].day == 2


# --- find_room_for_course ---

def test_find_room_found():
    assignments = [
        RoomAssignment(bldg="H", room="929", subject="COEN", catalog_nbrs=["311"]),
    ]
    course = _make_course(subject="COEN", catalog="311")
    result = find_room_for_course(course, assignments)
    assert result == ("H", "929")


def test_find_room_not_found():
    assignments = [
        RoomAssignment(bldg="H", room="929", subject="ELEC", catalog_nbrs=["273"]),
    ]
    course = _make_course(subject="COEN", catalog="311")
    result = find_room_for_course(course, assignments)
    assert result is None


# --- validate_room_timetables ---

def test_validate_no_conflicts():
    tt = RoomTimetable("H", "929")
    tt.add_slot(1, 525, 690, "COEN", "311", "00001", 0)
    tt.add_slot(2, 525, 690, "COEN", "212", "00002", 0)
    timetables = {("H", "929"): tt}
    assert validate_room_timetables(timetables) is True


# --- create_room_timetables ---

def test_create_room_timetables_basic():
    c = _make_course(subject="COEN", catalog="311", lab_count=1,
                     lab_duration=165, biweekly_lab_freq=1)
    c.lab[0].day = [1]
    c.lab[0].start = 525
    c.lab[0].end = 690
    assignments = [RoomAssignment(bldg="H", room="929", subject="COEN", catalog_nbrs=["311"])]
    timetables = create_room_timetables([c], assignments)
    assert ("H", "929") in timetables
    assert len(timetables[("H", "929")].slots) == 1


def test_create_room_timetables_no_room_assignment():
    c = _make_course(subject="COEN", catalog="311", lab_count=1,
                     lab_duration=165, biweekly_lab_freq=1)
    c.lab[0].day = [1]
    c.lab[0].start = 525
    c.lab[0].end = 690
    assignments = [RoomAssignment(bldg="H", room="929", subject="ELEC", catalog_nbrs=["273"])]
    timetables = create_room_timetables([c], assignments)
    assert len(timetables[("H", "929")].slots) == 0


def test_create_room_timetables_no_labs():
    c = _make_course(subject="COEN", catalog="311")
    assignments = [RoomAssignment(bldg="H", room="929", subject="COEN", catalog_nbrs=["311"])]
    timetables = create_room_timetables([c], assignments)
    assert len(timetables[("H", "929")].slots) == 0


# --- count_room_conflicts ---

def test_count_room_conflicts_none():
    c1 = _make_course(subject="COEN", catalog="311", lab_count=1,
                      lab_duration=165, biweekly_lab_freq=1)
    c1.lab[0].day = [1]
    c1.lab[0].start = 525
    c1.lab[0].end = 690
    c2 = _make_course(subject="COEN", catalog="212", lab_count=1,
                      lab_duration=165, biweekly_lab_freq=1)
    c2.lab[0].day = [2]
    c2.lab[0].start = 525
    c2.lab[0].end = 690
    assignments = [
        RoomAssignment(bldg="H", room="929", subject="COEN", catalog_nbrs=["311", "212"]),
    ]
    assert count_room_conflicts([c1, c2], assignments) == 0


def test_count_room_conflicts_no_overlap_different_rooms():
    c1 = _make_course(subject="COEN", catalog="311", lab_count=1,
                      lab_duration=165, biweekly_lab_freq=1)
    c1.lab[0].day = [1]
    c1.lab[0].start = 525
    c1.lab[0].end = 690
    c2 = _make_course(subject="ELEC", catalog="273", lab_count=1,
                      lab_duration=165, biweekly_lab_freq=1)
    c2.lab[0].day = [1]
    c2.lab[0].start = 525
    c2.lab[0].end = 690
    assignments = [
        RoomAssignment(bldg="H", room="929", subject="COEN", catalog_nbrs=["311"]),
        RoomAssignment(bldg="H", room="930", subject="ELEC", catalog_nbrs=["273"]),
    ]
    assert count_room_conflicts([c1, c2], assignments) == 0


# --- load_room_assignments ---

def _write_room_csv(path, rows):
    fieldnames = ['bldg', 'room', 'subject', 'course1', 'course2']
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_load_room_assignments_basic(tmp_path):
    csv_path = str(tmp_path / "rooms.csv")
    _write_room_csv(csv_path, [
        {'bldg': 'H', 'room': '929', 'subject': 'COEN', 'course1': '311', 'course2': '212'},
    ])
    assignments = load_room_assignments(csv_path)
    assert len(assignments) == 1
    assert assignments[0].bldg == 'H'
    assert assignments[0].room == '929'
    assert '311' in assignments[0].catalog_nbrs
    assert '212' in assignments[0].catalog_nbrs


def test_load_room_assignments_excludes_007(tmp_path):
    csv_path = str(tmp_path / "rooms.csv")
    _write_room_csv(csv_path, [
        {'bldg': 'H', 'room': '007', 'subject': 'COEN', 'course1': '311', 'course2': ''},
        {'bldg': 'H', 'room': '929', 'subject': 'COEN', 'course1': '212', 'course2': ''},
    ])
    assignments = load_room_assignments(csv_path)
    assert len(assignments) == 1
    assert assignments[0].room == '929'


def test_load_room_assignments_excludes_aits(tmp_path):
    csv_path = str(tmp_path / "rooms.csv")
    _write_room_csv(csv_path, [
        {'bldg': 'H', 'room': 'AITS', 'subject': 'COEN', 'course1': '311', 'course2': ''},
    ])
    assignments = load_room_assignments(csv_path)
    assert len(assignments) == 0


def test_load_room_assignments_empty_courses_skipped(tmp_path):
    csv_path = str(tmp_path / "rooms.csv")
    _write_room_csv(csv_path, [
        {'bldg': 'H', 'room': '929', 'subject': 'COEN', 'course1': '', 'course2': ''},
    ])
    assignments = load_room_assignments(csv_path)
    assert len(assignments) == 0


def test_load_room_assignments_multiple(tmp_path):
    csv_path = str(tmp_path / "rooms.csv")
    _write_room_csv(csv_path, [
        {'bldg': 'H', 'room': '929', 'subject': 'COEN', 'course1': '311', 'course2': ''},
        {'bldg': 'H', 'room': '930', 'subject': 'ELEC', 'course1': '273', 'course2': '275'},
    ])
    assignments = load_room_assignments(csv_path)
    assert len(assignments) == 2


# --- validate_room_timetables with conflict ---

def test_validate_with_conflict():
    tt = RoomTimetable("H", "929")
    from room_management import RoomSlot
    tt.slots.append(RoomSlot(day=1, start=525, end=690, subject="COEN",
                             catalog_nbr="311", class_nbr="00001", lab_index=0))
    tt.slots.append(RoomSlot(day=1, start=600, end=765, subject="COEN",
                             catalog_nbr="212", class_nbr="00002", lab_index=0))
    timetables = {("H", "929"): tt}
    assert validate_room_timetables(timetables) is False


# --- create_room_timetables with conflict ---

def test_create_timetables_lab_conflict_logged():
    c1 = _make_course(subject="COEN", catalog="311", lab_count=1,
                      lab_duration=165, biweekly_lab_freq=1)
    c1.lab[0].day = [1]
    c1.lab[0].start = 525
    c1.lab[0].end = 690
    c2 = _make_course(subject="COEN", catalog="212", lab_count=1,
                      lab_duration=165, biweekly_lab_freq=1)
    c2.lab[0].day = [1]
    c2.lab[0].start = 525
    c2.lab[0].end = 690
    assignments = [
        RoomAssignment(bldg="H", room="929", subject="COEN", catalog_nbrs=["311", "212"]),
    ]
    timetables = create_room_timetables([c1, c2], assignments)
    assert len(timetables[("H", "929")].slots) == 1


def test_create_timetables_none_lab_skipped():
    c = _make_course(subject="COEN", catalog="311", lab_count=2,
                     lab_duration=165, biweekly_lab_freq=1)
    c.lab[0].day = [1]
    c.lab[0].start = 525
    c.lab[0].end = 690
    assignments = [RoomAssignment(bldg="H", room="929", subject="COEN", catalog_nbrs=["311"])]
    timetables = create_room_timetables([c], assignments)
    assert len(timetables[("H", "929")].slots) == 1
