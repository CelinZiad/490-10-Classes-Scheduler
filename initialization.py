import random
from course import Course
from typing import Tuple, List, Optional, Dict

start_time_0845 = 8*60 + 45
start_time_0950 = 9*60 + 50
start_time_1040 = 10*60 + 40
start_time_1145 = 11*60 + 45
start_time_1250 = 12*60 + 50
start_time_1340 = 13*60 + 40
start_time_1445 = 14*60 + 45
start_time_1550 = 15*60 + 50
start_time_1640 = 16*60 + 40
start_time_1745 = 17*60 + 45
start_time_1850 = 18*60 + 50
start_time_1940 = 19*60 + 40

day_of_week_tut = [1, 2, 3, 4, 5]
day_of_week_lab = [1, 2, 3, 4, 5, 8, 9, 10, 11, 12]
lab_165_start = [start_time_0845, start_time_1145, start_time_1445, start_time_1745]
tut_50_start = [start_time_0845, start_time_1040, start_time_1145, start_time_1340, 
                start_time_1445, start_time_1640, start_time_1745, start_time_1940]
tut_100_start = [start_time_0845, start_time_0950, start_time_1145, start_time_1250, 
                    start_time_1445, start_time_1550, start_time_1745, start_time_1850]

def insert_tut_into_timetable(course):
    for tut in course.tutorial:
        if course.weekly_tut_freq == 1 and course.tut_duration == 50:
            d = random.choice(day_of_week_tut)
            tut.day = [d, d + 7]
            if any(d in day.value for day in course.lecture.day):
                diff = -1
                while 0 >= diff:
                    tut_start = random.choice(tut_50_start)
                    if tut_start > course.lecture.start:
                        diff = tut_start - course.lecture.end
                    elif course.lecture.start > tut_start:
                        diff = course.lecture.end - 50 - tut_start
                tut.start = tut_start
            else:
                tut.start = random.choice(tut_50_start)    
            tut.end = tut.start + 50
        elif course.weekly_tut_freq == 1 and course.tut_duration == 100:
            d = random.choice(day_of_week_tut)
            tut.day = [d, d + 7]
            if any(d in day.value for day in course.lecture.day):
                diff = -1
                while 0 >= diff:
                    tut_start = random.choice(tut_100_start)
                    if tut_start > course.lecture.start:
                        diff = tut_start - course.lecture.end
                    elif course.lecture.start > tut_start:
                        diff = course.lecture.end - 100 - tut_start
                tut.start = tut_start
            else:
                tut.start = random.choice(tut_100_start)    
            tut.end = tut.start + 100


def get_lab_days_for_frequency(biweekly_lab_freq: int, base_day: int) -> List[int]:
    """
    Get the list of days a lab occurs based on its biweekly frequency.
    
    Args:
        biweekly_lab_freq: Frequency value from Data.csv
            1 = once every two weeks (appears on only one day in 14-day period)
            2 = twice every two weeks (appears on same weekday both weeks)
        base_day: The weekday chosen (1-5 for Week 1, or 8-12 for Week 2)
    
    Returns:
        List of day numbers where lab occurs
    """
    if biweekly_lab_freq == 1:
        # Lab occurs only once in the 14-day period
        return [base_day]
    elif biweekly_lab_freq == 2:
        # Lab occurs on the same weekday in both weeks
        if base_day <= 7:
            return [base_day, base_day + 7]
        else:
            return [base_day - 7, base_day]
    else:
        # Default to once per two weeks
        return [base_day]


def check_room_conflict(day: int, start: int, end: int, 
                        room_timetable: Optional[Dict] = None) -> bool:
    """
    Check if placing a lab at this time creates a room conflict.
    
    Args:
        day: Day number (1-14)
        start: Start time in minutes
        end: End time in minutes
        room_timetable: Dictionary mapping (bldg, room) to list of occupied slots
                       Each slot is {'day': int, 'start': int, 'end': int}
    
    Returns:
        True if there's a conflict, False if slot is available
    """
    if room_timetable is None:
        return False
    
    for slots in room_timetable.values():
        for slot in slots:
            if slot['day'] == day:
                # Check time overlap: start1 < end2 AND start2 < end1
                if start < slot['end'] and slot['start'] < end:
                    return True
    
    return False


