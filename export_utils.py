# export_utils.py
import csv
from typing import List, Dict, Tuple
from course import Course
from room_management import RoomTimetable, create_room_timetables, load_room_assignments

def minutes_to_time_string(minutes: int) -> str:
    """Convert minutes from midnight to HH:MM format."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def day_number_to_string(day) -> str:
    """
    Convert day number (1-14) to a readable format.
    Days 1-7 are Week 1 (Mon-Sun), Days 8-14 are Week 2 (Mon-Sun)
    Handles both int and Day enum objects.
    """
    from day import Day
    
    # If it's a Day enum, extract the integer value
    if isinstance(day, Day):
        day_num = day.first if hasattr(day, 'first') else day.value[0]
    else:
        day_num = int(day)
    
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    if 1 <= day_num <= 7:
        week = 1
        day_index = day_num - 1
    elif 8 <= day_num <= 14:
        week = 2
        day_index = day_num - 8
    else:
        return f"Day {day_num}"
    
    return f"Week {week} - {day_names[day_index]}"


def extract_day_numbers(day_list):
    """
    Extract day numbers from a list that may contain Day enum objects or integers.
    Returns a list of integers.
    """
    from day import Day
    
    result = []
    for day in day_list:
        if isinstance(day, Day):
            # Day enum has .first and .second properties
            result.extend([day.first, day.second])
        elif isinstance(day, int):
            result.append(day)
    return result


def export_course_timetable_csv(schedule: List[Course], output_path: str):
    """
    Export the course timetable (lectures, tutorials, labs) to a CSV file.
    
    Args:
        schedule: List of Course objects
        output_path: Path to output CSV file
    """
    rows = []
    
    for course in schedule:
        # Export lecture information
        if course.lecture:
            lecture = course.lecture
            day_numbers = extract_day_numbers(lecture.day)
            for day in day_numbers:
                rows.append({
                    'Type': 'Lecture',
                    'Subject': course.subject,
                    'Catalog_Nbr': course.catalog_nbr,
                    'Class_Nbr': course.class_nbr,
                    'Component_Index': 0,
                    'Day_Number': day,
                    'Day_Name': day_number_to_string(day),
                    'Start_Time': minutes_to_time_string(lecture.start),
                    'End_Time': minutes_to_time_string(lecture.end),
                    'Start_Minutes': lecture.start,
                    'End_Minutes': lecture.end,
                    'Building': lecture.bldg or '',
                    'Room': lecture.room or ''
                })
        
        # Export tutorial information
        if course.tutorial:
            for tut_index, tut in enumerate(course.tutorial):
                if tut is None or not tut.day:
                    continue
                day_numbers = extract_day_numbers(tut.day)
                for day in day_numbers:
                    rows.append({
                        'Type': 'Tutorial',
                        'Subject': course.subject,
                        'Catalog_Nbr': course.catalog_nbr,
                        'Class_Nbr': course.class_nbr,
                        'Component_Index': tut_index,
                        'Day_Number': day,
                        'Day_Name': day_number_to_string(day),
                        'Start_Time': minutes_to_time_string(tut.start),
                        'End_Time': minutes_to_time_string(tut.end),
                        'Start_Minutes': tut.start,
                        'End_Minutes': tut.end,
                        'Building': tut.bldg or '',
                        'Room': tut.room or ''
                    })
        
        # Export lab information
        if course.lab:
            for lab_index, lab in enumerate(course.lab):
                if lab is None or not lab.day:
                    continue
                day_numbers = extract_day_numbers(lab.day)
                for day in day_numbers:
                    rows.append({
                        'Type': 'Lab',
                        'Subject': course.subject,
                        'Catalog_Nbr': course.catalog_nbr,
                        'Class_Nbr': course.class_nbr,
                        'Component_Index': lab_index,
                        'Day_Number': day,
                        'Day_Name': day_number_to_string(day),
                        'Start_Time': minutes_to_time_string(lab.start),
                        'End_Time': minutes_to_time_string(lab.end),
                        'Start_Minutes': lab.start,
                        'End_Minutes': lab.end,
                        'Building': lab.bldg or '',
                        'Room': lab.room or ''
                    })
    
    # Sort by subject, catalog_nbr, type, day, start time
    rows.sort(key=lambda x: (
        x['Subject'], 
        x['Catalog_Nbr'], 
        x['Class_Nbr'],
        x['Type'], 
        x['Day_Number'], 
        x['Start_Minutes']
    ))
    
    # Write to CSV
    if rows:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'Type', 'Subject', 'Catalog_Nbr', 'Class_Nbr', 'Component_Index',
                'Day_Number', 'Day_Name', 'Start_Time', 'End_Time', 
                'Start_Minutes', 'End_Minutes', 'Building', 'Room'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    
    print(f"Course timetable exported to: {output_path}")
    print(f"Total entries: {len(rows)}")


def export_room_timetable_csv(timetables: Dict[Tuple[str, str], RoomTimetable], 
                              output_path: str):
    """
    Export room timetables to a CSV file.
    
    Args:
        timetables: Dictionary mapping (bldg, room) to RoomTimetable objects
        output_path: Path to output CSV file
    """
    rows = []
    
    for (bldg, room), timetable in timetables.items():
        for slot in timetable.slots:
            rows.append({
                'Building': bldg,
                'Room': room,
                'Day_Number': slot.day,
                'Day_Name': day_number_to_string(slot.day),
                'Start_Time': minutes_to_time_string(slot.start),
                'End_Time': minutes_to_time_string(slot.end),
                'Start_Minutes': slot.start,
                'End_Minutes': slot.end,
                'Subject': slot.subject,
                'Catalog_Nbr': slot.catalog_nbr,
                'Class_Nbr': slot.class_nbr,
                'Lab_Index': slot.lab_index,
                'Course': f"{slot.subject}{slot.catalog_nbr}"
            })
    
    # Sort by building, room, day, start time
    rows.sort(key=lambda x: (
        x['Building'], 
        x['Room'], 
        x['Day_Number'], 
        x['Start_Minutes']
    ))
    
    # Write to CSV
    if rows:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'Building', 'Room', 'Day_Number', 'Day_Name', 
                'Start_Time', 'End_Time', 'Start_Minutes', 'End_Minutes',
                'Subject', 'Catalog_Nbr', 'Class_Nbr', 'Lab_Index', 'Course'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    
    print(f"Room timetable exported to: {output_path}")
    print(f"Total room bookings: {len(rows)}")


def export_fittest_individual(schedule: List[Course], 
                              room_assignments_path: str,
                              course_output_path: str,
                              room_output_path: str):
    """
    Export the fittest individual's course and room timetables to CSV files.
    
    Args:
        schedule: List of Course objects (the fittest individual)
        room_assignments_path: Path to Room_data.csv
        course_output_path: Path for course timetable output
        room_output_path: Path for room timetable output
    """
    print("\n" + "=" * 70)
    print("EXPORTING FITTEST INDIVIDUAL")
    print("=" * 70)
    
    # Load room assignments
    room_assignments = load_room_assignments(room_assignments_path)
    print(f"Loaded {len(room_assignments)} room assignments")
    
    # Create room timetables
    timetables = create_room_timetables(schedule, room_assignments)
    print(f"Created timetables for {len(timetables)} rooms")
    
    # Export course timetable
    export_course_timetable_csv(schedule, course_output_path)
    
    # Export room timetable
    export_room_timetable_csv(timetables, room_output_path)
    
    print("=" * 70)


def display_export_summary(schedule: List[Course], 
                          room_assignments_path: str):
    """
    Display a summary of what will be exported.
    """
    print("\n" + "=" * 70)
    print("EXPORT SUMMARY")
    print("=" * 70)
    
    # Count components
    lecture_count = sum(1 for c in schedule if c.lecture)
    tutorial_count = sum(len([t for t in c.tutorial if t is not None]) 
                        for c in schedule if c.tutorial)
    lab_count = sum(len([l for l in c.lab if l is not None]) 
                   for c in schedule if c.lab)
    
    print(f"Courses: {len(schedule)}")
    print(f"  Lectures: {lecture_count}")
    print(f"  Tutorials: {tutorial_count}")
    print(f"  Labs: {lab_count}")
    
    # Count courses with room assignments
    room_assignments = load_room_assignments(room_assignments_path)
    courses_with_rooms = 0
    
    for course in schedule:
        for assignment in room_assignments:
            if assignment.matches_course(course):
                courses_with_rooms += 1
                break
    
    print(f"\nCourses with room assignments: {courses_with_rooms}/{len(schedule)}")
    print(f"Total rooms: {len(room_assignments)}")
    
    print("=" * 70)
