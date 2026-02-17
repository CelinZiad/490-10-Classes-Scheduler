# scheduleterm_export.py
from typing import List, Dict, Tuple
from datetime import date
from .db import get_connection, fetch_all
from genetic_algo.course import Course


EXCLUDED_COURSES = {
    ('ELEC', '430'), ('ELEC', '434'), ('ELEC', '436'), ('ELEC', '438'),
    ('ELEC', '446'), ('ELEC', '443'), ('ELEC', '498')
}


def should_exclude_course(subject: str, catalog: str) -> bool:
    """Check if course should be excluded from scheduling."""
    return (subject, catalog) in EXCLUDED_COURSES


def build_termcode(year: int, season: int) -> str:
    """Build termcode from year and season (Format: 2 + YY + S)."""
    year_suffix = str(year)[-2:]
    return f"2{year_suffix}{season}"


def get_session_code(season: int, previous_session: str = None) -> str:
    """Get session code based on season."""
    if season == 2 or season == 4:
        return "13W"
    elif season == 3:
        return "26W"
    elif season == 1:
        return previous_session if previous_session else "13W"
    return "13W"


def get_class_dates(season: int, componentcode: str, session: str = None, 
                   day_numbers: List[int] = None) -> Tuple[str, str]:
    """Get class start and end dates based on season, component, and days."""
    if componentcode in ('LEC', 'TUT'):
        if season == 2:
            return ('2026-09-08', '2026-12-07')
        elif season == 4:
            return ('2027-01-11', '2027-04-12')
        elif season == 3:
            return ('2026-09-08', '2027-04-12')
        elif season == 1 and session == '13W':
            return ('2026-05-11', '2026-08-12')
    
    elif componentcode == 'LAB' and day_numbers:
        has_week1 = any(d in [1, 2, 3, 4, 5] for d in day_numbers)
        has_week2 = any(d in [8, 9, 10, 11, 12] for d in day_numbers)
        
        if season == 2:
            if has_week1 and not has_week2:
                return ('2026-09-20', '2026-09-26')
            elif has_week2 and not has_week1:
                return ('2026-09-27', '2026-10-03')
            elif has_week1 and has_week2:
                return ('2026-09-20', '2026-10-03')
        
        elif season == 4:
            if has_week1 and not has_week2:
                return ('2027-01-24', '2027-01-30')
            elif has_week2 and not has_week1:
                return ('2027-01-31', '2027-02-06')
            elif has_week1 and has_week2:
                return ('2027-01-24', '2027-02-06')
        
        elif season == 3:
            return ('', '')
    
    return ('', '')


def get_previous_year_data(subject: str, catalog: str, section: str, 
                           componentcode: str, previous_year_cache: Dict) -> Dict:
    """Get data from previous academic year cache."""
    key = (subject, catalog, section, componentcode)
    
    if key in previous_year_cache:
        return previous_year_cache[key]
    
    alt_key = (subject, catalog, componentcode)
    if alt_key in previous_year_cache:
        return previous_year_cache[alt_key]
    
    return {
        'classnumber': None,
        'session': '13W',
        'instructionmodecode': 'P',
        'locationcode': 'SGW',
        'career': 'UGRD'
    }


def build_previous_year_cache(previous_termcode: str) -> Dict:
    """Build a cache of previous year's schedule data."""
    sql = """
        SELECT subject, catalog, section, componentcode, classnumber,
               session, instructionmodecode, locationcode, career
        FROM scheduleterm
        WHERE termcode = %s
          AND departmentcode = 'ELECCOEN'
          AND meetingpatternnumber = 1
    """
    
    records = fetch_all(sql, (previous_termcode,))
    
    cache = {}
    for record in records:
        key = (record['subject'], record['catalog'], record['section'], record['componentcode'])
        cache[key] = {
            'classnumber': record['classnumber'],
            'session': record.get('session', '13W'),
            'instructionmodecode': record.get('instructionmodecode', 'P'),
            'locationcode': record.get('locationcode', 'SGW'),
            'career': record.get('career', 'UGRD')
        }
        
        alt_key = (record['subject'], record['catalog'], record['componentcode'])
        if alt_key not in cache:
            cache[alt_key] = cache[key]
    
    return cache


