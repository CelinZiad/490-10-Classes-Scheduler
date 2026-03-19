# export_utils.py
import csv
from typing import List, Dict, Tuple
from genetic_algo.course import Course
from genetic_algo.room_management import RoomTimetable, create_room_timetables, load_room_assignments
from .time_utils import minutes_to_time_short as minutes_to_time_string


def day_number_to_string(day) -> str:
    """Convert day number (1-14) to readable format (Days 1-7 Week 1, Days 8-14 Week 2)."""
    from genetic_algo.day import Day
    
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
    """Extract day numbers from a list that may contain Day enum objects or integers."""
    from genetic_algo.day import Day
    
    result = []
    for day in day_list:
        if isinstance(day, Day):
            result.extend([day.first, day.second])
        elif isinstance(day, int):
            result.append(day)
    return result


def _fetch_passthrough_course_rows(year: int, season: int) -> List[Dict]:
    """Fetch pass-through courses (ELEC 490, COEN 490) from the previous year's
    scheduleterm and return them as rows matching the course timetable CSV format.
    
    Only applies for fall (season 2) and winter (season 4).
    """
    if season not in (2, 4):
        return []

    from .db import fetch_all

    PASSTHROUGH_COURSES = {('ELEC', '490'), ('COEN', '490')}
    clauses = []
    filter_params = []
    for subj, cat in PASSTHROUGH_COURSES:
        clauses.append("(subject = %s AND catalog = %s)")
        filter_params.extend([subj, cat])
    filter_clause = ' OR '.join(clauses)

    previous_year = year - 1
    # Build termcodes for the target season and Fall+Winter (season 3)
    year_suffix = str(previous_year)[-2:]
    prev_termcode = f"2{year_suffix}{season}"
    fw_termcode = f"2{year_suffix}3"

    sql = f"""
        SELECT subject, catalog, section, componentcode, classnumber,
               buildingcode, room, classstarttime, classendtime,
               mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays,
               meetingpatternnumber
        FROM scheduleterm
        WHERE termcode IN (%s, %s)
          AND departmentcode = 'ELECCOEN'
          AND classstartdate != '0001-01-01'
          AND ({filter_clause})
        ORDER BY subject, catalog, classnumber, componentcode, meetingpatternnumber
    """
    records = fetch_all(sql, (prev_termcode, fw_termcode, *filter_params))

    component_map = {'LEC': 'Lecture', 'TUT': 'Tutorial', 'LAB': 'Lab'}
    day_col_to_num = {
        'mondays': 1, 'tuesdays': 2, 'wednesdays': 3,
        'thursdays': 4, 'fridays': 5, 'saturdays': 6, 'sundays': 7
    }

    rows = []
    for r in records:
        comp_type = component_map.get(r['componentcode'])
        if not comp_type:
            continue

        # Parse start/end times to minutes
        start_time = r['classstarttime']
        end_time = r['classendtime']
        if hasattr(start_time, 'hour'):
            start_min = start_time.hour * 60 + start_time.minute
            end_min = end_time.hour * 60 + end_time.minute
            start_str = f"{start_time.hour:02d}:{start_time.minute:02d}"
            end_str = f"{end_time.hour:02d}:{end_time.minute:02d}"
        else:
            start_str = str(start_time) if start_time else "00:00"
            end_str = str(end_time) if end_time else "00:00"
            start_min = 0
            end_min = 0

        # Extract day numbers from boolean columns
        for col, day_num in day_col_to_num.items():
            if r.get(col) == True or str(r.get(col)).lower() == 'true':
                rows.append({
                    'Type': comp_type,
                    'Subject': r['subject'],
                    'Catalog_Nbr': r['catalog'],
                    'Class_Nbr': r['section'],
                    'Component_Index': 0,
                    'Day_Number': day_num,
                    'Day_Name': day_number_to_string(day_num),
                    'Start_Time': start_str,
                    'End_Time': end_str,
                    'Start_Minutes': start_min,
                    'End_Minutes': end_min,
                    'Building': r['buildingcode'] or '',
                    'Room': r['room'] or ''
                })

    return rows


