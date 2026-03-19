# helper/time_utils.py
"""Shared utility functions used across multiple helper/export modules.

Consolidates duplicated functions that previously appeared in
scheduleterm_export.py, db_timetable_export.py, export_utils.py,
and conflict_export.py.
"""
from typing import List, Dict


def minutes_to_time(minutes: int) -> str:
    """Convert minutes from midnight to HH:MM:SS format."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}:00"


def minutes_to_time_short(minutes: int) -> str:
    """Convert minutes from midnight to HH:MM format."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def day_number_to_day_columns(day_num: int) -> Dict[str, bool]:
    """Convert a GA day number (1-5 or 8-12) to boolean day columns."""
    day_map = {
        1: 'mondays', 2: 'tuesdays', 3: 'wednesdays', 4: 'thursdays', 5: 'fridays',
        8: 'mondays', 9: 'tuesdays', 10: 'wednesdays', 11: 'thursdays', 12: 'fridays'
    }
    result = {
        'mondays': False, 'tuesdays': False, 'wednesdays': False,
        'thursdays': False, 'fridays': False, 'saturdays': False, 'sundays': False
    }
    col = day_map.get(day_num)
    if col:
        result[col] = True
    return result


def combine_day_columns(day_numbers: List[int]) -> Dict[str, bool]:
    """Combine multiple day numbers into a single boolean day-column dict."""
    result = {
        'mondays': False, 'tuesdays': False, 'wednesdays': False,
        'thursdays': False, 'fridays': False, 'saturdays': False, 'sundays': False
    }
    for d in day_numbers:
        for k, v in day_number_to_day_columns(d).items():
            if v:
                result[k] = True
    return result


def extract_day_numbers(day_enum) -> List[int]:
    """Extract integer day numbers from a Day enum or int.
    
    Handles plain ints, Day enum objects, and string representations.
    """
    if isinstance(day_enum, int):
        return [day_enum]
    day_str = str(day_enum)
    if 'Week1' in day_str or 'Week2' in day_str:
        day_map = {
            'Week1Monday': 1, 'Week1Tuesday': 2, 'Week1Wednesday': 3,
            'Week1Thursday': 4, 'Week1Friday': 5,
            'Week2Monday': 8, 'Week2Tuesday': 9, 'Week2Wednesday': 10,
            'Week2Thursday': 11, 'Week2Friday': 12
        }
        for key, val in day_map.items():
            if key in day_str:
                return [val]
    return [day_enum] if isinstance(day_enum, int) else []