def find_conflict_free_lab_slot(course, lab_index: int, room_timetable: Optional[Dict] = None,
                                max_attempts: int = 100) -> Optional[Tuple[List[int], int, int]]:
    """
    Find a conflict-free slot for a lab, checking both lecture conflicts and room conflicts.
    
    Args:
        course: Course object
        lab_index: Index of the lab being scheduled
        room_timetable: Optional room timetable to check conflicts
        max_attempts: Maximum number of attempts to find a slot
    
    Returns:
        Tuple of (days, start_time, end_time) if found, None otherwise
    """
    # Determine available start times based on lab duration
    if course.lab_duration == 165:
        available_starts = lab_165_start
    elif course.lab_duration == 100:
        available_starts = tut_100_start
    else:
        # Default to 165-minute slots
        available_starts = lab_165_start
    
    # Try to find a conflict-free slot
    for attempt in range(max_attempts):
        # Randomly choose a weekday
        base_day = random.choice(day_of_week_lab)
        
        # Get the actual days based on biweekly frequency
        lab_days = get_lab_days_for_frequency(course.biweekly_lab_freq, base_day)
        
        # Choose a start time
        lab_start = random.choice(available_starts)
        lab_end = lab_start + course.lab_duration
        
        # Check lecture conflict (only check the base weekday, not week number)
        base_weekday = base_day if base_day <= 7 else base_day - 7
        has_lecture_conflict = False
        
        if any(base_weekday in day.value for day in course.lecture.day):
            # Same day as lecture, check time overlap
            if lab_start < course.lecture.end and course.lecture.start < lab_end:
                has_lecture_conflict = True
        
        if has_lecture_conflict:
            continue
        
        # Check room conflicts for all days this lab occurs
        has_room_conflict = False
        if room_timetable is not None:
            for day in lab_days:
                if check_room_conflict(day, lab_start, lab_end, room_timetable):
                    has_room_conflict = True
                    break
        
        if not has_room_conflict:
            return (lab_days, lab_start, lab_end)
    
    # Could not find conflict-free slot
    return None


def insert_lab_into_timetable(course, room_timetable: Optional[Dict] = None):
    """
    Insert labs into course timetable, avoiding both lecture and room conflicts.
    
    Args:
        course: Course object with labs to schedule
        room_timetable: Optional dict mapping (bldg, room) to occupied slots
    """
    for lab_index, lab in enumerate(course.lab):
        result = find_conflict_free_lab_slot(course, lab_index, room_timetable)
        
        if result is not None:
            lab_days, lab_start, lab_end = result
            lab.day = lab_days
            lab.start = lab_start
            lab.end = lab_end
        else:
            # Fallback to old method without room conflict checking
            if course.biweekly_lab_freq == 1 and course.lab_duration == 165:
                d = random.choice(day_of_week_lab)
                lab.day = [d]
                if any(d in day.value for day in course.lecture.day):
                    diff = -1
                    while 0 >= diff:
                        lab_start = random.choice(lab_165_start)
                        if lab_start > course.lecture.start:
                            diff = lab_start - course.lecture.end
                        elif course.lecture.start > lab_start:
                            diff = course.lecture.end - 165 - lab_start
                    lab.start = lab_start
                else:
                    lab.start = random.choice(lab_165_start)    
                lab.end = lab.start + 165
            elif course.biweekly_lab_freq == 1 and course.lab_duration == 100:
                d = random.choice(day_of_week_lab)
                lab.day = [d]
                if any(d in day.value for day in course.lecture.day):
                    diff = -1
                    while 0 >= diff:
                        lab_start = random.choice(tut_100_start)
                        if lab_start > course.lecture.start:
                            diff = lab_start - course.lecture.end
                        elif course.lecture.start > lab_start:
                            diff = course.lecture.end - 100 - lab_start
                    lab.start = lab_start
                else:
                    lab.start = random.choice(tut_100_start)    
                lab.end = lab.start + 100