def create_scheduleterm_table():
    """Create optimized_schedule table with full scheduleterm structure."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DROP TABLE IF EXISTS optimized_schedule CASCADE")
        
        cursor.execute("""
            CREATE TABLE optimized_schedule (
                id SERIAL PRIMARY KEY,
                subject VARCHAR(10),
                catalog VARCHAR(10),
                section VARCHAR(20),
                componentcode VARCHAR(10),
                termcode VARCHAR(10),
                classnumber VARCHAR(20),
                session VARCHAR(10),
                buildingcode VARCHAR(10),
                room VARCHAR(20),
                instructionmodecode VARCHAR(10),
                locationcode VARCHAR(10),
                currentwaitlisttotal INTEGER DEFAULT 0,
                waitlistcapacity INTEGER DEFAULT 0,
                enrollmentcapacity INTEGER DEFAULT 0,
                currentenrollment INTEGER DEFAULT 0,
                departmentcode VARCHAR(20),
                facultycode VARCHAR(20),
                classstarttime TIME,
                classendtime TIME,
                classstartdate DATE,
                classenddate DATE,
                mondays BOOLEAN DEFAULT false,
                tuesdays BOOLEAN DEFAULT false,
                wednesdays BOOLEAN DEFAULT false,
                thursdays BOOLEAN DEFAULT false,
                fridays BOOLEAN DEFAULT false,
                saturdays BOOLEAN DEFAULT false,
                sundays BOOLEAN DEFAULT false,
                facultydescription TEXT,
                career VARCHAR(10),
                meetingpatternnumber INTEGER DEFAULT 1
            )
        """)
        
        cursor.execute("CREATE INDEX idx_opt_subject_catalog ON optimized_schedule(subject, catalog)")
        cursor.execute("CREATE INDEX idx_opt_section ON optimized_schedule(section)")
        cursor.execute("CREATE INDEX idx_opt_component ON optimized_schedule(componentcode)")
        cursor.execute("CREATE INDEX idx_opt_termcode ON optimized_schedule(termcode)")
        
        conn.commit()
        return True
        
    except Exception:
        conn.rollback()
        return False
        
    finally:
        cursor.close()
        conn.close()


def minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight to HH:MM:SS format."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}:00"


def day_number_to_day_columns(day_num: int) -> Dict[str, bool]:
    """Convert day number to boolean day columns (1-5 Week 1, 8-12 Week 2)."""
    day_map = {
        1: 'mondays', 2: 'tuesdays', 3: 'wednesdays', 4: 'thursdays', 5: 'fridays',
        8: 'mondays', 9: 'tuesdays', 10: 'wednesdays', 11: 'thursdays', 12: 'fridays'
    }
    
    result = {
        'mondays': False, 'tuesdays': False, 'wednesdays': False,
        'thursdays': False, 'fridays': False, 'saturdays': False, 'sundays': False
    }
    
    day_col = day_map.get(day_num)
    if day_col:
        result[day_col] = True
    
    return result


def combine_day_columns(day_numbers: List[int]) -> Dict[str, bool]:
    """Combine multiple day numbers into single set of day columns."""
    result = {
        'mondays': False, 'tuesdays': False, 'wednesdays': False,
        'thursdays': False, 'fridays': False, 'saturdays': False, 'sundays': False
    }
    
    for day_num in day_numbers:
        day_cols = day_number_to_day_columns(day_num)
        for day, value in day_cols.items():
            if value:
                result[day] = True
    
    return result


def extract_day_numbers(day_enum):
    """Extract day numbers from Day enum."""
    if isinstance(day_enum, int):
        return [day_enum]
    
    day_str = str(day_enum)
    
    if 'Week1' in day_str or 'Week2' in day_str:
        day_map = {
            'Week1Monday': 1, 'Week1Tuesday': 2, 'Week1Wednesday': 3,
            'Week1Thursday': 4, 'Week1Friday': 5,
            'Week2Monday': 8, 'Week2Tuesday': 9, 'Week2Wednesday': 10,
            'Week2Thursday': 11, 'Week2Friday': 12
        }
        for key, val in day_map.items():
            if key in day_str:
                return [val]
    
    return [day_enum] if isinstance(day_enum, int) else []


def insert_lecture_records(termcode: str, season: int, previous_termcode: str) -> int:
    """Insert lecture records from previous year into optimized_schedule."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        sql = """
            SELECT subject, catalog, section, componentcode, classnumber,
                   session, buildingcode, room, instructionmodecode, locationcode,
                   currentwaitlisttotal, waitlistcapacity, enrollmentcapacity, currentenrollment,
                   departmentcode, facultycode, classstarttime, classendtime,
                   mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays,
                   facultydescription, career
            FROM scheduleterm
            WHERE termcode = %s
              AND departmentcode = 'ELECCOEN'
              AND componentcode = 'LEC'
              AND meetingpatternnumber = 1
              AND classstarttime != '00:00:00'
        """
        
        lectures = fetch_all(sql, (previous_termcode,))
        
        count = 0
        session_code = get_session_code(season)
        start_date, end_date = get_class_dates(season, 'LEC', session_code)
        
        for lec in lectures:
            if should_exclude_course(lec['subject'], lec['catalog']):
                continue
            
            cursor.execute("""
                INSERT INTO optimized_schedule
                (subject, catalog, section, componentcode, termcode, classnumber,
                 session, buildingcode, room, instructionmodecode, locationcode,
                 currentwaitlisttotal, waitlistcapacity, enrollmentcapacity, currentenrollment,
                 departmentcode, facultycode, classstarttime, classendtime,
                 classstartdate, classenddate,
                 mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays,
                 facultydescription, career, meetingpatternnumber)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                lec['subject'], lec['catalog'], lec['section'], 'LEC', termcode,
                lec['classnumber'], session_code, lec['buildingcode'], lec['room'],
                lec['instructionmodecode'], lec['locationcode'],
                lec['currentwaitlisttotal'], lec['waitlistcapacity'],
                lec['enrollmentcapacity'], lec['currentenrollment'],
                lec['departmentcode'], lec['facultycode'],
                lec['classstarttime'], lec['classendtime'],
                start_date if start_date else None, end_date if end_date else None,
                lec['mondays'], lec['tuesdays'], lec['wednesdays'],
                lec['thursdays'], lec['fridays'], lec['saturdays'], lec['sundays'],
                lec['facultydescription'], lec['career'], 1
            ))
            count += 1
        
        conn.commit()
        return count
        
    except Exception:
        conn.rollback()
        raise
        
    finally:
        cursor.close()
        conn.close()


