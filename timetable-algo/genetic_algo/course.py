# course.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, List
from day import parse_day_pattern          # adjust names to match your day.py
from course_element import CourseElement        # adjust to match your file
import re

def parse_time_to_minutes(raw: str) -> int:
    """
    Accepts:
      '11:45'
      '11:45:00'
      '11.45.00'
      '13.00.00'
    """
    s = (raw or "").strip()
    if not s:
        raise ValueError("start_time/end_time is empty")

    s = s.replace(".", ":")

    m = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", s)
    if not m:
        raise ValueError(f"Invalid time format '{raw}'")

    hh = int(m.group(1))
    mm = int(m.group(2))
    ss = int(m.group(3)) if m.group(3) else 0

    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
        raise ValueError(f"Time out of range '{raw}'")

    return hh * 60 + mm


def _get(row: dict, key: str) -> str:
    if key not in row:
        raise KeyError(f"Missing CSV header '{key}'")
    return (row[key] or "").strip()


def _int_or_zero(s: str) -> int:
    s = (s or "").strip()
    return int(s) if s else 0


@dataclass(frozen=True, slots=True)
class Course:
    subject: str
    catalog_nbr: str
    class_nbr: str

    lecture: CourseElement
    lab: Tuple[CourseElement, ...] = ()
    tutorial: Tuple[CourseElement, ...] = ()

    lab_count: int = 0
    biweekly_lab_freq: int = 0
    lab_duration: int = 0

    tut_count: int = 0
    weekly_tut_freq: int = 0
    tut_duration: int = 0

    @property
    def day_codes(self) -> List[int]:
        """
        Example:
          TuTh -> [2, 9, 4, 11]
        """
        codes: List[int] = []
        for d in self.lecture.day:  # FIXED: changed from self.days to self.lecture.day
            codes.extend(d.as_list())
        return codes

    @classmethod
    def from_csv_row(cls, row: dict) -> "Course":
        subject = _get(row, "subject")
        catalog_nbr = _get(row, "catalog_nbr")
        class_nbr = _get(row, "class_nbr")

        lec_days = parse_day_pattern(_get(row, "day_of_week"))
        lec_start = parse_time_to_minutes(_get(row, "start_time"))
        lec_end = parse_time_to_minutes(_get(row, "end_time"))

        lecture = CourseElement(
            day=lec_days,
            start=lec_start,
            end=lec_end,
            bldg=None,
            room=None
        )

        lab_count = _int_or_zero(_get(row, "lab_count"))
        biweekly_lab_freq = _int_or_zero(_get(row, "biweekly_lab_freq"))
        lab_duration = _int_or_zero(_get(row, "lab_duration"))

        tut_count = _int_or_zero(_get(row, "tut_count"))
        weekly_tut_freq = _int_or_zero(_get(row, "weekly_tut_freq"))
        tut_duration = _int_or_zero(_get(row, "tut_duration"))

        # Build lab objects (placeholders until you have actual lab day/time columns)
        laboratory = tuple(
            CourseElement(day=[], start=0, end=0, bldg=None, room=None) 
            for _ in range(lab_count)
        )

        # Build tutorial objects (placeholders)
        tutorials = tuple(
            CourseElement(day=[], start=0, end=0, bldg=None, room=None) 
            for _ in range(tut_count)
        )

        return cls(
            subject=subject,
            catalog_nbr=catalog_nbr,
            class_nbr=class_nbr,
            lecture=lecture,
            lab=laboratory,
            tutorial=tutorials,
            lab_count=lab_count,
            biweekly_lab_freq=biweekly_lab_freq,
            lab_duration=lab_duration,
            tut_count=tut_count,
            weekly_tut_freq=weekly_tut_freq,
            tut_duration=tut_duration,
        )
