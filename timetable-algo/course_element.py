#course_element.py
from dataclasses import dataclass
from typing import List

@dataclass
class CourseElement:
    day: List[int]
    start: int
    end: int
    bldg: str
    room: str