def insert_optimized_components(schedule: List[Course], room_assignments,
                                termcode: str, season: int, previous_year_cache: Dict) -> int:
    """Insert optimized tutorials and labs into optimized_schedule."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        count = 0
        tutorial_count = 0
        lab_count = 0
        
        for course in schedule:
            if should_exclude_course(course.subject, course.catalog_nbr):
                continue
            
            building = ''
            room = ''
            if isinstance(room_assignments, list):
                for assignment in room_assignments:
                    if (assignment.subject.strip().upper() == course.subject.upper() and 
                        course.catalog_nbr in assignment.catalog_nbrs):
                        building = assignment.bldg
                        room = assignment.room
                        break
            elif isinstance(room_assignments, dict):
                key = (course.subject, course.catalog_nbr)
                building, room = room_assignments.get(key, ('', ''))
            
            section = course.class_nbr
            
            if course.tutorial:
                prev_tut = get_previous_year_data(
                    course.subject, course.catalog_nbr, section, 'TUT', previous_year_cache
                )
                
                session = get_session_code(season, prev_tut['session'])
                start_date, end_date = get_class_dates(season, 'TUT', session)
                career = 'GRAD' if course.catalog_nbr.startswith('6') else 'UGRD'
                instruction_mode = prev_tut['instructionmodecode']
                location = 'SGW' if instruction_mode == 'P' else 'ONL'
                
                for tut_idx, tut in enumerate(course.tutorial):
                    if tut is None or not tut.day:
                        continue
                    all_day_numbers = []
                    for day_enum in tut.day:
                        all_day_numbers.extend(extract_day_numbers(day_enum))
                    
                    day_cols = combine_day_columns(all_day_numbers)
                    
                    cursor.execute("""
                        INSERT INTO optimized_schedule
                        (subject, catalog, section, componentcode, termcode, classnumber,
                         session, buildingcode, room, instructionmodecode, locationcode,
                         currentwaitlisttotal, waitlistcapacity, enrollmentcapacity, currentenrollment,
                         departmentcode, facultycode, classstarttime, classendtime,
                         classstartdate, classenddate,
                         mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays,
                         facultydescription, career, meetingpatternnumber)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        course.subject, course.catalog_nbr, section, 'TUT', termcode,
                        prev_tut['classnumber'], session, '', '', instruction_mode, location,
                        0, 0, 0, 0, 'ELECCOEN', 'ENCS',
                        minutes_to_time(tut.start), minutes_to_time(tut.end),
                        start_date if start_date else None, end_date if end_date else None,
                        day_cols['mondays'], day_cols['tuesdays'], day_cols['wednesdays'],
                        day_cols['thursdays'], day_cols['fridays'], day_cols['saturdays'],
                        day_cols['sundays'],
                        'Gina Cody School of Engineering & Computer Science', career, 1
                    ))
                    count += 1
                    tutorial_count += 1
            
            if course.lab:
                prev_lab = get_previous_year_data(
                    course.subject, course.catalog_nbr, section, 'LAB', previous_year_cache
                )
                
                session = get_session_code(season, prev_lab['session'])
                career = 'GRAD' if course.catalog_nbr.startswith('6') else 'UGRD'
                instruction_mode = prev_lab['instructionmodecode']
                location = 'SGW' if instruction_mode == 'P' else 'ONL'
                buildingcode = building if building else ''

                for lab_idx, lab in enumerate(course.lab):
                    if lab is None or not lab.day:
                        continue
                    all_day_numbers = []
                    for day_enum in lab.day:
                        all_day_numbers.extend(extract_day_numbers(day_enum))
                    
                    start_date, end_date = get_class_dates(season, 'LAB', session, all_day_numbers)
                    day_cols = combine_day_columns(all_day_numbers)
                    
                    cursor.execute("""
                        INSERT INTO optimized_schedule
                        (subject, catalog, section, componentcode, termcode, classnumber,
                         session, buildingcode, room, instructionmodecode, locationcode,
                         currentwaitlisttotal, waitlistcapacity, enrollmentcapacity, currentenrollment,
                         departmentcode, facultycode, classstarttime, classendtime,
                         classstartdate, classenddate,
                         mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays,
                         facultydescription, career, meetingpatternnumber)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        course.subject, course.catalog_nbr, section, 'LAB', termcode,
                        prev_lab['classnumber'], session, buildingcode, room,
                        instruction_mode, location,
                        0, 0, 16, 0,
                        'ELECCOEN', 'ENCS',
                        minutes_to_time(lab.start), minutes_to_time(lab.end),
                        start_date if start_date else None, end_date if end_date else None,
                        day_cols['mondays'], day_cols['tuesdays'], day_cols['wednesdays'],
                        day_cols['thursdays'], day_cols['fridays'], day_cols['saturdays'],
                        day_cols['sundays'],
                        'Gina Cody School of Engineering & Computer Science', career, 1
                    ))
                    count += 1
                    lab_count += 1
        
        conn.commit()
        return count
        
    except Exception:
        conn.rollback()
        raise
        
    finally:
        cursor.close()
        conn.close()


def export_to_scheduleterm_format(schedule: List[Course], room_assignments,
                                   year: int, season: int) -> bool:
    """Export complete timetable in scheduleterm format."""
    try:
        termcode = build_termcode(year, season)
        previous_year = year - 1
        previous_termcode = build_termcode(previous_year, season)
        
        previous_year_cache = build_previous_year_cache(previous_termcode)
        
        if not create_scheduleterm_table():
            return False
        
        insert_lecture_records(termcode, season, previous_termcode)
        insert_optimized_components(schedule, room_assignments, termcode, season, previous_year_cache)
        
        return True
        
    except Exception:
        return False


if __name__ == "__main__":
    create_scheduleterm_table()
