# db_timetable_export.py
"""
Module to create database table and insert optimized timetable results.
Table structure matches the scheduleterm table format.
"""

from typing import List, Dict
from db import get_connection
from course import Course


def create_optimized_schedule_table():
    """
    Create a table in the database to store the optimized timetable.
    Table structure matches scheduleterm table columns.
    
    Table created:
    - optimized_schedule: Complete timetable in scheduleterm format
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        print("\n" + "=" * 70)
        print("CREATING OPTIMIZED_SCHEDULE TABLE")
        print("=" * 70)
        
        # Drop existing table if it exists
        print("\nDropping existing table (if any)...")
        cursor.execute("DROP TABLE IF EXISTS optimized_schedule CASCADE")
        print("  Done")
        
        # Create optimized_schedule table
        print("\nCreating optimized_schedule table...")
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
        print("  ✓ optimized_schedule table created")
        
        # Create indexes for better query performance
        print("\nCreating indexes...")
        cursor.execute("CREATE INDEX idx_opt_subject_catalog ON optimized_schedule(subject, catalog)")
        cursor.execute("CREATE INDEX idx_opt_section ON optimized_schedule(section)")
        cursor.execute("CREATE INDEX idx_opt_component ON optimized_schedule(componentcode)")
        cursor.execute("CREATE INDEX idx_opt_room ON optimized_schedule(buildingcode, room)")
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


def day_number_to_day_columns(day_num: int) -> Dict[str, bool]:
    """
    Convert day number to boolean day columns.
    
    Args:
        day_num: Day number (1-5 for Week 1, 8-12 for Week 2)
    
    Returns:
        Dictionary with day column values
    """
    # Map day numbers to weekday names
    day_map = {
        1: 'mondays',    # Week 1 Monday
        2: 'tuesdays',   # Week 1 Tuesday
        3: 'wednesdays', # Week 1 Wednesday
        4: 'thursdays',  # Week 1 Thursday
        5: 'fridays',    # Week 1 Friday
        8: 'mondays',    # Week 2 Monday
        9: 'tuesdays',   # Week 2 Tuesday
        10: 'wednesdays',# Week 2 Wednesday
        11: 'thursdays', # Week 2 Thursday
        12: 'fridays'    # Week 2 Friday
    }
    
    result = {
        'mondays': False,
        'tuesdays': False,
        'wednesdays': False,
        'thursdays': False,
        'fridays': False,
        'saturdays': False,
        'sundays': False
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
    
    # Handle Day enum
    day_str = str(day_enum)
    
    if 'Week1' in day_str or 'Week2' in day_str:
        # Single day enum
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
    """
    Insert all schedule records (tutorials and labs only - no lectures).
    
    Args:
        schedule: List of Course objects
        room_assignments: List of RoomAssignment objects or dict
        termcode: Term code (e.g., "2252")
    
    Returns:
        Number of records inserted
    """
    print(f"\n  Processing {len(schedule)} courses for database insert...")
    print(f"  Termcode: {termcode}")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        count = 0
        tutorial_count = 0
        lab_count = 0
        
        for course in schedule:
            # Get room assignment for this course
            building = ''
            room = ''
            
            # Handle room_assignments as list or dict
            if isinstance(room_assignments, list):
                # It's a list of RoomAssignment objects
                for assignment in room_assignments:
                    if (assignment.subject.strip().upper() == course.subject.upper() and 
                        course.catalog_nbr in assignment.catalog_nbrs):
                        building = assignment.bldg
                        room = assignment.room
                        break
            elif isinstance(room_assignments, dict):
                # It's a dictionary
                key = (course.subject, course.catalog_nbr)
                building, room = room_assignments.get(key, ('', ''))
            
            # Process tutorials
            if course.tutorial:
                for tut_idx, tut in enumerate(course.tutorial):
                    for day_enum in tut.day:
                        day_numbers = extract_day_numbers(day_enum)
                        
                        for day_num in day_numbers:
                            # Get day columns
                            day_cols = day_number_to_day_columns(day_num)
                            
                            # Insert record
                            cursor.execute("""
                                INSERT INTO optimized_schedule
                                (subject, catalog, section, componentcode, termcode, classnumber,
                                 buildingcode, room, classstarttime, classendtime,
                                 mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                course.subject,
                                course.catalog_nbr,
                                course.class_nbr,  # Using class_nbr as section
                                'TUT',
                                termcode,
                                course.class_nbr,
                                '',  # No building for tutorials
                                '',  # No room for tutorials
                                minutes_to_time(tut.start),
                                minutes_to_time(tut.end),
                                day_cols['mondays'],
                                day_cols['tuesdays'],
                                day_cols['wednesdays'],
                                day_cols['thursdays'],
                                day_cols['fridays'],
                                day_cols['saturdays'],
                                day_cols['sundays']
                            ))
                            count += 1
                            tutorial_count += 1
            
            # Process labs
            if course.lab:
                for lab_idx, lab in enumerate(course.lab):
                    for day_enum in lab.day:
                        day_numbers = extract_day_numbers(day_enum)
                        
                        for day_num in day_numbers:
                            # Get day columns
                            day_cols = day_number_to_day_columns(day_num)
                            
                            # Insert record
                            cursor.execute("""
                                INSERT INTO optimized_schedule
                                (subject, catalog, section, componentcode, termcode, classnumber,
                                 buildingcode, room, classstarttime, classendtime,
                                 mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                course.subject,
                                course.catalog_nbr,
                                course.class_nbr,  # Using class_nbr as section
                                'LAB',
                                termcode,
                                course.class_nbr,
                                building,
                                room,
                                minutes_to_time(lab.start),
                                minutes_to_time(lab.end),
                                day_cols['mondays'],
                                day_cols['tuesdays'],
                                day_cols['wednesdays'],
                                day_cols['thursdays'],
                                day_cols['fridays'],
                                day_cols['saturdays'],
                                day_cols['sundays']
                            ))
                            count += 1
                            lab_count += 1
        
        conn.commit()
        print(f"\n  ✓ Inserted {count} schedule records")
        print(f"    - Tutorials: {tutorial_count}")
        print(f"    - Labs: {lab_count}")
        return count
        
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Error inserting records: {e}")
        import traceback
        traceback.print_exc()
        raise
        
    finally:
        cursor.close()
        conn.close()


def export_to_database(schedule: List[Course], room_assignments,
                      termcode: str) -> bool:
    """
    Export the optimized timetable to the database.
    
    Args:
        schedule: List of optimized Course objects
        room_assignments: List of RoomAssignment objects or dict
        termcode: Term code (e.g., "2252")
    
    Returns:
        True if successful, False otherwise
    """
    print("\n" + "=" * 70)
    print("EXPORTING TIMETABLE TO DATABASE")
    print("=" * 70)
    
    try:
        # Create table
        if not create_optimized_schedule_table():
            return False
        
        # Insert records
        print("\nInserting schedule records...")
        record_count = insert_schedule_records(schedule, room_assignments, termcode)
        
        print("\n" + "=" * 70)
        print("DATABASE EXPORT SUMMARY")
        print("=" * 70)
        print(f"Records inserted: {record_count}")
        print(f"Table: optimized_schedule")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Failed to export to database: {e}")
        import traceback
        traceback.print_exc()
        return False


# Standalone execution for testing
if __name__ == "__main__":
    print("Database Timetable Export Module")
    print("=" * 70)
    
    # Create table
    success = create_optimized_schedule_table()
    
    if success:
        print("\n✓ Table created successfully!")
        print("\nTable structure:")
        print("  subject, catalog, section, componentcode, termcode, classnumber,")
        print("  buildingcode, room, classstarttime, classendtime,")
        print("  mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays")
    else:
        print("\n✗ Failed to create table")
