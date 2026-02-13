# db_room_extractor.py
"""
Module to extract lab room assignments from the database and generate Room_data.csv.
This replaces manual entry of room data by querying the database tables.
"""

import csv
from collections import defaultdict
from typing import List, Dict, Tuple
from db import fetch_all


def should_include_course(subject: str, catalog: str) -> bool:
    """
    Determine if a course should be included in scheduling.
    
    Include only:
    - COEN courses
    - ELEC courses  
    - ENGR 290
    """
    subject = subject.upper().strip()
    catalog = catalog.strip()
    
    if subject == "COEN":
        return True
    if subject == "ELEC":
        return True
    if subject == "ENGR" and catalog == "290":
        return True
    
    return False


def fetch_lab_rooms() -> Dict[int, Dict]:
    """
    Fetch all lab room information from the database.
    Excludes room 007 and AITS rooms.
    
    Returns:
        Dictionary mapping labroomid to room details
    """
    sql = """
        SELECT labroomid, campus, building, room, resources, capacity, capacitymax
        FROM labrooms
        WHERE room NOT IN ('007', 'AITS')
        ORDER BY labroomid
    """
    
    rows = fetch_all(sql)
    
    lab_rooms = {}
    for row in rows:
        lab_rooms[row['labroomid']] = {
            'campus': row['campus'],
            'building': row['building'],
            'room': row['room'],
            'resources': row['resources'] or '',
            'capacity': row['capacity'],
            'capacitymax': row['capacitymax']
        }
    
    return lab_rooms


def fetch_course_lab_assignments() -> List[Dict]:
    """
    Fetch all course-lab room assignments from the database.
    Filters to only include COEN, ELEC, and ENGR 290 courses.
    
    Returns:
        List of assignment dictionaries
    """
    sql = """
        SELECT labroomid, subject, catalog, comments
        FROM courselabs
        ORDER BY subject, catalog, labroomid
    """
    
    rows = fetch_all(sql)
    
    assignments = []
    filtered_count = 0
    
    for row in rows:
        # Filter courses
        if not should_include_course(row['subject'], row['catalog']):
            filtered_count += 1
            continue
        
        assignments.append({
            'labroomid': row['labroomid'],
            'subject': row['subject'],
            'catalog': row['catalog'],
            'comments': row['comments'] or ''
        })
    
    if filtered_count > 0:
        print(f"  Filtered out {filtered_count} non-COEN/ELEC/ENGR290 course assignments")
    
    return assignments


def group_courses_by_room(assignments: List[Dict]) -> Dict[int, List[Tuple[str, str]]]:
    """
    Group courses by their assigned lab room.
    
    Args:
        assignments: List of course-lab assignments
    
    Returns:
        Dictionary mapping labroomid to list of (subject, catalog) tuples
    """
    room_courses = defaultdict(list)
    
    for assignment in assignments:
        labroomid = assignment['labroomid']
        subject = assignment['subject']
        catalog = assignment['catalog']
        
        # Avoid duplicates
        course_tuple = (subject, catalog)
        if course_tuple not in room_courses[labroomid]:
            room_courses[labroomid].append(course_tuple)
    
    return room_courses


