# conflict_export.py
import csv
from typing import List, Dict, Tuple
from genetic_algo.course import Course
from itertools import product


def times_overlap(element1, element2):
    """Check if two course elements overlap in time."""
    if element1 is None or element2 is None:
        return False
    
    days1 = set(element1.day)
    days2 = set(element2.day)
    
    if not days1.intersection(days2):
        return False
    
    return element1.start < element2.end and element2.start < element1.end


def minutes_to_time_string(minutes: int) -> str:
    """Convert minutes from midnight to HH:MM format."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def extract_day_number(day):
    """Extract integer day number from Day enum or int."""
    from genetic_algo.day import Day
    
    if isinstance(day, Day):
        return day.first if hasattr(day, 'first') else day.value[0]
    return int(day)


def collect_lecture_conflicts(schedule: List[Course]) -> List[Dict]:
    """Collect all lecture-tutorial/lab conflicts."""
    conflicts = []
    
    for course in schedule:
        if not course.lecture:
            continue
        
        if course.tutorial:
            for tut_index, tut in enumerate(course.tutorial):
                if tut is None or not tut.day:
                    continue
                
                if times_overlap(course.lecture, tut):
                    lecture_days = set()
                    for d in course.lecture.day:
                        lecture_days.add(extract_day_number(d))
                    
                    tut_days = set()
                    for d in tut.day:
                        tut_days.add(extract_day_number(d))
                    
                    overlap_days = lecture_days.intersection(tut_days)
                    
                    for day in overlap_days:
                        conflicts.append({
                            'Conflict_Type': 'Lecture-Tutorial',
                            'Course': f"{course.subject}{course.catalog_nbr}",
                            'Class_Nbr': course.class_nbr,
                            'Component1': 'Lecture',
                            'Component1_Index': 0,
                            'Component2': 'Tutorial',
                            'Component2_Index': tut_index,
                            'Day': day,
                            'Time1': f"{minutes_to_time_string(course.lecture.start)}-{minutes_to_time_string(course.lecture.end)}",
                            'Time2': f"{minutes_to_time_string(tut.start)}-{minutes_to_time_string(tut.end)}",
                            'Building': '',
                            'Room': ''
                        })
        
        if course.lab:
            for lab_index, lab in enumerate(course.lab):
                if lab is None or not lab.day:
                    continue
                
                if times_overlap(course.lecture, lab):
                    lecture_days = set()
                    for d in course.lecture.day:
                        lecture_days.add(extract_day_number(d))
                    
                    lab_days = set()
                    for d in lab.day:
                        lab_days.add(extract_day_number(d))
                    
                    overlap_days = lecture_days.intersection(lab_days)
                    
                    for day in overlap_days:
                        conflicts.append({
                            'Conflict_Type': 'Lecture-Lab',
                            'Course': f"{course.subject}{course.catalog_nbr}",
                            'Class_Nbr': course.class_nbr,
                            'Component1': 'Lecture',
                            'Component1_Index': 0,
                            'Component2': 'Lab',
                            'Component2_Index': lab_index,
                            'Day': day,
                            'Time1': f"{minutes_to_time_string(course.lecture.start)}-{minutes_to_time_string(course.lecture.end)}",
                            'Time2': f"{minutes_to_time_string(lab.start)}-{minutes_to_time_string(lab.end)}",
                            'Building': lab.bldg or '',
                            'Room': lab.room or ''
                        })
    
    return conflicts


def collect_sequence_conflicts(schedule: List[Course], core_sequences: List[List[str]]) -> List[Dict]:
    """Collect all sequence conflicts (no valid combination for core courses)."""
    conflicts = []
    
    for semester_idx, semester_courses in enumerate(core_sequences):
        courses = []
        for course_code in semester_courses:
            subject = ''.join(c for c in course_code if c.isalpha())
            catalog = ''.join(c for c in course_code if c.isdigit())
            
            for course in schedule:
                if course.subject == subject and course.catalog_nbr == catalog:
                    courses.append(course)
                    break
        
        if len(courses) != len(semester_courses):
            conflicts.append({
                'Conflict_Type': 'Sequence-Missing Course',
                'Course': 'Multiple',
                'Class_Nbr': '',
                'Component1': f"Semester {semester_idx + 1}",
                'Component1_Index': '',
                'Component2': str(semester_courses),
                'Component2_Index': '',
                'Day': '',
                'Time1': '',
                'Time2': '',
                'Building': '',
                'Room': ''
            })
            continue
        
        if not has_valid_sequence_combination(schedule, semester_courses):
            all_tutorials = []
            all_labs = []
            
            for course in courses:
                if course.tutorial:
                    valid_tuts = [t for t in course.tutorial if t is not None]
                    if valid_tuts:
                        all_tutorials.append((course, valid_tuts))
                
                if course.lab:
                    valid_labs = [l for l in course.lab if l is not None]
                    if valid_labs:
                        all_labs.append((course, valid_labs))
            
            found_specific = False
            
            for i, (course1, tuts1) in enumerate(all_tutorials):
                for j, (course2, tuts2) in enumerate(all_tutorials[i+1:], i+1):
                    for tut1 in tuts1:
                        for tut2 in tuts2:
                            if times_overlap(tut1, tut2):
                                tut1_days = set(extract_day_number(d) for d in tut1.day)
                                tut2_days = set(extract_day_number(d) for d in tut2.day)
                                overlap_days = tut1_days.intersection(tut2_days)
                                
                                for day in overlap_days:
                                    conflicts.append({
                                        'Conflict_Type': 'Sequence-Tutorial Overlap',
                                        'Course': f"{course1.subject}{course1.catalog_nbr} & {course2.subject}{course2.catalog_nbr}",
                                        'Class_Nbr': f"{course1.class_nbr} & {course2.class_nbr}",
                                        'Component1': f"{course1.subject}{course1.catalog_nbr} Tutorial",
                                        'Component1_Index': tuts1.index(tut1),
                                        'Component2': f"{course2.subject}{course2.catalog_nbr} Tutorial",
                                        'Component2_Index': tuts2.index(tut2),
                                        'Day': day,
                                        'Time1': f"{minutes_to_time_string(tut1.start)}-{minutes_to_time_string(tut1.end)}",
                                        'Time2': f"{minutes_to_time_string(tut2.start)}-{minutes_to_time_string(tut2.end)}",
                                        'Building': '',
                                        'Room': ''
                                    })
                                    found_specific = True
            
            for i, (course1, labs1) in enumerate(all_labs):
                for j, (course2, labs2) in enumerate(all_labs[i+1:], i+1):
                    for lab1 in labs1:
                        for lab2 in labs2:
                            if times_overlap(lab1, lab2):
                                lab1_days = set(extract_day_number(d) for d in lab1.day)
                                lab2_days = set(extract_day_number(d) for d in lab2.day)
                                overlap_days = lab1_days.intersection(lab2_days)
                                
                                for day in overlap_days:
                                    conflicts.append({
                                        'Conflict_Type': 'Sequence-Lab Overlap',
                                        'Course': f"{course1.subject}{course1.catalog_nbr} & {course2.subject}{course2.catalog_nbr}",
                                        'Class_Nbr': f"{course1.class_nbr} & {course2.class_nbr}",
                                        'Component1': f"{course1.subject}{course1.catalog_nbr} Lab",
                                        'Component1_Index': labs1.index(lab1),
                                        'Component2': f"{course2.subject}{course2.catalog_nbr} Lab",
                                        'Component2_Index': labs2.index(lab2),
                                        'Day': day,
                                        'Time1': f"{minutes_to_time_string(lab1.start)}-{minutes_to_time_string(lab1.end)}",
                                        'Time2': f"{minutes_to_time_string(lab2.start)}-{minutes_to_time_string(lab2.end)}",
                                        'Building': lab1.bldg or '',
                                        'Room': lab1.room or ''
                                    })
                                    found_specific = True
            
            for i, (course1, tuts1) in enumerate(all_tutorials):
                for j, (course2, labs2) in enumerate(all_labs):
                    for tut in tuts1:
                        for lab in labs2:
                            if times_overlap(tut, lab):
                                tut_days = set(extract_day_number(d) for d in tut.day)
                                lab_days = set(extract_day_number(d) for d in lab.day)
                                overlap_days = tut_days.intersection(lab_days)
                                
                                for day in overlap_days:
                                    conflicts.append({
                                        'Conflict_Type': 'Sequence-Tutorial/Lab Overlap',
                                        'Course': f"{course1.subject}{course1.catalog_nbr} & {course2.subject}{course2.catalog_nbr}",
                                        'Class_Nbr': f"{course1.class_nbr} & {course2.class_nbr}",
                                        'Component1': f"{course1.subject}{course1.catalog_nbr} Tutorial",
                                        'Component1_Index': tuts1.index(tut),
                                        'Component2': f"{course2.subject}{course2.catalog_nbr} Lab",
                                        'Component2_Index': labs2.index(lab),
                                        'Day': day,
                                        'Time1': f"{minutes_to_time_string(tut.start)}-{minutes_to_time_string(tut.end)}",
                                        'Time2': f"{minutes_to_time_string(lab.start)}-{minutes_to_time_string(lab.end)}",
                                        'Building': lab.bldg or '',
                                        'Room': lab.room or ''
                                    })
                                    found_specific = True
            
            if not found_specific:
                conflicts.append({
                    'Conflict_Type': 'Sequence-No Valid Combination',
                    'Course': 'Multiple',
                    'Class_Nbr': '',
                    'Component1': f"Semester {semester_idx + 1}",
                    'Component1_Index': '',
                    'Component2': str(semester_courses),
                    'Component2_Index': '',
                    'Day': '',
                    'Time1': '',
                    'Time2': '',
                    'Building': '',
                    'Room': ''
                })
    
    return conflicts


def has_valid_sequence_combination(schedule, sequence_courses):
    """Check if sequence has valid combination."""
    courses = []
    for course_code in sequence_courses:
        subject = ''.join(c for c in course_code if c.isalpha())
        catalog = ''.join(c for c in course_code if c.isdigit())
        
        for course in schedule:
            if course.subject == subject and course.catalog_nbr == catalog:
                courses.append(course)
                break
    
    if len(courses) != len(sequence_courses):
        return False
    
    all_tutorials = []
    all_labs = []
    
    for course in courses:
        if course.tutorial:
            valid_tuts = [t for t in course.tutorial if t is not None]
            if valid_tuts:
                all_tutorials.append(valid_tuts)
        
        if course.lab:
            valid_labs = [l for l in course.lab if l is not None]
            if valid_labs:
                all_labs.append(valid_labs)
    
    if not all_tutorials and not all_labs:
        return True
    
    tut_iter = product(*all_tutorials) if all_tutorials else iter([[]])
    lab_list = list(product(*all_labs)) if all_labs else [[]]

    for tut_combo in tut_iter:
        tut_has_overlap = False
        for i, tut1 in enumerate(tut_combo):
            for tut2 in tut_combo[i+1:]:
                if times_overlap(tut1, tut2):
                    tut_has_overlap = True
                    break
            if tut_has_overlap:
                break

        if tut_has_overlap:
            continue

        for lab_combo in lab_list:
            lab_has_overlap = False
            for i, lab1 in enumerate(lab_combo):
                for lab2 in lab_combo[i+1:]:
                    if times_overlap(lab1, lab2):
                        lab_has_overlap = True
                        break
                if lab_has_overlap:
                    break

            if lab_has_overlap:
                continue

            tut_lab_overlap = False
            for tut in tut_combo:
                for lab in lab_combo:
                    if times_overlap(tut, lab):
                        tut_lab_overlap = True
                        break
                if tut_lab_overlap:
                    break

            if not tut_lab_overlap:
                return True

    return False


def collect_room_conflicts(schedule: List[Course], room_assignments) -> List[Dict]:
    """Collect all room conflicts."""
    from genetic_algo.room_management import create_room_timetables
    
    conflicts = []
    
    timetables = create_room_timetables(schedule, room_assignments)
    
    for (bldg, room), timetable in timetables.items():
        slots = sorted(timetable.slots, key=lambda s: (s.day, s.start))
        
        for i in range(len(slots)):
            for j in range(i + 1, len(slots)):
                slot1 = slots[i]
                slot2 = slots[j]
                
                if slot1.day == slot2.day:
                    if slot1.start < slot2.end and slot2.start < slot1.end:
                        conflicts.append({
                            'Conflict_Type': 'Room Conflict',
                            'Course': f"{slot1.subject}{slot1.catalog_nbr} & {slot2.subject}{slot2.catalog_nbr}",
                            'Class_Nbr': f"{slot1.class_nbr} & {slot2.class_nbr}",
                            'Component1': f"{slot1.subject}{slot1.catalog_nbr} Lab {slot1.lab_index}",
                            'Component1_Index': slot1.lab_index,
                            'Component2': f"{slot2.subject}{slot2.catalog_nbr} Lab {slot2.lab_index}",
                            'Component2_Index': slot2.lab_index,
                            'Day': slot1.day,
                            'Time1': f"{minutes_to_time_string(slot1.start)}-{minutes_to_time_string(slot1.end)}",
                            'Time2': f"{minutes_to_time_string(slot2.start)}-{minutes_to_time_string(slot2.end)}",
                            'Building': bldg,
                            'Room': room
                        })
    
    return conflicts


def export_conflicts_csv(schedule: List[Course], core_sequences: List[List[str]], 
                        room_assignments, output_path: str):
    """Export all conflicts to a CSV file."""
    all_conflicts = []
    
    lecture_conflicts = collect_lecture_conflicts(schedule)
    all_conflicts.extend(lecture_conflicts)
    
    sequence_conflicts = collect_sequence_conflicts(schedule, core_sequences)
    all_conflicts.extend(sequence_conflicts)
    
    room_conflicts = collect_room_conflicts(schedule, room_assignments)
    all_conflicts.extend(room_conflicts)
    
    fieldnames = [
        'Conflict_Type', 'Course', 'Class_Nbr', 
        'Component1', 'Component1_Index', 
        'Component2', 'Component2_Index',
        'Day', 'Time1', 'Time2', 'Building', 'Room'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_conflicts)
    
    return len(all_conflicts)
