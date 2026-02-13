# scheduleterm_export.py
"""
Export optimized timetable to match scheduleterm table structure exactly.
Includes lectures, tutorials, and labs with all required columns.
"""

from typing import List, Dict, Tuple
from datetime import date
from db import get_connection, fetch_all
from course import Course


# Courses to exclude entirely
EXCLUDED_COURSES = {
    ('ELEC', '430'),
    ('ELEC', '434'),
    ('ELEC', '436'),
    ('ELEC', '438'),
    ('ELEC', '446'),
    ('ELEC', '443'),
    ('ELEC', '498')
}


def should_exclude_course(subject: str, catalog: str) -> bool:
    """Check if course should be excluded from scheduling."""
    return (subject, catalog) in EXCLUDED_COURSES


def build_termcode(year: int, season: int) -> str:
    """
    Build termcode from year and season.
    
    Format: 2 + YY + S
    - 2 = constant
    - YY = last 2 digits of year (e.g., 26 for 2026)
    - S = season (1=summer, 2=fall, 3=fall+winter, 4=winter)
    
    Args:
        year: Academic year (e.g., 2026)
        season: Season code (1, 2, 3, or 4)
    
    Returns:
        Termcode string (e.g., "2262" for Fall 2026)
    """
    year_suffix = str(year)[-2:]
    return f"2{year_suffix}{season}"


def get_session_code(season: int, previous_session: str = None) -> str:
    """
    Get session code based on season.
    
    Args:
        season: Season code (1, 2, 3, or 4)
        previous_session: Previous year's session (for summer courses)
    
    Returns:
        Session code (e.g., "13W", "26W", "6H1", "6H2")
    """
    if season == 2 or season == 4:
        return "13W"
    elif season == 3:
        return "26W"
    elif season == 1:
        # Summer: use previous year's session if available
        return previous_session if previous_session else "13W"
    return "13W"


def get_class_dates(season: int, componentcode: str, session: str = None, 
                   day_numbers: List[int] = None) -> Tuple[str, str]:
    """
    Get class start and end dates based on season, component, and days.
    
    Args:
        season: Season code (1, 2, 3, or 4)
        componentcode: Component type (LEC, TUT, LAB)
        session: Session code (for summer courses)
        day_numbers: List of day numbers for labs (to determine week)
    
    Returns:
        Tuple of (classstartdate, classenddate) as strings or empty strings
    """
    # LEC and TUT get term-wide dates
    if componentcode in ('LEC', 'TUT'):
        if season == 2:  # Fall
            return ('2026-09-08', '2026-12-07')
        elif season == 4:  # Winter
            return ('2027-01-11', '2027-04-12')
        elif season == 3:  # Fall + Winter
            return ('2026-09-08', '2027-04-12')
        elif season == 1 and session == '13W':  # Summer 13W
            return ('2026-05-11', '2026-08-12')
    
    # LAB gets week-specific dates
    elif componentcode == 'LAB' and day_numbers:
        # Determine which week(s) the lab occurs
        has_week1 = any(d in [1, 2, 3, 4, 5] for d in day_numbers)
        has_week2 = any(d in [8, 9, 10, 11, 12] for d in day_numbers)
        
        if season == 2:  # Fall
            if has_week1 and not has_week2:
                # Week 1 only
                return ('2026-09-20', '2026-09-26')
            elif has_week2 and not has_week1:
                # Week 2 only
                return ('2026-09-27', '2026-10-03')
            elif has_week1 and has_week2:
                # Both weeks - use week 1 start, week 2 end
                return ('2026-09-20', '2026-10-03')
        
        elif season == 4:  # Winter
            if has_week1 and not has_week2:
                # Week 1 only
                return ('2027-01-24', '2027-01-30')
            elif has_week2 and not has_week1:
                # Week 2 only
                return ('2027-01-31', '2027-02-06')
            elif has_week1 and has_week2:
                # Both weeks - use week 1 start, week 2 end
                return ('2027-01-24', '2027-02-06')
        
        # Season 3 (Fall+Winter) - no labs per requirements
        elif season == 3:
            return ('', '')
    
    # Default: no dates
    return ('', '')