def export_course_timetable_csv(schedule: List[Course], output_path: str,
                                year: int = None, season: int = None):
    """Export the course timetable (lectures, tutorials, labs) to a CSV file.
    
    If year and season are provided, also includes pass-through courses
    (ELEC 490, COEN 490) fetched from the previous year's scheduleterm.
    """
    # Cross-listed courses: ELEC 390 rows are duplicated as COEN 390
    CROSS_LISTED = {
        ('ELEC', '390'): ('COEN', '390'),
    }

    rows = []
    
    for course in schedule:
        if course.lecture:
            lecture = course.lecture
            lec_section = lecture.section or course.lec_section or course.class_nbr
            day_numbers = extract_day_numbers(lecture.day)
            for day in day_numbers:
                row = {
                    'Type': 'Lecture',
                    'Subject': course.subject,
                    'Catalog_Nbr': course.catalog_nbr,
                    'Class_Nbr': course.class_nbr,
                    'Section': lec_section,
                    'Component_Index': 0,
                    'Day_Number': day,
                    'Day_Name': day_number_to_string(day),
                    'Start_Time': minutes_to_time_string(lecture.start),
                    'End_Time': minutes_to_time_string(lecture.end),
                    'Start_Minutes': lecture.start,
                    'End_Minutes': lecture.end,
                    'Building': lecture.bldg or '',
                    'Room': lecture.room or ''
                }
                rows.append(row)
                source_key = (course.subject, course.catalog_nbr)
                if source_key in CROSS_LISTED:
                    clone_subj, clone_cat = CROSS_LISTED[source_key]
                    clone_row = dict(row)
                    clone_row['Subject'] = clone_subj
                    clone_row['Catalog_Nbr'] = clone_cat
                    rows.append(clone_row)
        
        if course.tutorial:
            for tut_index, tut in enumerate(course.tutorial):
                if tut is None or not tut.day:
                    continue
                tut_section = tut.section or course.lec_section or course.class_nbr
                day_numbers = extract_day_numbers(tut.day)
                for day in day_numbers:
                    row = {
                        'Type': 'Tutorial',
                        'Subject': course.subject,
                        'Catalog_Nbr': course.catalog_nbr,
                        'Class_Nbr': course.class_nbr,
                        'Section': tut_section,
                        'Component_Index': tut_index,
                        'Day_Number': day,
                        'Day_Name': day_number_to_string(day),
                        'Start_Time': minutes_to_time_string(tut.start),
                        'End_Time': minutes_to_time_string(tut.end),
                        'Start_Minutes': tut.start,
                        'End_Minutes': tut.end,
                        'Building': tut.bldg or '',
                        'Room': tut.room or ''
                    }
                    rows.append(row)
                    source_key = (course.subject, course.catalog_nbr)
                    if source_key in CROSS_LISTED:
                        clone_subj, clone_cat = CROSS_LISTED[source_key]
                        clone_row = dict(row)
                        clone_row['Subject'] = clone_subj
                        clone_row['Catalog_Nbr'] = clone_cat
                        rows.append(clone_row)
        
        if course.lab:
            for lab_index, lab in enumerate(course.lab):
                if lab is None or not lab.day:
                    continue
                lab_section = lab.section or course.lec_section or course.class_nbr
                day_numbers = extract_day_numbers(lab.day)
                for day in day_numbers:
                    row = {
                        'Type': 'Lab',
                        'Subject': course.subject,
                        'Catalog_Nbr': course.catalog_nbr,
                        'Class_Nbr': course.class_nbr,
                        'Section': lab_section,
                        'Component_Index': lab_index,
                        'Day_Number': day,
                        'Day_Name': day_number_to_string(day),
                        'Start_Time': minutes_to_time_string(lab.start),
                        'End_Time': minutes_to_time_string(lab.end),
                        'Start_Minutes': lab.start,
                        'End_Minutes': lab.end,
                        'Building': lab.bldg or '',
                        'Room': lab.room or ''
                    }
                    rows.append(row)
                    source_key = (course.subject, course.catalog_nbr)
                    if source_key in CROSS_LISTED:
                        clone_subj, clone_cat = CROSS_LISTED[source_key]
                        clone_row = dict(row)
                        clone_row['Subject'] = clone_subj
                        clone_row['Catalog_Nbr'] = clone_cat
                        rows.append(clone_row)
    
    # Append pass-through courses from previous year's scheduleterm
    if year is not None and season is not None:
        passthrough_rows = _fetch_passthrough_course_rows(year, season)
        # Ensure passthrough rows have a Section field
        for r in passthrough_rows:
            if 'Section' not in r:
                r['Section'] = r.get('Class_Nbr', '')
        rows.extend(passthrough_rows)

    rows.sort(key=lambda x: (
        x['Subject'], x['Catalog_Nbr'], x['Class_Nbr'],
        x['Type'], x['Day_Number'], x['Start_Minutes']
    ))
    
    if rows:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'Type', 'Subject', 'Catalog_Nbr', 'Class_Nbr', 'Section',
                'Component_Index',
                'Day_Number', 'Day_Name', 'Start_Time', 'End_Time', 
                'Start_Minutes', 'End_Minutes', 'Building', 'Room'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def export_room_timetable_csv(timetables: Dict[Tuple[str, str], RoomTimetable], 
                              output_path: str):
    """Export room timetables to a CSV file."""
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
    
    rows.sort(key=lambda x: (
        x['Building'], x['Room'], x['Day_Number'], x['Start_Minutes']
    ))
    
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


def export_fittest_individual(schedule: List[Course], 
                              room_assignments_path: str,
                              course_output_path: str,
                              room_output_path: str,
                              year: int = None,
                              season: int = None):
    """Export the fittest individual's course and room timetables to CSV files.
    
    If year and season are provided, also includes pass-through courses
    (ELEC 490, COEN 490) and excluded-but-output courses (COEN 390)
    from the previous year's scheduleterm data.
    """
    room_assignments = load_room_assignments(room_assignments_path)
    timetables = create_room_timetables(schedule, room_assignments)
    export_course_timetable_csv(schedule, course_output_path,
                                year=year, season=season)
    export_room_timetable_csv(timetables, room_output_path)


def display_export_summary(schedule: List[Course], 
                          room_assignments_path: str):
    """Display a summary of what will be exported."""
    lecture_count = sum(1 for c in schedule if c.lecture)
    tutorial_count = sum(len([t for t in c.tutorial if t is not None]) 
                        for c in schedule if c.tutorial)
    lab_count = sum(len([l for l in c.lab if l is not None]) 
                   for c in schedule if c.lab)
    
    room_assignments = load_room_assignments(room_assignments_path)
    courses_with_rooms = 0
    
    for course in schedule:
        for assignment in room_assignments:
            if assignment.matches_course(course):
                courses_with_rooms += 1
                break