def build_room_timetable_for_schedule(schedule, room_assignments):
    """
    Build a room timetable from all labs already scheduled.
    
    Args:
        schedule: List of Course objects
        room_assignments: List of RoomAssignment objects
    
    Returns:
        Dictionary mapping (bldg, room) to list of occupied slots
    """
    from room_management import find_room_for_course
    
    room_timetable = {}
    
    for course in schedule:
        if not course.lab or course.lab_count == 0:
            continue
        
        # Find room for this course
        room_info = find_room_for_course(course, room_assignments)
        if room_info is None:
            continue
        
        bldg, room = room_info
        
        if (bldg, room) not in room_timetable:
            room_timetable[(bldg, room)] = []
        
        # Add all scheduled labs to the timetable
        for lab in course.lab:
            if lab is None or not lab.day:
                continue
            
            for day in lab.day:
                room_timetable[(bldg, room)].append({
                    'day': day,
                    'start': lab.start,
                    'end': lab.end,
                    'course': f"{course.subject}{course.catalog_nbr}"
                })
    
    return room_timetable


def has_valid_lab_tut_combination(course):
    """
    Check that at least one lab doesn't overlap with at least one tutorial.
    Returns True if valid, False otherwise.
    """
    if not course.lab or not course.tutorial:
        return True  # No conflict if either is empty
    
    for lab in course.lab:
        if lab is None:
            continue
        for tut in course.tutorial:
            if tut is None:
                continue
            if not times_overlap(lab, tut):
                return True  # Found at least one non-overlapping pair
    
    return False  # All combinations overlap


def times_overlap(element1, element2):
    """
    Check if two course elements overlap in time.
    Returns True if they overlap, False otherwise.
    """
    # Check if they share any days
    days1 = set(element1.day)
    days2 = set(element2.day)
    
    if not days1.intersection(days2):
        return False  # Different days = no overlap
    
    # Same day(s), check time overlap
    # Times overlap if: start1 < end2 AND start2 < end1
    return element1.start < element2.end and element2.start < element1.end


def initialize_course_with_validation(course, max_attempts=100, room_assignments=None, 
                                     existing_schedule=None):
    """
    Initialize a course's labs and tutorials, ensuring at least one valid combination
    and avoiding room conflicts.
    
    Args:
        course: Course object to initialize
        max_attempts: Maximum number of attempts
        room_assignments: Optional list of RoomAssignment objects
        existing_schedule: Optional list of already-scheduled courses (for room conflicts)
    
    Returns:
        True if successful, False if max attempts exceeded.
    """
    # Build room timetable from existing schedule
    room_timetable = None
    if room_assignments is not None and existing_schedule is not None:
        room_timetable = build_room_timetable_for_schedule(existing_schedule, room_assignments)
        
        # Find this course's room and add it to the timetable structure
        from room_management import find_room_for_course
        room_info = find_room_for_course(course, room_assignments)
        if room_info is not None:
            bldg, room = room_info
            if (bldg, room) not in room_timetable:
                room_timetable[(bldg, room)] = []
            # Filter to only this room's timetable for conflict checking
            room_timetable = {(bldg, room): room_timetable[(bldg, room)]}
    
    for attempt in range(max_attempts):
        insert_tut_into_timetable(course)
        insert_lab_into_timetable(course, room_timetable)
        
        if has_valid_lab_tut_combination(course):
            return True
        
        # Reset and try again
        for tut in course.tutorial:
            if tut:
                tut.day = []
                tut.start = 0
                tut.end = 0
        
        for lab in course.lab:
            if lab:
                lab.day = []
                lab.start = 0
                lab.end = 0
    
    return False  # Failed after max_attempts