def generate_room_data_csv(output_path: str = "Room_data.csv") -> int:
    """
    Generate Room_data.csv from database tables.
    Excludes room 007 and AITS rooms.
    
    Format matches the original Room_data.csv:
    bldg,room,subject,course1,course2,...
    
    Args:
        output_path: Path to output CSV file
    
    Returns:
        Number of rows written
    """
    print("\n" + "=" * 70)
    print("EXTRACTING LAB ROOM DATA FROM DATABASE")
    print("(Excluding room 007 and AITS)")
    print("=" * 70)
    
    # Fetch data from database
    print("Fetching lab rooms...")
    lab_rooms = fetch_lab_rooms()
    print(f"  Found {len(lab_rooms)} lab rooms")
    
    print("Fetching course-lab assignments...")
    assignments = fetch_course_lab_assignments()
    print(f"  Found {len(assignments)} course-lab assignments")
    
    # Group courses by room
    print("Grouping courses by room...")
    room_courses = group_courses_by_room(assignments)
    print(f"  {len(room_courses)} rooms have course assignments")
    
    # Prepare rows for CSV
    rows = []
    
    for labroomid in sorted(room_courses.keys()):
        if labroomid not in lab_rooms:
            print(f"  Warning: labroomid {labroomid} not found in labrooms table")
            continue
        
        room_info = lab_rooms[labroomid]
        building = room_info['building']
        room = room_info['room']
        
        # Get all courses for this room
        courses = room_courses[labroomid]
        
        # Group courses by subject
        subject_courses = defaultdict(list)
        for subject, catalog in courses:
            subject_courses[subject].append(catalog)
        
        # Create a row for each subject in this room
        for subject, catalogs in subject_courses.items():
            # Remove duplicates and sort
            unique_catalogs = sorted(set(catalogs))
            
            row = {
                'bldg': building,
                'room': room,
                'subject': subject
            }
            
            # Add course columns (course1, course2, etc.)
            for i, catalog in enumerate(unique_catalogs, start=1):
                row[f'course{i}'] = catalog
            
            rows.append(row)
    
    # Determine maximum number of courses per room
    max_courses = max(len([k for k in row.keys() if k.startswith('course')]) 
                     for row in rows) if rows else 0
    
    # Write to CSV
    fieldnames = ['bldg', 'room', 'subject'] + [f'course{i}' for i in range(1, max_courses + 1)]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\nGenerated Room_data.csv:")
    print(f"  {len(rows)} room-subject assignments")
    print(f"  Maximum {max_courses} courses per room")
    print(f"  Output file: {output_path}")
    print("=" * 70)
    
    return len(rows)


def display_room_summary(output_path: str = "Room_data.csv"):
    """
    Display a summary of the generated Room_data.csv file.
    """
    print("\n" + "=" * 70)
    print("ROOM DATA SUMMARY")
    print("=" * 70)
    
    # Read the generated file
    with open(output_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Count courses per subject
    subject_counts = defaultdict(int)
    for row in rows:
        subject = row['subject']
        course_count = len([v for k, v in row.items() 
                          if k.startswith('course') and v])
        subject_counts[subject] += course_count
    
    print(f"Total rooms: {len(set((row['bldg'], row['room']) for row in rows))}")
    print(f"Total assignments: {len(rows)}")
    print("\nCourses per subject:")
    for subject in sorted(subject_counts.keys()):
        print(f"  {subject}: {subject_counts[subject]} courses")
    
    # Display sample rows
    print("\nSample assignments:")
    for i, row in enumerate(rows[:5]):
        courses = [v for k, v in row.items() if k.startswith('course') and v]
        print(f"  {row['bldg']}-{row['room']} ({row['subject']}): {', '.join(courses)}")
    
    if len(rows) > 5:
        print(f"  ... and {len(rows) - 5} more")
    
    print("=" * 70)


def verify_database_connection():
    """
    Verify that the database connection is working.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        print("Testing database connection...")
        rows = fetch_all("SELECT 1 as test")
        if rows and rows[0]['test'] == 1:
            print("✓ Database connection successful")
            return True
        else:
            print("✗ Database connection failed: unexpected result")
            return False
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def extract_and_generate_room_data(output_path: str = "Room_data.csv", 
                                   show_summary: bool = True) -> bool:
    """
    Main function to extract data from database and generate Room_data.csv.
    
    Args:
        output_path: Path to output CSV file
        show_summary: Whether to display summary after generation
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Verify connection
        if not verify_database_connection():
            return False
        
        # Generate the CSV
        num_rows = generate_room_data_csv(output_path)
        
        # Display summary if requested
        if show_summary:
            display_room_summary(output_path)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error generating Room_data.csv: {e}")
        import traceback
        traceback.print_exc()
        return False


# Standalone execution
if __name__ == "__main__":
    print("Lab Room Data Extractor")
    print("=" * 70)
    
    success = extract_and_generate_room_data()
    
    if success:
        print("\n✓ Room_data.csv generated successfully!")
    else:
        print("\n✗ Failed to generate Room_data.csv")
        exit(1)
