import sys
from unittest.mock import MagicMock

# Mock database dependency before importing the modules
sys.modules.setdefault("helper.db", MagicMock())

# Mock course_filter with the real module so db_room_extractor can import it
import genetic_algo.course_filter as real_course_filter
sys.modules.setdefault("genetic_algo.course_filter", real_course_filter)

from genetic_algo.course_filter import should_include_course
from helper.db_room_extractor import group_courses_by_room


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
        {'labroomid': 1, 'subject': 'COEN', 'catalog': '311', 'comments': ''},
        {'labroomid': 1, 'subject': 'COEN', 'catalog': '212', 'comments': ''},
        {'labroomid': 2, 'subject': 'ELEC', 'catalog': '273', 'comments': ''},
    ]
    grouped = group_courses_by_room(assignments)
    assert len(grouped[1]) == 2
    assert len(grouped[2]) == 1


def test_group_no_duplicates():
    assignments = [
        {'labroomid': 1, 'subject': 'COEN', 'catalog': '311', 'comments': ''},
        {'labroomid': 1, 'subject': 'COEN', 'catalog': '311', 'comments': ''},
    ]
    grouped = group_courses_by_room(assignments)
    assert len(grouped[1]) == 1


def test_group_empty():
    grouped = group_courses_by_room([])
    assert len(grouped) == 0
```

Wait — if `genetic_algo.course_filter` can already be imported (since `timetable-algo` is on `PYTHONPATH`), then the original error means `helper.db` is the only blocker. But the error persisted even after mocking `helper.db`... which suggests `timetable-algo` might **not** be on `PYTHONPATH`.

Can you confirm your CI workflow has this in the `PYTHONPATH`?
```
PYTHONPATH=/home/runner/work/490-10-Classes-Scheduler/490-10-Classes-Scheduler:/home/runner/work/490-10-Classes-Scheduler/490-10-Classes-Scheduler/timetable-algo