def get_previous_year_data(subject: str, catalog: str, section: str, 
                           componentcode: str, previous_year_cache: Dict) -> Dict:
    """
    Get data from previous academic year cache.
    
    Args:
        subject: Course subject
        catalog: Course catalog number
        section: Section identifier
        componentcode: Component type (LEC, TUT, LAB)
        previous_year_cache: Dictionary of previous year's data
    
    Returns:
        Dictionary with previous year's data or defaults
    """
    # Build cache key
    key = (subject, catalog, section, componentcode)
    
    if key in previous_year_cache:
        return previous_year_cache[key]
    
    # Try without section (for tutorials/labs that might have different sections)
    alt_key = (subject, catalog, componentcode)
    if alt_key in previous_year_cache:
        return previous_year_cache[alt_key]
    
    # Defaults if not found
    return {
        'classnumber': None,
        'session': '13W',
        'instructionmodecode': 'P',
        'locationcode': 'SGW',
        'career': 'UGRD'
    }


def build_previous_year_cache(previous_termcode: str) -> Dict:
    """
    Build a cache of previous year's schedule data.
    
    Args:
        previous_termcode: Previous year's termcode
    
    Returns:
        Dictionary with previous year's data keyed by (subject, catalog, section, componentcode)
    """
    print(f"\n  Building cache from previous year (termcode {previous_termcode})...")
    
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
        # Full key with section
        key = (record['subject'], record['catalog'], record['section'], record['componentcode'])
        cache[key] = {
            'classnumber': record['classnumber'],
            'session': record.get('session', '13W'),
            'instructionmodecode': record.get('instructionmodecode', 'P'),
            'locationcode': record.get('locationcode', 'SGW'),
            'career': record.get('career', 'UGRD')
        }
        
        # Also store by component type only (fallback)
        alt_key = (record['subject'], record['catalog'], record['componentcode'])
        if alt_key not in cache:
            cache[alt_key] = cache[key]
    
    print(f"  Cached {len(cache)} records from previous year")
    return cache


def day_number_to_day_columns(day_num: int) -> Dict[str, bool]:
    """Convert day number to boolean day columns."""
    day_map = {
        1: 'mondays', 2: 'tuesdays', 3: 'wednesdays',
        4: 'thursdays', 5: 'fridays',
        8: 'mondays', 9: 'tuesdays', 10: 'wednesdays',
        11: 'thursdays', 12: 'fridays'
    }
    
    result = {
        'mondays': False, 'tuesdays': False, 'wednesdays': False,
        'thursdays': False, 'fridays': False, 'saturdays': False,
        'sundays': False
    }
    
    day_col = day_map.get(day_num)
    if day_col:
        result[day_col] = True
    
    return result


def combine_day_columns(day_numbers: List[int]) -> Dict[str, bool]:
    """
    Combine multiple day numbers into a single set of day columns.
    This prevents duplication when a class meets on the same weekday in both weeks.
    
    Args:
        day_numbers: List of day numbers (e.g., [1, 8] for Monday both weeks)
    
    Returns:
        Dictionary with consolidated boolean day columns
        
    Example:
        [1, 8, 3, 10] → {mondays: True, wednesdays: True, rest: False}
        (Meets every Monday and Wednesday)
    """
    day_cols = {
        'mondays': False, 'tuesdays': False, 'wednesdays': False,
        'thursdays': False, 'fridays': False, 'saturdays': False,
        'sundays': False
    }
    
    for day_num in day_numbers:
        if day_num in [1, 8]:  # Monday (either week)
            day_cols['mondays'] = True
        elif day_num in [2, 9]:  # Tuesday
            day_cols['tuesdays'] = True
        elif day_num in [3, 10]:  # Wednesday
            day_cols['wednesdays'] = True
        elif day_num in [4, 11]:  # Thursday
            day_cols['thursdays'] = True
        elif day_num in [5, 12]:  # Friday
            day_cols['fridays'] = True
        elif day_num in [6, 13]:  # Saturday
            day_cols['saturdays'] = True
        elif day_num in [7, 14]:  # Sunday
            day_cols['sundays'] = True
    
    return day_cols


def minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight to HH:MM:SS format."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}:00"


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


