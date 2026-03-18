# scheduleterm_export.py

from typing import List, Dict, Tuple, Optional
from datetime import date
import csv
from .db import get_connection, fetch_all
from genetic_algo.course import Course
from .academic_calendar import (
    SemesterDates,
    get_lec_tut_dates,
    compute_lab_meeting_dates,
    get_session_code,
    format_date,
)


EXCLUDED_COURSES = {
    ('ELEC', '430'), ('ELEC', '434'), ('ELEC', '436'), ('ELEC', '438'),
    ('ELEC', '446'), ('ELEC', '443'), ('ELEC', '490'), ('ELEC', '498'),
    ('COEN', '390'), ('COEN', '490')
}


CROSS_LISTED = {
    # (source_subject, catalog): (clone_subject, catalog)
    ('ELEC', '390'): ('COEN', '390'),
}

# Courses that are copied verbatim from the previous year's scheduleterm

PASSTHROUGH_COURSES = {
    ('ELEC', '490'), ('COEN', '490'),
}



# Small helpers


def should_exclude_course(subject: str, catalog: str) -> bool:
    return (subject, catalog) in EXCLUDED_COURSES


def build_termcode(year: int, season: int) -> str:
    year_suffix = str(year)[-2:]
    return f"2{year_suffix}{season}"


def _build_cross_list_classnumber_map(previous_termcode: str) -> Dict:
    """Build a map from (subject, catalog, section, componentcode) -> classnumber
    for the clone side of every CROSS_LISTED pair.

    This lets us stamp COEN 390 rows with the correct classnumber values from
    the scheduleterm table.
    """
    clone_subjects = set()
    for (_, _), (clone_subj, clone_cat) in CROSS_LISTED.items():
        clone_subjects.add((clone_subj, clone_cat))

    if not clone_subjects:
        return {}

    sql = """
        SELECT subject, catalog, section, componentcode, classnumber
        FROM scheduleterm
        WHERE termcode = %s
          AND departmentcode = 'ELECCOEN'
          AND meetingpatternnumber = 1
    """
    records = fetch_all(sql, (previous_termcode,))

    mapping: Dict = {}
    for r in records:
        key = (r['subject'], r['catalog'])
        if key in clone_subjects:
            full_key = (r['subject'], r['catalog'], r['section'], r['componentcode'])
            mapping[full_key] = r['classnumber']
            alt_key = (r['subject'], r['catalog'], r['componentcode'])
            if alt_key not in mapping:
                mapping[alt_key] = r['classnumber']
    return mapping


def minutes_to_time(minutes: int) -> str:
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}:00"


def day_number_to_day_columns(day_num: int) -> Dict[str, bool]:
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
    result = {
        'mondays': False, 'tuesdays': False, 'wednesdays': False,
        'thursdays': False, 'fridays': False, 'saturdays': False, 'sundays': False
    }
    for day_num in day_numbers:
        dc = day_number_to_day_columns(day_num)
        for day, value in dc.items():
            if value:
                result[day] = True
    return result


def extract_day_numbers(day_enum) -> List[int]:
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



# SemesterDates cache — avoids rebuilding for every course


_semester_cache: Dict[Tuple[int, int, str], SemesterDates] = {}


def _get_semester_dates(year: int, season: int, session: str) -> SemesterDates:
    """Return a cached SemesterDates for the given (year, season, session)."""
    key = (year, season, session)
    if key not in _semester_cache:
        _semester_cache[key] = SemesterDates(year, season, session)
    return _semester_cache[key]


def _resolve_course_session(season: int, prev_session: str) -> str:
    """Determine the session code for a course.

    For summer (season 1) the previous year's session is carried forward
    (13W, 6H1, or 6H2).  For other seasons the session is deterministic.
    """
    if season == 1:
        if prev_session in ('13W', '6H1', '6H2'):
            return prev_session
        return '13W'  # default summer
    return get_session_code(season)



# Previous-year cache 


def get_previous_year_data(subject, catalog, section, componentcode, cache):
    key = (subject, catalog, section, componentcode)
    if key in cache:
        return cache[key]
    alt = (subject, catalog, componentcode)
    if alt in cache:
        return cache[alt]
    return {
        'classnumber': None,
        'session': '13W',
        'instructionmodecode': 'P',
        'locationcode': 'SGW',
        'career': 'UGRD'
    }


