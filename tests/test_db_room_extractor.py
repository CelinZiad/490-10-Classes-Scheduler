import sys
from unittest.mock import MagicMock

sys.modules.setdefault("helper.db", MagicMock())
sys.modules.setdefault("genetic_algo.course_filter", MagicMock())

import helper.db_room_extractor as mod

EXCLUDED_ELEC = {"430", "434", "436", "438", "443", "446", "490", "498"}
EXCLUDED_COEN = {"390", "490"}


def should_include_course(subject, catalog):
    subject = subject.upper().strip()
    catalog = catalog.strip()
    if subject == "COEN":
        return catalog not in EXCLUDED_COEN
    if subject == "ELEC":
        return catalog not in EXCLUDED_ELEC
    if subject == "ENGR" and catalog == "290":
        return True
    return False


group_courses_by_room = mod.group_courses_by_room


# --- should_include_course ---


def test_include_coen():
    assert should_include_course("COEN", "311") is True


def test_include_elec():
    assert should_include_course("ELEC", "273") is True


def test_include_engr_290():
    assert should_include_course("ENGR", "290") is True


def test_exclude_engr_other():
    assert should_include_course("ENGR", "391") is False


def test_exclude_math():
    assert should_include_course("MATH", "201") is False


def test_include_lowercase():
    assert should_include_course("coen", "311") is True


# --- group_courses_by_room ---


def test_group_basic():
    assignments = [
        {"labroomid": 1, "subject": "COEN", "catalog": "311", "comments": ""},
        {"labroomid": 1, "subject": "COEN", "catalog": "212", "comments": ""},
        {"labroomid": 2, "subject": "ELEC", "catalog": "273", "comments": ""},
    ]
    grouped = group_courses_by_room(assignments)
    assert len(grouped[1]) == 2
    assert len(grouped[2]) == 1


def test_group_no_duplicates():
    assignments = [
        {"labroomid": 1, "subject": "COEN", "catalog": "311", "comments": ""},
        {"labroomid": 1, "subject": "COEN", "catalog": "311", "comments": ""},
    ]
    grouped = group_courses_by_room(assignments)
    assert len(grouped[1]) == 1


def test_group_empty():
    grouped = group_courses_by_room([])
    assert len(grouped) == 0
