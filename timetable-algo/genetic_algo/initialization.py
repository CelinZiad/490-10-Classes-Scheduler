# initialization.py
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
                attempts = 0
                while 0 >= diff and attempts < 120:
                    tut_start = random.choice(tut_50_start)
                    if tut_start > course.lecture.start:
                        diff = tut_start - course.lecture.end
                    elif course.lecture.start > tut_start:
                        diff = course.lecture.end - 50 - tut_start
                    attempts += 1
                tut.start = tut_start
            else:
                tut.start = random.choice(tut_50_start)
            tut.end = tut.start + 50
        elif course.weekly_tut_freq == 1 and course.tut_duration == 100:
            d = random.choice(day_of_week_tut)
            tut.day = [d, d + 7]
            if any(d in day.value for day in course.lecture.day):
                diff = -1
                attempts = 0
                while 0 >= diff and attempts < 120:
                    tut_start = random.choice(tut_100_start)
                    if tut_start > course.lecture.start:
                        diff = tut_start - course.lecture.end
                    elif course.lecture.start > tut_start:
                        diff = course.lecture.end - 100 - tut_start
                    attempts += 1
                tut.start = tut_start
            else:
                tut.start = random.choice(tut_100_start)    
            tut.end = tut.start + 100


def get_lab_days_for_frequency(biweekly_lab_freq: int, base_day: int) -> List[int]:
    """Get lab days based on biweekly frequency (1=once/2 weeks, 2=twice/2 weeks)."""
    if biweekly_lab_freq == 1:
        return [base_day]
    elif biweekly_lab_freq == 2:
        if base_day <= 7:
            return [base_day, base_day + 7]
        else:
            return [base_day - 7, base_day]
    else:
        return [base_day]


def check_room_conflict(day: int, start: int, end: int, 
                        room_timetable: Optional[Dict] = None) -> bool:
    """Check if placing a lab creates a room conflict."""
    if room_timetable is None:
        return False
    
    for slots in room_timetable.values():
        for slot in slots:
            if slot['day'] == day:
                if start < slot['end'] and slot['start'] < end:
                    return True
    
    return False


def find_conflict_free_lab_slot(course, lab_index: int, room_timetable: Optional[Dict] = None,
                                max_attempts: int = 100) -> Optional[Tuple[List[int], int, int]]:
    """Find a conflict-free slot for a lab."""
    if course.lab_duration == 165:
        available_starts = lab_165_start
    elif course.lab_duration == 100:
        available_starts = tut_100_start
    else:
        available_starts = lab_165_start
    
    for attempt in range(max_attempts):
        base_day = random.choice(day_of_week_lab)
        lab_days = get_lab_days_for_frequency(course.biweekly_lab_freq, base_day)
        lab_start = random.choice(available_starts)
        lab_end = lab_start + course.lab_duration
        
        base_weekday = base_day if base_day <= 7 else base_day - 7
        has_lecture_conflict = False
        
        if any(base_weekday in day.value for day in course.lecture.day):
            if lab_start < course.lecture.end and course.lecture.start < lab_end:
                has_lecture_conflict = True
        
        if has_lecture_conflict:
            continue
        
        has_room_conflict = False
        if room_timetable is not None:
            for day in lab_days:
                if check_room_conflict(day, lab_start, lab_end, room_timetable):
                    has_room_conflict = True
                    break
        
        if not has_room_conflict:
            return (lab_days, lab_start, lab_end)
    
    return None


def insert_lab_into_timetable(course, room_timetable: Optional[Dict] = None):
    """Insert labs into course timetable, avoiding lecture and room conflicts."""
    for lab_index, lab in enumerate(course.lab):
        result = find_conflict_free_lab_slot(course, lab_index, room_timetable)
        
        if result is not None:
            lab_days, lab_start, lab_end = result
            lab.day = lab_days
            lab.start = lab_start
            lab.end = lab_end
        else:
            if course.biweekly_lab_freq == 1 and course.lab_duration == 165:
                d = random.choice(day_of_week_lab)
                lab.day = [d]
                if any(d in day.value for day in course.lecture.day):
                    diff = -1
                    attempts = 0
                    while 0 >= diff and attempts < 120:
                        lab_start = random.choice(lab_165_start)
                        if lab_start > course.lecture.start:
                            diff = lab_start - course.lecture.end
                        elif course.lecture.start > lab_start:
                            diff = course.lecture.end - 165 - lab_start
                        attempts += 1
                    lab.start = lab_start
                else:
                    lab.start = random.choice(lab_165_start)
                lab.end = lab.start + 165
            elif course.biweekly_lab_freq == 1 and course.lab_duration == 100:
                d = random.choice(day_of_week_lab)
                lab.day = [d]
                if any(d in day.value for day in course.lecture.day):
                    diff = -1
                    attempts = 0
                    while 0 >= diff and attempts < 120:
                        lab_start = random.choice(tut_100_start)
                        if lab_start > course.lecture.start:
                            diff = lab_start - course.lecture.end
                        elif course.lecture.start > lab_start:
                            diff = course.lecture.end - 100 - lab_start
                        attempts += 1
                    lab.start = lab_start
                else:
                    lab.start = random.choice(tut_100_start)    
                lab.end = lab.start + 100


def build_room_timetable_for_schedule(schedule, room_assignments):
    """Build a room timetable from all labs already scheduled."""
    from room_management import find_room_for_course
    
    room_timetable = {}
    
    for course in schedule:
        if not course.lab or course.lab_count == 0:
            continue
        
        room_info = find_room_for_course(course, room_assignments)
        if room_info is None:
            continue
        
        bldg, room = room_info
        
        if (bldg, room) not in room_timetable:
            room_timetable[(bldg, room)] = []
        
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
    """Check that at least one lab doesn't overlap with at least one tutorial."""
    if not course.lab or not course.tutorial:
        return True
    
    for lab in course.lab:
        if lab is None:
            continue
        for tut in course.tutorial:
            if tut is None:
                continue
            if not times_overlap(lab, tut):
                return True
    
    return False


def times_overlap(element1, element2):
    """Check if two course elements overlap in time."""
    days1 = set(element1.day)
    days2 = set(element2.day)
    
    if not days1.intersection(days2):
        return False
    
    return element1.start < element2.end and element2.start < element1.end


def initialize_course_with_validation(course, max_attempts=100, room_assignments=None, 
                                     existing_schedule=None):
    """Initialize a course's labs and tutorials with validation."""
    room_timetable = None
    if room_assignments is not None and existing_schedule is not None:
        room_timetable = build_room_timetable_for_schedule(existing_schedule, room_assignments)
        
        from room_management import find_room_for_course
        room_info = find_room_for_course(course, room_assignments)
        if room_info is not None:
            bldg, room = room_info
            if (bldg, room) not in room_timetable:
                room_timetable[(bldg, room)] = []
            room_timetable = {(bldg, room): room_timetable[(bldg, room)]}
    
    for attempt in range(max_attempts):
        insert_tut_into_timetable(course)
        insert_lab_into_timetable(course, room_timetable)
        
        if has_valid_lab_tut_combination(course):
            return True
        
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
    
    return False