def build_previous_year_cache(previous_termcode: str) -> Dict:
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
    for r in records:
        # Full section key: (ELEC, 275, CDDE, TUT)
        key = (r['subject'], r['catalog'], r['section'], r['componentcode'])
        val = {
            'classnumber': r['classnumber'],
            'session': r.get('session', '13W'),
            'instructionmodecode': r.get('instructionmodecode', 'P'),
            'locationcode': r.get('locationcode', 'SGW'),
            'career': r.get('career', 'UGRD')
        }
        cache[key] = val

        
        # The GA uses the first character of the section as class_nbr.
        
        base_sec = r['section'][0] if r['section'] else r['section']
        base_key = (r['subject'], r['catalog'], base_sec, r['componentcode'])
        if base_key not in cache:
            cache[base_key] = val

        # Subject+catalog+component fallback: (ELEC, 275, TUT)
        alt = (r['subject'], r['catalog'], r['componentcode'])
        if alt not in cache:
            cache[alt] = val
    return cache



# DB table creation


def create_scheduleterm_table():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DROP TABLE IF EXISTS optimized_schedule CASCADE")
        cur.execute("""
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
        cur.execute("CREATE INDEX idx_opt_subject_catalog ON optimized_schedule(subject, catalog)")
        cur.execute("CREATE INDEX idx_opt_section ON optimized_schedule(section)")
        cur.execute("CREATE INDEX idx_opt_component ON optimized_schedule(componentcode)")
        cur.execute("CREATE INDEX idx_opt_termcode ON optimized_schedule(termcode)")
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()



# Insert lectures 


def insert_lecture_records(termcode: str, year: int, season: int,
                           previous_termcode: str,
                           cross_list_map: Dict = None) -> int:
    conn = get_connection()
    cur = conn.cursor()
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
              AND classstartdate != '0001-01-01'
        """
        lectures = fetch_all(sql, (previous_termcode,))
        count = 0
        cross_list_map = cross_list_map or {}

        insert_sql = """
            INSERT INTO optimized_schedule
            (subject, catalog, section, componentcode, termcode, classnumber,
             session, buildingcode, room, instructionmodecode, locationcode,
             currentwaitlisttotal, waitlistcapacity, enrollmentcapacity, currentenrollment,
             departmentcode, facultycode, classstarttime, classendtime,
             classstartdate, classenddate,
             mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays,
             facultydescription, career, meetingpatternnumber)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        for lec in lectures:
            if should_exclude_course(lec['subject'], lec['catalog']):
                continue

            # Per-course session resolution (matters for summer)
            lec_session = lec.get('session', '13W') or '13W'
            session_code = _resolve_course_session(season, lec_session)
            sem = _get_semester_dates(year, season, session_code)
            start_d, end_d = get_lec_tut_dates(sem)

            params = (
                lec['subject'], lec['catalog'], lec['section'], 'LEC', termcode,
                lec['classnumber'], session_code, lec['buildingcode'], lec['room'],
                lec['instructionmodecode'], lec['locationcode'],
                lec['currentwaitlisttotal'], lec['waitlistcapacity'],
                lec['enrollmentcapacity'], lec['currentenrollment'],
                lec['departmentcode'], lec['facultycode'],
                lec['classstarttime'], lec['classendtime'],
                format_date(start_d), format_date(end_d),
                lec['mondays'], lec['tuesdays'], lec['wednesdays'],
                lec['thursdays'], lec['fridays'], lec['saturdays'], lec['sundays'],
                lec['facultydescription'], lec['career'], 1
            )
            cur.execute(insert_sql, params)
            count += 1

            # Duplicate for cross-listed courses (e.g. ELEC 390 -> COEN 390)
            source_key = (lec['subject'], lec['catalog'])
            if source_key in CROSS_LISTED:
                clone_subj, clone_cat = CROSS_LISTED[source_key]
                clone_cn_key = (clone_subj, clone_cat, lec['section'], 'LEC')
                clone_cn_alt = (clone_subj, clone_cat, 'LEC')
                clone_classnumber = cross_list_map.get(
                    clone_cn_key, cross_list_map.get(clone_cn_alt, lec['classnumber']))

                clone_params = (
                    clone_subj, clone_cat, lec['section'], 'LEC', termcode,
                    clone_classnumber, session_code, lec['buildingcode'], lec['room'],
                    lec['instructionmodecode'], lec['locationcode'],
                    lec['currentwaitlisttotal'], lec['waitlistcapacity'],
                    lec['enrollmentcapacity'], lec['currentenrollment'],
                    lec['departmentcode'], lec['facultycode'],
                    lec['classstarttime'], lec['classendtime'],
                    format_date(start_d), format_date(end_d),
                    lec['mondays'], lec['tuesdays'], lec['wednesdays'],
                    lec['thursdays'], lec['fridays'], lec['saturdays'], lec['sundays'],
                    lec['facultydescription'], lec['career'], 1
                )
                cur.execute(insert_sql, clone_params)
                count += 1

        conn.commit()
        return count
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()



# Insert optimised tutorials + labs 


def insert_optimized_components(schedule: List[Course], room_assignments,
                                 termcode: str, year: int, season: int,
                                 previous_year_cache: Dict,
                                 cross_list_map: Dict = None) -> int:
    """Insert tutorials (1 row each) and labs (6 rows each) into the DB."""
    conn = get_connection()
    cur = conn.cursor()
    cross_list_map = cross_list_map or {}

    insert_sql = """
        INSERT INTO optimized_schedule
        (subject, catalog, section, componentcode, termcode, classnumber,
         session, buildingcode, room, instructionmodecode, locationcode,
         currentwaitlisttotal, waitlistcapacity, enrollmentcapacity, currentenrollment,
         departmentcode, facultycode, classstarttime, classendtime,
         classstartdate, classenddate,
         mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays,
         facultydescription, career, meetingpatternnumber)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    try:
        count = 0

        for course in schedule:
            if should_exclude_course(course.subject, course.catalog_nbr):
                continue

            # Resolve room assignment
            building, room = '', ''
            if isinstance(room_assignments, list):
                for a in room_assignments:
                    if (a.subject.strip().upper() == course.subject.upper()
                            and course.catalog_nbr in a.catalog_nbrs):
                        building, room = a.bldg, a.room
                        break
            elif isinstance(room_assignments, dict):
                building, room = room_assignments.get(
                    (course.subject, course.catalog_nbr), ('', ''))

            section = course.class_nbr
            source_key = (course.subject, course.catalog_nbr)

            # --- Tutorials ---
            if course.tutorial:
                prev_tut = get_previous_year_data(
                    course.subject, course.catalog_nbr, section, 'TUT',
                    previous_year_cache)
                session = _resolve_course_session(season, prev_tut['session'])
                sem = _get_semester_dates(year, season, session)
                start_d, end_d = get_lec_tut_dates(sem)
                career = 'GRAD' if course.catalog_nbr.startswith('6') else 'UGRD'
                instr_mode = prev_tut['instructionmodecode']
                location = 'SGW' if instr_mode == 'P' else 'ONL'

                for tut in course.tutorial:
                    if tut is None or not tut.day:
                        continue
                    all_days = []
                    for de in tut.day:
                        all_days.extend(extract_day_numbers(de))
                    day_cols = combine_day_columns(all_days)

                    params = (
                        course.subject, course.catalog_nbr, section, 'TUT', termcode,
                        prev_tut['classnumber'], session, '', '', instr_mode, location,
                        0, 0, 0, 0, 'ELECCOEN', 'ENCS',
                        minutes_to_time(tut.start), minutes_to_time(tut.end),
                        format_date(start_d), format_date(end_d),
                        day_cols['mondays'], day_cols['tuesdays'], day_cols['wednesdays'],
                        day_cols['thursdays'], day_cols['fridays'], day_cols['saturdays'],
                        day_cols['sundays'],
                        'Gina Cody School of Engineering & Computer Science', career, 1
                    )
                    cur.execute(insert_sql, params)
                    count += 1

                    # Duplicate for cross-listed course
                    if source_key in CROSS_LISTED:
                        clone_subj, clone_cat = CROSS_LISTED[source_key]
                        clone_cn_key = (clone_subj, clone_cat, section, 'TUT')
                        clone_cn_alt = (clone_subj, clone_cat, 'TUT')
                        clone_cn = cross_list_map.get(
                            clone_cn_key, cross_list_map.get(
                                clone_cn_alt, prev_tut['classnumber']))
                        clone_params = (
                            clone_subj, clone_cat, section, 'TUT', termcode,
                            clone_cn, session, '', '', instr_mode, location,
                            0, 0, 0, 0, 'ELECCOEN', 'ENCS',
                            minutes_to_time(tut.start), minutes_to_time(tut.end),
                            format_date(start_d), format_date(end_d),
                            day_cols['mondays'], day_cols['tuesdays'], day_cols['wednesdays'],
                            day_cols['thursdays'], day_cols['fridays'], day_cols['saturdays'],
                            day_cols['sundays'],
                            'Gina Cody School of Engineering & Computer Science', career, 1
                        )
                        cur.execute(insert_sql, clone_params)
                        count += 1

            # --- Labs ---
            if course.lab:
                prev_lab = get_previous_year_data(
                    course.subject, course.catalog_nbr, section, 'LAB',
                    previous_year_cache)
                session = _resolve_course_session(season, prev_lab['session'])
                sem = _get_semester_dates(year, season, session)
                career = 'GRAD' if course.catalog_nbr.startswith('6') else 'UGRD'
                instr_mode = prev_lab['instructionmodecode']
                location = 'SGW' if instr_mode == 'P' else 'ONL'
                bldg_code = building if building else ''

                for lab in course.lab:
                    if lab is None or not lab.day:
                        continue

                    all_days = []
                    for de in lab.day:
                        all_days.extend(extract_day_numbers(de))

                    day_cols = combine_day_columns(all_days)

                    # Compute the 6 meeting dates using the course's own session
                    meeting_dates = compute_lab_meeting_dates(sem, all_days, 6)

                    for mpn, (mp_start, mp_end) in enumerate(meeting_dates, start=1):
                        params = (
                            course.subject, course.catalog_nbr, section, 'LAB', termcode,
                            prev_lab['classnumber'], session, bldg_code, room,
                            instr_mode, location,
                            0, 0, 16, 0, 'ELECCOEN', 'ENCS',
                            minutes_to_time(lab.start), minutes_to_time(lab.end),
                            format_date(mp_start), format_date(mp_end),
                            day_cols['mondays'], day_cols['tuesdays'], day_cols['wednesdays'],
                            day_cols['thursdays'], day_cols['fridays'], day_cols['saturdays'],
                            day_cols['sundays'],
                            'Gina Cody School of Engineering & Computer Science', career, mpn
                        )
                        cur.execute(insert_sql, params)
                        count += 1

                        # Duplicate for cross-listed course
                        if source_key in CROSS_LISTED:
                            clone_subj, clone_cat = CROSS_LISTED[source_key]
                            clone_cn_key = (clone_subj, clone_cat, section, 'LAB')
                            clone_cn_alt = (clone_subj, clone_cat, 'LAB')
                            clone_cn = cross_list_map.get(
                                clone_cn_key, cross_list_map.get(
                                    clone_cn_alt, prev_lab['classnumber']))
                            clone_params = (
                                clone_subj, clone_cat, section, 'LAB', termcode,
                                clone_cn, session, bldg_code, room,
                                instr_mode, location,
                                0, 0, 16, 0, 'ELECCOEN', 'ENCS',
                                minutes_to_time(lab.start), minutes_to_time(lab.end),
                                format_date(mp_start), format_date(mp_end),
                                day_cols['mondays'], day_cols['tuesdays'], day_cols['wednesdays'],
                                day_cols['thursdays'], day_cols['fridays'], day_cols['saturdays'],
                                day_cols['sundays'],
                                'Gina Cody School of Engineering & Computer Science', career, mpn
                            )
                            cur.execute(insert_sql, clone_params)
                            count += 1

        conn.commit()
        return count
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()



# CSV export 


def _build_csv_rows_for_schedule(schedule: List[Course], room_assignments,
                                  termcode: str, year: int, season: int,
                                  previous_year_cache: Dict,
                                  previous_termcode: str,
                                  cross_list_map: Dict = None) -> List[Dict]:
    """Build all CSV rows (lectures from prev year + optimised tuts/labs)."""
    rows: List[Dict] = []
    cross_list_map = cross_list_map or {}

    # --- Lectures from previous year ---------------------------------------
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
          AND classstartdate != '0001-01-01'
    """
    lectures = fetch_all(sql, (previous_termcode,))

    for lec in lectures:
        if should_exclude_course(lec['subject'], lec['catalog']):
            continue

        lec_session = lec.get('session', '13W') or '13W'
        session_code = _resolve_course_session(season, lec_session)
        sem = _get_semester_dates(year, season, session_code)
        start_d, end_d = get_lec_tut_dates(sem)

        row = {
            'subject': lec['subject'],
            'catalog': lec['catalog'],
            'section': lec['section'],
            'componentcode': 'LEC',
            'termcode': termcode,
            'classnumber': lec['classnumber'],
            'session': session_code,
            'buildingcode': lec['buildingcode'] or '',
            'room': lec['room'] or '',
            'instructionmodecode': lec['instructionmodecode'] or 'P',
            'locationcode': lec['locationcode'] or 'SGW',
            'currentwaitlisttotal': lec['currentwaitlisttotal'] or 0,
            'waitlistcapacity': lec['waitlistcapacity'] or 0,
            'enrollmentcapacity': lec['enrollmentcapacity'] or 0,
            'currentenrollment': lec['currentenrollment'] or 0,
            'departmentcode': lec['departmentcode'] or 'ELECCOEN',
            'facultycode': lec['facultycode'] or 'ENCS',
            'classstarttime': str(lec['classstarttime']) if lec['classstarttime'] else '00:00:00',
            'classendtime': str(lec['classendtime']) if lec['classendtime'] else '00:00:00',
            'classstartdate': format_date(start_d) or '',
            'classenddate': format_date(end_d) or '',
            'mondays': lec['mondays'],
            'tuesdays': lec['tuesdays'],
            'wednesdays': lec['wednesdays'],
            'thursdays': lec['thursdays'],
            'fridays': lec['fridays'],
            'saturdays': lec['saturdays'],
            'sundays': lec['sundays'],
            'facultydescription': lec['facultydescription'] or '',
            'career': lec['career'] or 'UGRD',
            'meetingpatternnumber': 1,
        }
        rows.append(row)

        # Duplicate for cross-listed courses
        source_key = (lec['subject'], lec['catalog'])
        if source_key in CROSS_LISTED:
            clone_subj, clone_cat = CROSS_LISTED[source_key]
            clone_cn_key = (clone_subj, clone_cat, lec['section'], 'LEC')
            clone_cn_alt = (clone_subj, clone_cat, 'LEC')
            clone_cn = cross_list_map.get(
                clone_cn_key, cross_list_map.get(clone_cn_alt, lec['classnumber']))
            clone_row = dict(row)
            clone_row['subject'] = clone_subj
            clone_row['catalog'] = clone_cat
            clone_row['classnumber'] = clone_cn
            rows.append(clone_row)

    # --- Optimised tutorials and labs ---
    for course in schedule:
        if should_exclude_course(course.subject, course.catalog_nbr):
            continue

        building, room = '', ''
        if isinstance(room_assignments, list):
            for a in room_assignments:
                if (a.subject.strip().upper() == course.subject.upper()
                        and course.catalog_nbr in a.catalog_nbrs):
                    building, room = a.bldg, a.room
                    break
        elif isinstance(room_assignments, dict):
            building, room = room_assignments.get(
                (course.subject, course.catalog_nbr), ('', ''))

        section = course.class_nbr
        source_key = (course.subject, course.catalog_nbr)

        # Tutorials
        if course.tutorial:
            prev_tut = get_previous_year_data(
                course.subject, course.catalog_nbr, section, 'TUT',
                previous_year_cache)
            session = _resolve_course_session(season, prev_tut['session'])
            sem = _get_semester_dates(year, season, session)
            tut_start, tut_end = get_lec_tut_dates(sem)
            career = 'GRAD' if course.catalog_nbr.startswith('6') else 'UGRD'
            instr_mode = prev_tut['instructionmodecode']
            location = 'SGW' if instr_mode == 'P' else 'ONL'

            for tut in course.tutorial:
                if tut is None or not tut.day:
                    continue
                all_days = []
                for de in tut.day:
                    all_days.extend(extract_day_numbers(de))
                day_cols = combine_day_columns(all_days)

                row = {
                    'subject': course.subject,
                    'catalog': course.catalog_nbr,
                    'section': section,
                    'componentcode': 'TUT',
                    'termcode': termcode,
                    'classnumber': prev_tut['classnumber'] or '',
                    'session': session,
                    'buildingcode': '',
                    'room': '',
                    'instructionmodecode': instr_mode,
                    'locationcode': location,
                    'currentwaitlisttotal': 0,
                    'waitlistcapacity': 0,
                    'enrollmentcapacity': 0,
                    'currentenrollment': 0,
                    'departmentcode': 'ELECCOEN',
                    'facultycode': 'ENCS',
                    'classstarttime': minutes_to_time(tut.start),
                    'classendtime': minutes_to_time(tut.end),
                    'classstartdate': format_date(tut_start) or '',
                    'classenddate': format_date(tut_end) or '',
                    **day_cols,
                    'facultydescription': 'Gina Cody School of Engineering & Computer Science',
                    'career': career,
                    'meetingpatternnumber': 1,
                }
                rows.append(row)

                # Duplicate for cross-listed course
                if source_key in CROSS_LISTED:
                    clone_subj, clone_cat = CROSS_LISTED[source_key]
                    clone_cn_key = (clone_subj, clone_cat, section, 'TUT')
                    clone_cn_alt = (clone_subj, clone_cat, 'TUT')
                    clone_cn = cross_list_map.get(
                        clone_cn_key, cross_list_map.get(
                            clone_cn_alt, prev_tut['classnumber'] or ''))
                    clone_row = dict(row)
                    clone_row['subject'] = clone_subj
                    clone_row['catalog'] = clone_cat
                    clone_row['classnumber'] = clone_cn
                    rows.append(clone_row)

        # Labs — 6 rows per lab section
        if course.lab:
            prev_lab = get_previous_year_data(
                course.subject, course.catalog_nbr, section, 'LAB',
                previous_year_cache)
            session = _resolve_course_session(season, prev_lab['session'])
            sem = _get_semester_dates(year, season, session)
            career = 'GRAD' if course.catalog_nbr.startswith('6') else 'UGRD'
            instr_mode = prev_lab['instructionmodecode']
            location = 'SGW' if instr_mode == 'P' else 'ONL'
            bldg_code = building if building else ''

            for lab in course.lab:
                if lab is None or not lab.day:
                    continue
                all_days = []
                for de in lab.day:
                    all_days.extend(extract_day_numbers(de))
                day_cols = combine_day_columns(all_days)

                meeting_dates = compute_lab_meeting_dates(sem, all_days, 6)

                for mpn, (mp_start, mp_end) in enumerate(meeting_dates, start=1):
                    row = {
                        'subject': course.subject,
                        'catalog': course.catalog_nbr,
                        'section': section,
                        'componentcode': 'LAB',
                        'termcode': termcode,
                        'classnumber': prev_lab['classnumber'] or '',
                        'session': session,
                        'buildingcode': bldg_code,
                        'room': room,
                        'instructionmodecode': instr_mode,
                        'locationcode': location,
                        'currentwaitlisttotal': 0,
                        'waitlistcapacity': 0,
                        'enrollmentcapacity': 16,
                        'currentenrollment': 0,
                        'departmentcode': 'ELECCOEN',
                        'facultycode': 'ENCS',
                        'classstarttime': minutes_to_time(lab.start),
                        'classendtime': minutes_to_time(lab.end),
                        'classstartdate': format_date(mp_start) or '',
                        'classenddate': format_date(mp_end) or '',
                        **day_cols,
                        'facultydescription': 'Gina Cody School of Engineering & Computer Science',
                        'career': career,
                        'meetingpatternnumber': mpn,
                    }
                    rows.append(row)

                    # Duplicate for cross-listed course
                    if source_key in CROSS_LISTED:
                        clone_subj, clone_cat = CROSS_LISTED[source_key]
                        clone_cn_key = (clone_subj, clone_cat, section, 'LAB')
                        clone_cn_alt = (clone_subj, clone_cat, 'LAB')
                        clone_cn = cross_list_map.get(
                            clone_cn_key, cross_list_map.get(
                                clone_cn_alt, prev_lab['classnumber'] or ''))
                        clone_row = dict(row)
                        clone_row['subject'] = clone_subj
                        clone_row['catalog'] = clone_cat
                        clone_row['classnumber'] = clone_cn
                        rows.append(clone_row)

    return rows


def _csv_fieldnames() -> List[str]:
    return [
        'subject', 'catalog', 'section', 'componentcode', 'termcode',
        'classnumber', 'session', 'buildingcode', 'room',
        'instructionmodecode', 'locationcode',
        'currentwaitlisttotal', 'waitlistcapacity',
        'enrollmentcapacity', 'currentenrollment',
        'departmentcode', 'facultycode',
        'classstarttime', 'classendtime',
        'classstartdate', 'classenddate',
        'mondays', 'tuesdays', 'wednesdays', 'thursdays',
        'fridays', 'saturdays', 'sundays',
        'facultydescription', 'career', 'meetingpatternnumber',
    ]


def export_csv(rows: List[Dict], output_path: str):
    """Write rows to CSV."""
    if not rows:
        return
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=_csv_fieldnames())
        writer.writeheader()
        writer.writerows(rows)



# Pass-through courses 


def _build_passthrough_filter() -> str:
    """Build a SQL OR clause for PASSTHROUGH_COURSES."""
    clauses = []
    for subj, cat in PASSTHROUGH_COURSES:
        clauses.append(f"(subject = '{subj}' AND catalog = '{cat}')")
    return ' OR '.join(clauses)


def insert_passthrough_records(termcode: str, year: int, season: int,
                                previous_termcode: str) -> int:

    if season not in (2, 4):
        return 0

    filter_clause = _build_passthrough_filter()
    if not filter_clause:
        return 0

    # Also look in the Fall+Winter termcode (season 3) for 8-month courses
    previous_year = year - 1
    fw_termcode = build_termcode(previous_year, 3)

    sql = f"""
        SELECT subject, catalog, section, componentcode, classnumber,
               session, buildingcode, room, instructionmodecode, locationcode,
               currentwaitlisttotal, waitlistcapacity, enrollmentcapacity, currentenrollment,
               departmentcode, facultycode, classstarttime, classendtime,
               mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays,
               facultydescription, career, meetingpatternnumber
        FROM scheduleterm
        WHERE termcode IN (%s, %s)
          AND departmentcode = 'ELECCOEN'
          AND classstartdate != '0001-01-01'
          AND ({filter_clause})
        ORDER BY subject, catalog, classnumber, componentcode, meetingpatternnumber
    """
    records = fetch_all(sql, (previous_termcode, fw_termcode))
    if not records:
        return 0

    conn = get_connection()
    cur = conn.cursor()

    # Pass-through courses are Fall+Winter (8-month): session 26W,
    # classstartdate from fall semester, classenddate from winter semester.
    session_code = '26W'
    fall_sem = _get_semester_dates(year, 2, '13W')
    winter_sem = _get_semester_dates(year + 1, 4, '13W')
    fall_start, _ = get_lec_tut_dates(fall_sem)
    _, winter_end = get_lec_tut_dates(winter_sem)

    try:
        count = 0
        for r in records:
            if r['componentcode'] == 'LAB' and r['meetingpatternnumber'] > 1:
                start_d = r.get('classstartdate')
                end_d = r.get('classenddate')
            else:
                start_d = fall_start
                end_d = winter_end

            cur.execute("""
                INSERT INTO optimized_schedule
                (subject, catalog, section, componentcode, termcode, classnumber,
                 session, buildingcode, room, instructionmodecode, locationcode,
                 currentwaitlisttotal, waitlistcapacity, enrollmentcapacity, currentenrollment,
                 departmentcode, facultycode, classstarttime, classendtime,
                 classstartdate, classenddate,
                 mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays,
                 facultydescription, career, meetingpatternnumber)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                r['subject'], r['catalog'], r['section'], r['componentcode'],
                termcode, r['classnumber'], session_code,
                r['buildingcode'] or '', r['room'] or '',
                r['instructionmodecode'] or 'P', r['locationcode'] or 'SGW',
                r['currentwaitlisttotal'] or 0, r['waitlistcapacity'] or 0,
                r['enrollmentcapacity'] or 0, r['currentenrollment'] or 0,
                r['departmentcode'] or 'ELECCOEN', r['facultycode'] or 'ENCS',
                r['classstarttime'], r['classendtime'],
                format_date(start_d) if isinstance(start_d, date) else (start_d or ''),
                format_date(end_d) if isinstance(end_d, date) else (end_d or ''),
                r['mondays'], r['tuesdays'], r['wednesdays'],
                r['thursdays'], r['fridays'], r['saturdays'], r['sundays'],
                r['facultydescription'] or '', r['career'] or 'UGRD',
                r['meetingpatternnumber']
            ))
            count += 1

        conn.commit()
        return count
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def _build_passthrough_csv_rows(termcode: str, year: int, season: int,
                                 previous_termcode: str) -> List[Dict]:
    """Build CSV rows for pass-through courses.

    Only called for fall (season 2) and winter (season 4).
    Also queries the Fall+Winter termcode (season 3) for 8-month courses.
    """
    if season not in (2, 4):
        return []

    filter_clause = _build_passthrough_filter()
    if not filter_clause:
        return []

    previous_year = year - 1
    fw_termcode = build_termcode(previous_year, 3)

    sql = f"""
        SELECT subject, catalog, section, componentcode, classnumber,
               session, buildingcode, room, instructionmodecode, locationcode,
               currentwaitlisttotal, waitlistcapacity, enrollmentcapacity, currentenrollment,
               departmentcode, facultycode, classstarttime, classendtime,
               classstartdate, classenddate,
               mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays,
               facultydescription, career, meetingpatternnumber
        FROM scheduleterm
        WHERE termcode IN (%s, %s)
          AND departmentcode = 'ELECCOEN'
          AND classstartdate != '0001-01-01'
          AND ({filter_clause})
        ORDER BY subject, catalog, classnumber, componentcode, meetingpatternnumber
    """
    records = fetch_all(sql, (previous_termcode, fw_termcode))

    # Pass-through courses are Fall+Winter (8-month): session 26W,
    # classstartdate from fall semester, classenddate from winter semester.
    session_code = '26W'
    fall_sem = _get_semester_dates(year, 2, '13W')
    winter_sem = _get_semester_dates(year + 1, 4, '13W')
    fall_start, _ = get_lec_tut_dates(fall_sem)
    _, winter_end = get_lec_tut_dates(winter_sem)

    rows: List[Dict] = []
    for r in records:
        if r['componentcode'] == 'LAB' and r['meetingpatternnumber'] > 1:
            start_d = r.get('classstartdate')
            end_d = r.get('classenddate')
            start_str = format_date(start_d) if isinstance(start_d, date) else (str(start_d) if start_d else '')
            end_str = format_date(end_d) if isinstance(end_d, date) else (str(end_d) if end_d else '')
        else:
            start_str = format_date(fall_start) or ''
            end_str = format_date(winter_end) or ''

        rows.append({
            'subject': r['subject'],
            'catalog': r['catalog'],
            'section': r['section'],
            'componentcode': r['componentcode'],
            'termcode': termcode,
            'classnumber': r['classnumber'],
            'session': session_code,
            'buildingcode': r['buildingcode'] or '',
            'room': r['room'] or '',
            'instructionmodecode': r['instructionmodecode'] or 'P',
            'locationcode': r['locationcode'] or 'SGW',
            'currentwaitlisttotal': r['currentwaitlisttotal'] or 0,
            'waitlistcapacity': r['waitlistcapacity'] or 0,
            'enrollmentcapacity': r['enrollmentcapacity'] or 0,
            'currentenrollment': r['currentenrollment'] or 0,
            'departmentcode': r['departmentcode'] or 'ELECCOEN',
            'facultycode': r['facultycode'] or 'ENCS',
            'classstarttime': str(r['classstarttime']) if r['classstarttime'] else '00:00:00',
            'classendtime': str(r['classendtime']) if r['classendtime'] else '00:00:00',
            'classstartdate': start_str,
            'classenddate': end_str,
            'mondays': r['mondays'],
            'tuesdays': r['tuesdays'],
            'wednesdays': r['wednesdays'],
            'thursdays': r['thursdays'],
            'fridays': r['fridays'],
            'saturdays': r['saturdays'],
            'sundays': r['sundays'],
            'facultydescription': r['facultydescription'] or '',
            'career': r['career'] or 'UGRD',
            'meetingpatternnumber': r['meetingpatternnumber'],
        })

    return rows