def create_scheduleterm_table():
    """
    Create optimized_schedule table matching scheduleterm structure exactly.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        print("\n" + "=" * 70)
        print("CREATING OPTIMIZED_SCHEDULE TABLE (SCHEDULETERM FORMAT)")
        print("=" * 70)
        
        # Drop existing table
        print("\nDropping existing table (if any)...")
        cursor.execute("DROP TABLE IF EXISTS optimized_schedule CASCADE")
        print("  Done")
        
        # Create table with all scheduleterm columns
        print("\nCreating optimized_schedule table...")
        cursor.execute("""
            CREATE TABLE optimized_schedule (
                cid SERIAL PRIMARY KEY,
                subject VARCHAR(10),
                catalog VARCHAR(10),
                section VARCHAR(20),
                componentcode VARCHAR(10),
                termcode VARCHAR(10),
                classnumber INTEGER,
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
                facultycode VARCHAR(10),
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
        print("  ✓ optimized_schedule table created")
        
        # Create indexes
        print("\nCreating indexes...")
        cursor.execute("CREATE INDEX idx_opt_subject_catalog ON optimized_schedule(subject, catalog)")
        cursor.execute("CREATE INDEX idx_opt_section ON optimized_schedule(section)")
        cursor.execute("CREATE INDEX idx_opt_component ON optimized_schedule(componentcode)")
        cursor.execute("CREATE INDEX idx_opt_termcode ON optimized_schedule(termcode)")
        print("  ✓ Indexes created")
        
        conn.commit()
        print("\n✓ Table created successfully")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error creating table: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        cursor.close()
        conn.close()


def insert_lecture_records(termcode: str, season: int, previous_termcode: str) -> int:
    """
    Insert lecture records from scheduleterm (previous year).
    
    Args:
        termcode: New termcode (e.g., "2262")
        season: Season code (1, 2, 3, or 4)
        previous_termcode: Previous year's termcode
    
    Returns:
        Number of records inserted
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        count = 0
        
        # Fetch lectures from previous year
        sql = """
            SELECT subject, catalog, section, classnumber, session, buildingcode, room,
                   instructionmodecode, locationcode, classstarttime, classendtime,
                   mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays,
                   career
            FROM scheduleterm
            WHERE termcode = %s
              AND departmentcode = 'ELECCOEN'
              AND componentcode = 'LEC'
              AND meetingpatternnumber = 1
              AND classstarttime != '00:00:00'
        """
        
        lectures = fetch_all(sql, (previous_termcode,))
        
        print(f"\n  Found {len(lectures)} lectures from previous year")
        
        for lec in lectures:
            # Check if should exclude
            if should_exclude_course(lec['subject'], lec['catalog']):
                continue
            
            # Get session code
            session = get_session_code(season, lec.get('session'))
            
            # Get class dates
            start_date, end_date = get_class_dates(season, 'LEC', session)
            
            # Determine career
            career = 'GRAD' if lec['catalog'].startswith('6') else 'UGRD'
            
            # Insert lecture
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
                lec['subject'],
                lec['catalog'],
                lec['section'],
                'LEC',
                termcode,
                lec['classnumber'],
                session,
                lec.get('buildingcode', ''),
                lec.get('room', ''),
                lec.get('instructionmodecode', 'P'),
                lec.get('locationcode', 'SGW'),
                0,  # currentwaitlisttotal
                0,  # waitlistcapacity
                0,  # enrollmentcapacity
                0,  # currentenrollment
                'ELECCOEN',
                'ENCS',
                lec.get('classstarttime'),
                lec.get('classendtime'),
                start_date if start_date else None,
                end_date if end_date else None,
                lec.get('mondays', False),
                lec.get('tuesdays', False),
                lec.get('wednesdays', False),
                lec.get('thursdays', False),
                lec.get('fridays', False),
                lec.get('saturdays', False),
                lec.get('sundays', False),
                'Gina Cody School of Engineering & Computer Science',
                career,
                1  # meetingpatternnumber
            ))
            count += 1
        
        conn.commit()
        print(f"  ✓ Inserted {count} lecture records")
        return count
        
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Error inserting lectures: {e}")
        import traceback
        traceback.print_exc()
        raise
        
    finally:
        cursor.close()
        conn.close()


def insert_optimized_components(schedule: List[Course], room_assignments,
                                termcode: str, season: int, previous_year_cache: Dict) -> int:
    """
    Insert optimized tutorials and labs.
    
    Args:
        schedule: List of optimized Course objects
        room_assignments: Room assignments (list or dict)
        termcode: New termcode
        season: Season code
        previous_year_cache: Cache of previous year's data
    
    Returns:
        Number of records inserted
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        count = 0
        tutorial_count = 0
        lab_count = 0
        
        print(f"\n  Processing {len(schedule)} courses for tutorials/labs...")
        
        for course in schedule:
            # Check if should exclude
            if should_exclude_course(course.subject, course.catalog_nbr):
                continue
            
            # Get room assignment
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
            
            # Get section from course
            section = course.class_nbr
            
            # Process tutorials
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
                    # Collect ALL day numbers for this tutorial
                    all_day_numbers = []
                    for day_enum in tut.day:
                        all_day_numbers.extend(extract_day_numbers(day_enum))
                    
                    # Combine into single day column set (prevents duplication)
                    day_cols = combine_day_columns(all_day_numbers)
                    
                    # Insert ONCE with combined day columns
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
            
            # Process labs
            if course.lab:
                prev_lab = get_previous_year_data(
                    course.subject, course.catalog_nbr, section, 'LAB', previous_year_cache
                )
                
                session = get_session_code(season, prev_lab['session'])
                career = 'GRAD' if course.catalog_nbr.startswith('6') else 'UGRD'
                instruction_mode = prev_lab['instructionmodecode']
                location = 'SGW' if instruction_mode == 'P' else 'ONL'
                buildingcode = 'H' if building else ''
                
                for lab_idx, lab in enumerate(course.lab):
                    # Collect ALL day numbers for this lab
                    all_day_numbers = []
                    for day_enum in lab.day:
                        all_day_numbers.extend(extract_day_numbers(day_enum))
                    
                    # Get lab-specific dates based on which week(s) it occurs
                    start_date, end_date = get_class_dates(season, 'LAB', session, all_day_numbers)
                    
                    # Combine into single day column set (prevents duplication)
                    day_cols = combine_day_columns(all_day_numbers)
                    
                    # Insert ONCE with combined day columns
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
                        0, 0, 16, 0,  # enrollmentcapacity = 16 for labs
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
        print(f"  ✓ Inserted {count} component records")
        print(f"    - Tutorials: {tutorial_count}")
        print(f"    - Labs: {lab_count}")
        return count
        
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Error inserting components: {e}")
        import traceback
        traceback.print_exc()
        raise
        
    finally:
        cursor.close()
        conn.close()


def export_to_scheduleterm_format(schedule: List[Course], room_assignments,
                                   year: int, season: int) -> bool:
    """
    Export complete timetable in scheduleterm format.
    
    Args:
        schedule: Optimized course schedule
        room_assignments: Room assignments
        year: Academic year (e.g., 2026)
        season: Season code (1, 2, 3, or 4)
    
    Returns:
        True if successful
    """
    print("\n" + "=" * 70)
    print("EXPORTING TO SCHEDULETERM FORMAT")
    print("=" * 70)
    
    try:
        # Build termcodes
        termcode = build_termcode(year, season)
        previous_year = year - 1
        previous_termcode = build_termcode(previous_year, season)
        
        print(f"\nNew termcode: {termcode}")
        print(f"Previous termcode: {previous_termcode}")
        
        # Build cache of previous year's data
        previous_year_cache = build_previous_year_cache(previous_termcode)
        
        # Create table
        if not create_scheduleterm_table():
            return False
        
        print("\nInserting lecture records...")
        lecture_count = insert_lecture_records(termcode, season, previous_termcode)
        
        print("\nInserting optimized tutorials and labs...")
        component_count = insert_optimized_components(
            schedule, room_assignments, termcode, season, previous_year_cache
        )
        
        print("\n" + "=" * 70)
        print("DATABASE EXPORT SUMMARY")
        print("=" * 70)
        print(f"Lectures: {lecture_count}")
        print(f"Tutorials + Labs: {component_count}")
        print(f"Total records: {lecture_count + component_count}")
        print(f"Table: optimized_schedule")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Failed to export: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Scheduleterm Export Module")
    print("=" * 70)
    
    # Test table creation
    success = create_scheduleterm_table()
    
    if success:
        print("\n✓ Table created successfully!")
    else:
        print("\n✗ Failed to create table")
