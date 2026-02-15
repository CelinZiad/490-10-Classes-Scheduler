# db_timetable_export.py
from typing import List, Dict
from .db import get_connection
from genetic_algo.course import Course


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
                mondays BOOLEAN DEFAULT false,
                tuesdays BOOLEAN DEFAULT false,
                wednesdays BOOLEAN DEFAULT false,
                thursdays BOOLEAN DEFAULT false,
                fridays BOOLEAN DEFAULT false,
                saturdays BOOLEAN DEFAULT false,
                sundays BOOLEAN DEFAULT false
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


def insert_schedule_records(schedule: List[Course], room_assignments,
                            termcode: str) -> int:
    """Insert all schedule records (tutorials and labs only - no lectures)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        count = 0
        
        for course in schedule:
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
            
            if course.tutorial:
                for tut_idx, tut in enumerate(course.tutorial):
                    for day_enum in tut.day:
                        day_numbers = extract_day_numbers(day_enum)
                        
                        for day_num in day_numbers:
                            day_cols = day_number_to_day_columns(day_num)
                            
                            cursor.execute("""
                                INSERT INTO optimized_schedule
                                (subject, catalog, section, componentcode, termcode, classnumber,
                                 buildingcode, room, classstarttime, classendtime,
                                 mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                course.subject, course.catalog_nbr, course.class_nbr,
                                'TUT', termcode, course.class_nbr,
                                '', '', minutes_to_time(tut.start), minutes_to_time(tut.end),
                                day_cols['mondays'], day_cols['tuesdays'], day_cols['wednesdays'],
                                day_cols['thursdays'], day_cols['fridays'], day_cols['saturdays'],
                                day_cols['sundays']
                            ))
                            count += 1
            
            if course.lab:
                for lab_idx, lab in enumerate(course.lab):
                    for day_enum in lab.day:
                        day_numbers = extract_day_numbers(day_enum)
                        
                        for day_num in day_numbers:
                            day_cols = day_number_to_day_columns(day_num)
                            
                            cursor.execute("""
                                INSERT INTO optimized_schedule
                                (subject, catalog, section, componentcode, termcode, classnumber,
                                 buildingcode, room, classstarttime, classendtime,
                                 mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                course.subject, course.catalog_nbr, course.class_nbr,
                                'LAB', termcode, course.class_nbr,
                                building, room, minutes_to_time(lab.start), minutes_to_time(lab.end),
                                day_cols['mondays'], day_cols['tuesdays'], day_cols['wednesdays'],
                                day_cols['thursdays'], day_cols['fridays'], day_cols['saturdays'],
                                day_cols['sundays']
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


def export_to_database(schedule: List[Course], room_assignments,
                      termcode: str) -> bool:
    """Export the optimized timetable to the database."""
    try:
        if not create_optimized_schedule_table():
            return False
        
        insert_schedule_records(schedule, room_assignments, termcode)
        return True
        
    except Exception:
        return False


if __name__ == "__main__":
    create_optimized_schedule_table()
