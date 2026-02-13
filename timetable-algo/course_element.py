# course_element.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CourseElement:
    """
    Represents a course component (lecture, lab, or tutorial).
    
    Attributes:
        day: List of day numbers (1-5 for Week 1, 8-12 for Week 2)
        start: Start time in minutes from midnight
        end: End time in minutes from midnight
        bldg: Building code (optional, mainly for labs)
        room: Room number (optional, mainly for labs)
    """
    day: List[int]
    start: int
    end: int
    bldg: Optional[str] = None
    room: Optional[str] = None
