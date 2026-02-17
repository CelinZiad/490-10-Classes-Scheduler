# course_element.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CourseElement:
    """Represents a course component (lecture, lab, or tutorial)."""
    day: List[int]  # Day numbers (1-5 for Week 1, 8-12 for Week 2)
    start: int  # Start time in minutes from midnight
    end: int  # End time in minutes from midnight
    bldg: Optional[str] = None
    room: Optional[str] = None
