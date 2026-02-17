# room_management.py
import csv
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from course import Course

EXCLUDED_ROOMS = {'007', 'AITS'}

@dataclass
class RoomAssignment:
    """Represents a room assignment for a course."""
    bldg: str
    room: str
    subject: str
    catalog_nbrs: List[str]

    def matches_course(self, course: Course) -> bool:
        """Check if this room assignment matches a given course."""
        return (self.subject.strip().upper() == course.subject.upper() and 
                course.catalog_nbr in self.catalog_nbrs)


@dataclass
class RoomSlot:
    """Represents a time slot in a room timetable."""
    day: int
    start: int
    end: int
    subject: str
    catalog_nbr: str
    class_nbr: str
    lab_index: int


class RoomTimetable:
    """Manages the timetable for a specific room."""
    
    def __init__(self, bldg: str, room: str):
        self.bldg = bldg
        self.room = room
        self.slots: List[RoomSlot] = []
    
    def has_conflict(self, day: int, start: int, end: int) -> bool:
        """Check if a time slot conflicts with existing bookings."""
        for slot in self.slots:
            if slot.day == day:
                if start < slot.end and slot.start < end:
                    return True
        return False
    
    def add_slot(self, day: int, start: int, end: int, 
                 subject: str, catalog_nbr: str, class_nbr: str, lab_index: int) -> bool:
        """Add a time slot to the room timetable."""
        if self.has_conflict(day, start, end):
            return False
        
        slot = RoomSlot(
            day=day, start=start, end=end,
            subject=subject, catalog_nbr=catalog_nbr,
            class_nbr=class_nbr, lab_index=lab_index
        )
        self.slots.append(slot)
        return True
    
    def get_slots_sorted(self) -> List[RoomSlot]:
        """Get all slots sorted by day and start time."""
        return sorted(self.slots, key=lambda s: (s.day, s.start))


def load_room_assignments(csv_path: str) -> List[RoomAssignment]:
    """Load room assignments from CSV file (excludes rooms 007, AITS)."""
    assignments = []
    
    with open(csv_path, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            bldg = row['bldg'].strip()
            room = row['room'].strip()
            subject = row['subject'].strip()
            
            if room in EXCLUDED_ROOMS:
                continue
            
            catalog_nbrs = []
            for key in row.keys():
                if key.startswith('course'):
                    course_nbr = row[key].strip()
                    if course_nbr:
                        catalog_nbrs.append(course_nbr)
            
            if catalog_nbrs:
                assignments.append(RoomAssignment(
                    bldg=bldg, room=room,
                    subject=subject, catalog_nbrs=catalog_nbrs
                ))
    
    return assignments


def find_room_for_course(course: Course, room_assignments: List[RoomAssignment]) -> Optional[Tuple[str, str]]:
    """Find the assigned room for a course."""
    for assignment in room_assignments:
        if assignment.matches_course(course):
            return (assignment.bldg, assignment.room)
    return None


def create_room_timetables(schedule: List[Course], 
                          room_assignments: List[RoomAssignment]) -> Dict[Tuple[str, str], RoomTimetable]:
    """Create room timetables for all labs in a schedule."""
    timetables = {}
    for assignment in room_assignments:
        key = (assignment.bldg, assignment.room)
        if key not in timetables:
            timetables[key] = RoomTimetable(assignment.bldg, assignment.room)
    
    conflicts = []
    
    for course in schedule:
        if not course.lab or course.lab_count == 0:
            continue
        
        room_info = find_room_for_course(course, room_assignments)
        if room_info is None:
            continue
        
        bldg, room = room_info
        timetable = timetables[(bldg, room)]
        
        for lab_index, lab in enumerate(course.lab):
            if lab is None or not lab.day:
                continue
            
            lab.bldg = bldg
            lab.room = room
            
            for day in lab.day:
                success = timetable.add_slot(
                    day=day, start=lab.start, end=lab.end,
                    subject=course.subject, catalog_nbr=course.catalog_nbr,
                    class_nbr=course.class_nbr, lab_index=lab_index
                )
                
                if not success:
                    conflicts.append({
                        'course': f"{course.subject}{course.catalog_nbr}",
                        'class_nbr': course.class_nbr,
                        'room': f"{bldg}-{room}",
                        'day': day,
                        'time': f"{lab.start}-{lab.end}",
                        'lab_index': lab_index
                    })
    
    return timetables


def validate_room_timetables(timetables: Dict[Tuple[str, str], RoomTimetable]) -> bool:
    """Validate that all room timetables have no conflicts."""
    all_valid = True
    
    for (bldg, room), timetable in timetables.items():
        slots = timetable.get_slots_sorted()
        
        for i in range(len(slots)):
            for j in range(i + 1, len(slots)):
                slot1 = slots[i]
                slot2 = slots[j]
                
                if slot1.day == slot2.day:
                    if slot1.start < slot2.end and slot2.start < slot1.end:
                        all_valid = False
    
    return all_valid


def display_room_timetable(timetable: RoomTimetable):
    """Display a room's timetable in a readable format."""
    pass


def count_room_conflicts(schedule: List[Course], 
                        room_assignments: List[RoomAssignment]) -> int:
    """Count the number of room conflicts in a schedule."""
    timetables = create_room_timetables(schedule, room_assignments)
    
    conflict_count = 0
    
    for (bldg, room), timetable in timetables.items():
        slots = timetable.slots
        
        for i in range(len(slots)):
            for j in range(i + 1, len(slots)):
                slot1 = slots[i]
                slot2 = slots[j]
                
                if slot1.day == slot2.day:
                    if slot1.start < slot2.end and slot2.start < slot1.end:
                        conflict_count += 1
    
    return conflict_count
