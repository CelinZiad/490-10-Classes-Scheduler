# db_timetable_export.py
"""
Export optimised schedule to the ``optimized_schedule`` database table.

This is a simpler alternative to ``scheduleterm_export.py`` that does not
carry forward lecture data from the previous year.  It writes tutorials
(1 row each) and labs (6 meeting‑pattern rows each) with accurate dates.
"""
from typing import List, Dict
from .db import get_connection
from genetic_algo.course import Course
from .time_utils import (minutes_to_time, day_number_to_day_columns,
                         combine_day_columns, extract_day_numbers)
from .academic_calendar import (
    SemesterDates,
    get_lec_tut_dates,
    compute_lab_meeting_dates,
    get_session_code,
    format_date,
)


def create_optimized_schedule_table():
    """Create a table in the database to store the optimized timetable."""
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
                buildingcode VARCHAR(10),
                room VARCHAR(20),
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
                meetingpatternnumber INTEGER DEFAULT 1
            )
        """)

        cursor.execute("CREATE INDEX idx_opt_subject_catalog ON optimized_schedule(subject, catalog)")
        cursor.execute("CREATE INDEX idx_opt_section ON optimized_schedule(section)")
        cursor.execute("CREATE INDEX idx_opt_component ON optimized_schedule(componentcode)")
        cursor.execute("CREATE INDEX idx_opt_room ON optimized_schedule(buildingcode, room)")

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        cursor.close()
        conn.close()


def insert_schedule_records(schedule: List[Course], room_assignments,
                            termcode: str, season: int = 2,
                            session: str = None,
                            cross_list_map: Dict = None) -> int:
    """Insert tutorials (1 row) and labs (6 rows each) into the DB."""
    conn = get_connection()
    cursor = conn.cursor()

    # Cross-listed courses: ELEC 390 rows are duplicated as COEN 390
    CROSS_LISTED = {
        ('ELEC', '390'): ('COEN', '390'),
    }
    cross_list_map = cross_list_map or {}

    if session is None:
        session = get_session_code(season)
    sem = SemesterDates(int('20' + termcode[1:3]), season, session)
    tut_start, tut_end = get_lec_tut_dates(sem)

    insert_sql = """
        INSERT INTO optimized_schedule
        (subject, catalog, section, componentcode, termcode, classnumber,
         buildingcode, room, classstarttime, classendtime,
         classstartdate, classenddate,
         mondays, tuesdays, wednesdays, thursdays, fridays,
         saturdays, sundays, meetingpatternnumber)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s)
    """

    try:
        count = 0

        for course in schedule:
            building = ''
            room = ''

            if isinstance(room_assignments, list):
                for assignment in room_assignments:
                    if (assignment.subject.strip().upper() == course.subject.upper()
                            and course.catalog_nbr in assignment.catalog_nbrs):
                        building = assignment.bldg
                        room = assignment.room
                        break
            elif isinstance(room_assignments, dict):
                key = (course.subject, course.catalog_nbr)
                building, room = room_assignments.get(key, ('', ''))

            source_key = (course.subject, course.catalog_nbr)

            # --- Tutorials -------------------------------------------------
            if course.tutorial:
                for tut in course.tutorial:
                    if tut is None or not tut.day:
                        continue
                    tut_section = tut.section or course.lec_section or course.class_nbr
                    all_days = []
                    for de in tut.day:
                        all_days.extend(extract_day_numbers(de))
                    day_cols = combine_day_columns(all_days)

                    params = (
                        course.subject, course.catalog_nbr, tut_section,
                        'TUT', termcode, course.class_nbr,
                        '', '', minutes_to_time(tut.start), minutes_to_time(tut.end),
                        format_date(tut_start), format_date(tut_end),
                        day_cols['mondays'], day_cols['tuesdays'], day_cols['wednesdays'],
                        day_cols['thursdays'], day_cols['fridays'], day_cols['saturdays'],
                        day_cols['sundays'], 1
                    )
                    cursor.execute(insert_sql, params)
                    count += 1

                    # Duplicate for cross-listed course
                    if source_key in CROSS_LISTED:
                        clone_subj, clone_cat = CROSS_LISTED[source_key]
                        clone_cn_key = (clone_subj, clone_cat, tut_section, 'TUT')
                        clone_cn_alt = (clone_subj, clone_cat, 'TUT')
                        clone_cn = cross_list_map.get(
                            clone_cn_key, cross_list_map.get(
                                clone_cn_alt, course.class_nbr))
                        clone_params = (
                            clone_subj, clone_cat, tut_section,
                            'TUT', termcode, clone_cn,
                            '', '', minutes_to_time(tut.start), minutes_to_time(tut.end),
                            format_date(tut_start), format_date(tut_end),
                            day_cols['mondays'], day_cols['tuesdays'], day_cols['wednesdays'],
                            day_cols['thursdays'], day_cols['fridays'], day_cols['saturdays'],
                            day_cols['sundays'], 1
                        )
                        cursor.execute(insert_sql, clone_params)
                        count += 1

            # --- Labs (6 meeting patterns) ---------------------------------
            if course.lab:
                for lab in course.lab:
                    if lab is None or not lab.day:
                        continue
                    lab_section = lab.section or course.lec_section or course.class_nbr
                    all_days = []
                    for de in lab.day:
                        all_days.extend(extract_day_numbers(de))
                    day_cols = combine_day_columns(all_days)

                    meeting_dates = compute_lab_meeting_dates(sem, all_days, 6)

                    for mpn, (mp_start, mp_end) in enumerate(meeting_dates, start=1):
                        params = (
                            course.subject, course.catalog_nbr, lab_section,
                            'LAB', termcode, course.class_nbr,
                            building, room,
                            minutes_to_time(lab.start), minutes_to_time(lab.end),
                            format_date(mp_start), format_date(mp_end),
                            day_cols['mondays'], day_cols['tuesdays'], day_cols['wednesdays'],
                            day_cols['thursdays'], day_cols['fridays'], day_cols['saturdays'],
                            day_cols['sundays'], mpn
                        )
                        cursor.execute(insert_sql, params)
                        count += 1

                        # Duplicate for cross-listed course
                        if source_key in CROSS_LISTED:
                            clone_subj, clone_cat = CROSS_LISTED[source_key]
                            clone_cn_key = (clone_subj, clone_cat, lab_section, 'LAB')
                            clone_cn_alt = (clone_subj, clone_cat, 'LAB')
                            clone_cn = cross_list_map.get(
                                clone_cn_key, cross_list_map.get(
                                    clone_cn_alt, course.class_nbr))
                            clone_params = (
                                clone_subj, clone_cat, lab_section,
                                'LAB', termcode, clone_cn,
                                building, room,
                                minutes_to_time(lab.start), minutes_to_time(lab.end),
                                format_date(mp_start), format_date(mp_end),
                                day_cols['mondays'], day_cols['tuesdays'], day_cols['wednesdays'],
                                day_cols['thursdays'], day_cols['fridays'], day_cols['saturdays'],
                                day_cols['sundays'], mpn
                            )
                            cursor.execute(insert_sql, clone_params)
                            count += 1

        conn.commit()
        return count

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


def export_to_database(schedule: List[Course], room_assignments,
                       termcode: str, season: int = 2,
                       session: str = None) -> bool:
    """Export the optimized timetable to the database."""
    try:
        if not create_optimized_schedule_table():
            return False

        insert_schedule_records(schedule, room_assignments, termcode,
                                season=season, session=session)
        return True

    except Exception:
        return False


if __name__ == "__main__":
    create_optimized_schedule_table()
