# room_management.py
import csv
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from course import Course

# Rooms to exclude from scheduling (unscheduled/special purpose rooms)
EXCLUDED_ROOMS = {'007', 'AITS'}

@dataclass
class RoomAssignment:
    """Represents a room assignment for a course."""
    bldg: str
    room: str
    subject: str
    catalog_nbrs: List[str]  # Can handle multiple courses per room

    def matches_course(self, course: Course) -> bool:
        """Check if this room assignment matches a given course."""
        return (self.subject.strip().upper() == course.subject.upper() and 
                course.catalog_nbr in self.catalog_nbrs)


@dataclass
class RoomSlot:
    """Represents a time slot in a room timetable."""
    day: int  # 1-14 for two-week period
    start: int  # minutes from midnight
    end: int  # minutes from midnight
    subject: str
    catalog_nbr: str
    class_nbr: str
    lab_index: int  # Which lab of the course (0, 1, 2, etc.)


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
                # Check time overlap: start1 < end2 AND start2 < end1
                if start < slot.end and slot.start < end:
                    return True
        return False
    
    def add_slot(self, day: int, start: int, end: int, 
                 subject: str, catalog_nbr: str, class_nbr: str, lab_index: int) -> bool:
        """
        Add a time slot to the room timetable.
        Returns True if successful, False if there's a conflict.
        """
        if self.has_conflict(day, start, end):
            return False
        
        slot = RoomSlot(
            day=day,
            start=start,
            end=end,
            subject=subject,
            catalog_nbr=catalog_nbr,
            class_nbr=class_nbr,
            lab_index=lab_index
        )
        self.slots.append(slot)
        return True
    
    def get_slots_sorted(self) -> List[RoomSlot]:
        """Get all slots sorted by day and start time."""
        return sorted(self.slots, key=lambda s: (s.day, s.start))


def load_room_assignments(csv_path: str) -> List[RoomAssignment]:
    """
    Load room assignments from CSV file.
    Excludes rooms in EXCLUDED_ROOMS (007, AITS).
    
    Returns:
        List of RoomAssignment objects
    """
    assignments = []
    
    with open(csv_path, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            bldg = row['bldg'].strip()
            room = row['room'].strip()
            subject = row['subject'].strip()
            
            # Skip excluded rooms
            if room in EXCLUDED_ROOMS:
                continue
            
            # Collect all course numbers from course1, course2, etc.
            catalog_nbrs = []
            for key in row.keys():
                if key.startswith('course'):
                    course_nbr = row[key].strip()
                    if course_nbr:
                        catalog_nbrs.append(course_nbr)
            
            if catalog_nbrs:
                assignments.append(RoomAssignment(
                    bldg=bldg,
                    room=room,
                    subject=subject,
                    catalog_nbrs=catalog_nbrs
                ))
    
    return assignments


def find_room_for_course(course: Course, room_assignments: List[RoomAssignment]) -> Optional[Tuple[str, str]]:
    """
    Find the assigned room for a course.
    
    Args:
        course: Course object
        room_assignments: List of RoomAssignment objects
    
    Returns:
        Tuple of (bldg, room) if found, None otherwise
    """
    for assignment in room_assignments:
        if assignment.matches_course(course):
            return (assignment.bldg, assignment.room)
    return None


def create_room_timetables(schedule: List[Course], 
                          room_assignments: List[RoomAssignment]) -> Dict[Tuple[str, str], RoomTimetable]:
    """
    Create room timetables for all labs in a schedule.
    
    Args:
        schedule: List of Course objects
        room_assignments: List of RoomAssignment objects
    
    Returns:
        Dictionary mapping (bldg, room) to RoomTimetable objects
    """
    # Initialize timetables for all rooms in assignments
    timetables = {}
    for assignment in room_assignments:
        key = (assignment.bldg, assignment.room)
        if key not in timetables:
            timetables[key] = RoomTimetable(assignment.bldg, assignment.room)
    
    # Assign labs to rooms
    conflicts = []
    
    for course in schedule:
        if not course.lab or course.lab_count == 0:
            continue
        
        # Find room for this course
        room_info = find_room_for_course(course, room_assignments)
        if room_info is None:
            # Course doesn't have a specific room assigned
            continue
        
        bldg, room = room_info
        timetable = timetables[(bldg, room)]
        
        # Add each lab to the room timetable
        for lab_index, lab in enumerate(course.lab):
            if lab is None or not lab.day:
                continue
            
            # Update the lab's building and room
            lab.bldg = bldg
            lab.room = room
            
            # For each day the lab occurs (biweekly labs have one day)
            for day in lab.day:
                success = timetable.add_slot(
                    day=day,
                    start=lab.start,
                    end=lab.end,
                    subject=course.subject,
                    catalog_nbr=course.catalog_nbr,
                    class_nbr=course.class_nbr,
                    lab_index=lab_index
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
    
    if conflicts:
        print(f"\n⚠ Warning: {len(conflicts)} room conflicts detected:")
        for conflict in conflicts[:10]:  # Show first 10
            print(f"  {conflict['course']} (class {conflict['class_nbr']}) "
                  f"Lab {conflict['lab_index']} in {conflict['room']} "
                  f"on day {conflict['day']} at {conflict['time']}")
        if len(conflicts) > 10:
            print(f"  ... and {len(conflicts) - 10} more conflicts")
    
    return timetables


def validate_room_timetables(timetables: Dict[Tuple[str, str], RoomTimetable]) -> bool:
    """
    Validate that all room timetables have no conflicts.
    
    Returns:
        True if all timetables are valid, False otherwise
    """
    all_valid = True
    
    for (bldg, room), timetable in timetables.items():
        slots = timetable.get_slots_sorted()
        
        # Check for overlaps
        for i in range(len(slots)):
            for j in range(i + 1, len(slots)):
                slot1 = slots[i]
                slot2 = slots[j]
                
                if slot1.day == slot2.day:
                    # Check time overlap
                    if slot1.start < slot2.end and slot2.start < slot1.end:
                        print(f"✗ Conflict in {bldg}-{room} on day {slot1.day}:")
                        print(f"  {slot1.subject}{slot1.catalog_nbr} ({slot1.start}-{slot1.end})")
                        print(f"  {slot2.subject}{slot2.catalog_nbr} ({slot2.start}-{slot2.end})")
                        all_valid = False
    
    return all_valid


def display_room_timetable(timetable: RoomTimetable):
    """Display a room's timetable in a readable format."""
    print(f"\nRoom {timetable.bldg}-{timetable.room}")
    print("=" * 70)
    
    if not timetable.slots:
        print("  No labs scheduled")
        return
    
    slots = timetable.get_slots_sorted()
    
    print(f"{'Day':<6} {'Time':<15} {'Course':<15} {'Class#':<10} {'Lab#':<6}")
    print("-" * 70)
    
    for slot in slots:
        time_str = f"{slot.start//60:02d}:{slot.start%60:02d}-{slot.end//60:02d}:{slot.end%60:02d}"
        course_str = f"{slot.subject}{slot.catalog_nbr}"
        
        print(f"{slot.day:<6} {time_str:<15} {course_str:<15} {slot.class_nbr:<10} {slot.lab_index:<6}")
    
    print("=" * 70)


def count_room_conflicts(schedule: List[Course], 
                        room_assignments: List[RoomAssignment]) -> int:
    """
    Count the number of room conflicts in a schedule.
    
    Returns:
        Number of conflicts detected
    """
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