# Public entry point


def export_to_scheduleterm_format(schedule: List[Course], room_assignments,
                                   year: int, season: int,
                                   csv_output_path: str = None) -> bool:

    try:
        termcode = build_termcode(year, season)
        previous_year = year - 1
        previous_termcode = build_termcode(previous_year, season)

        previous_year_cache = build_previous_year_cache(previous_termcode)
        cross_list_map = _build_cross_list_classnumber_map(previous_termcode)

        if not create_scheduleterm_table():
            return False

        insert_lecture_records(termcode, year, season, previous_termcode,
                              cross_list_map)
        insert_optimized_components(
            schedule, room_assignments, termcode, year, season,
            previous_year_cache, cross_list_map)

        # Pass-through courses (fall/winter only)
        insert_passthrough_records(termcode, year, season, previous_termcode)

        # CSV export
        if csv_output_path:
            csv_rows = _build_csv_rows_for_schedule(
                schedule, room_assignments, termcode, year, season,
                previous_year_cache, previous_termcode, cross_list_map)
            # Append pass-through rows
            csv_rows.extend(
                _build_passthrough_csv_rows(termcode, year, season,
                                            previous_termcode))
            export_csv(csv_rows, csv_output_path)

        return True

    except Exception:
        return False


if __name__ == "__main__":
    create_scheduleterm_table()
