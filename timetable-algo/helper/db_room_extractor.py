# db_room_extractor.py
import csv
from collections import defaultdict
from typing import List, Dict, Tuple
from .db import fetch_all


def should_include_course(subject: str, catalog: str) -> bool:
    """Determine if a course should be included in scheduling (COEN, ELEC, ENGR 290)."""
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
    """Fetch all lab room information from the database (excludes room 007 and AITS)."""
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
    """Fetch all course-lab room assignments from the database (COEN, ELEC, ENGR 290 only)."""
    sql = """
        SELECT labroomid, subject, catalog, comments
        FROM courselabs
        ORDER BY subject, catalog, labroomid
    """
    
    rows = fetch_all(sql)
    
    assignments = []
    
    for row in rows:
        if not should_include_course(row['subject'], row['catalog']):
            continue
        
        assignments.append({
            'labroomid': row['labroomid'],
            'subject': row['subject'],
            'catalog': row['catalog'],
            'comments': row['comments'] or ''
        })
    
    return assignments


def group_courses_by_room(assignments: List[Dict]) -> Dict[int, List[Tuple[str, str]]]:
    """Group courses by their assigned lab room."""
    room_courses = defaultdict(list)
    
    for assignment in assignments:
        labroomid = assignment['labroomid']
        subject = assignment['subject']
        catalog = assignment['catalog']
        
        course_tuple = (subject, catalog)
        if course_tuple not in room_courses[labroomid]:
            room_courses[labroomid].append(course_tuple)
    
    return room_courses


def generate_room_data_csv(output_path: str = "Room_data.csv") -> int:
    """Generate Room_data.csv from database tables (excludes room 007 and AITS)."""
    lab_rooms = fetch_lab_rooms()
    assignments = fetch_course_lab_assignments()
    room_courses = group_courses_by_room(assignments)
    
    rows = []
    
    for labroomid in sorted(room_courses.keys()):
        if labroomid not in lab_rooms:
            continue
        
        room_info = lab_rooms[labroomid]
        building = room_info['building']
        room = room_info['room']
        
        courses = room_courses[labroomid]
        
        subject_courses = defaultdict(list)
        for subject, catalog in courses:
            subject_courses[subject].append(catalog)
        
        for subject, catalogs in subject_courses.items():
            unique_catalogs = sorted(set(catalogs))
            
            row = {
                'bldg': building,
                'room': room,
                'subject': subject
            }
            
            for i, catalog in enumerate(unique_catalogs, start=1):
                row[f'course{i}'] = catalog
            
            rows.append(row)
    
    max_courses = max(len([k for k in row.keys() if k.startswith('course')]) 
                     for row in rows) if rows else 0
    
    fieldnames = ['bldg', 'room', 'subject'] + [f'course{i}' for i in range(1, max_courses + 1)]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    return len(rows)


def display_room_summary(output_path: str = "Room_data.csv"):
    """Display a summary of the generated Room_data.csv file."""
    with open(output_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    subject_counts = defaultdict(int)
    for row in rows:
        subject = row['subject']
        course_count = len([v for k, v in row.items() 
                          if k.startswith('course') and v])
        subject_counts[subject] += course_count


def verify_database_connection():
    """Verify that the database connection is working."""
    try:
        rows = fetch_all("SELECT 1 as test")
        return rows and rows[0]['test'] == 1
    except Exception:
        return False


def extract_and_generate_room_data(output_path: str = "Room_data.csv", 
                                   show_summary: bool = True) -> bool:
    """Main function to extract data from database and generate Room_data.csv."""
    try:
        if not verify_database_connection():
            return False
        
        generate_room_data_csv(output_path)
        
        if show_summary:
            display_room_summary(output_path)
        
        return True
        
    except Exception:
        return False


if __name__ == "__main__":
    extract_and_generate_room_data()
