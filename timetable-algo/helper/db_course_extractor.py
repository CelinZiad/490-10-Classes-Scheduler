# db_course_extractor.py
import csv
from collections import defaultdict
from typing import List, Dict, Tuple
from datetime import datetime, time
from .db import fetch_all
from genetic_algo.course_filter import should_include_course


def build_termcode(year: int, season_code: int) -> str:
    """Build termcode from year and season (Format: 2 + YY + S)."""
    year_suffix = str(year)[-2:]
    return f"2{year_suffix}{season_code}"


def parse_time_to_dotted(time_obj) -> str:
    """Convert time object to dotted format (HH.MM.SS)."""
    if isinstance(time_obj, str):
        try:
            time_obj = datetime.strptime(time_obj, "%H:%M:%S").time()
        except:
            return "00.00.00"
    
    if isinstance(time_obj, time):
        return f"{time_obj.hour:02d}.{time_obj.minute:02d}.{time_obj.second:02d}"
    
    return "00.00.00"


def calculate_duration_minutes(start_time, end_time) -> int:
    """Calculate duration in minutes between start and end times."""
    if isinstance(start_time, str):
        start_time = datetime.strptime(start_time, "%H:%M:%S").time()
    if isinstance(end_time, str):
        end_time = datetime.strptime(end_time, "%H:%M:%S").time()
    
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    
    return end_minutes - start_minutes


def parse_day_pattern(row: Dict) -> str:
    """Build day pattern from boolean day columns (e.g., "MoWe", "TuTh")."""
    day_map = [
        ('mondays', 'Mo'), ('tuesdays', 'Tu'), ('wednesdays', 'We'),
        ('thursdays', 'Th'), ('fridays', 'Fr'), ('saturdays', 'Sa'), ('sundays', 'Su')
    ]
    
    days = []
    for col, abbrev in day_map:
        if row.get(col) == True or str(row.get(col)).lower() == 'true':
            days.append(abbrev)
    
    return ''.join(days)


def fetch_schedule_data(termcode: str, department_code: str = "ELECCOEN") -> List[Dict]:
    """Fetch schedule data from database for specified term and department."""
    sql = """
        SELECT subject, catalog, section, componentcode, termcode, classnumber,
               session, buildingcode, room, instructionmodecode, locationcode,
               classstarttime, classendtime, classstartdate, classenddate,
               mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays,
               currentwaitlisttotal, waitlistcapacity, enrollmentcapacity, currentenrollment,
               departmentcode, facultycode, facultydescription, career,
               meetingpatternnumber
        FROM scheduleterm
        WHERE termcode = %s 
          AND departmentcode = %s
          AND meetingpatternnumber = 1
          AND classstarttime != '00:00:00'
        ORDER BY subject, catalog, classnumber, componentcode
    """
    
    return fetch_all(sql, (termcode, department_code))


def extract_base_section(section: str, componentcode: str) -> str:
    """Extract the base lecture section identifier from a section string."""
    if componentcode == 'LEC':
        return section.strip()
    
    section = section.strip()
    
    if ' ' in section:
        return section.split()[0]
    
    if '-' in section:
        base = section.split('-')[0]
        if len(base) > 1:
            return base[:-1] if base[:-1] else base
        return base
    
    return section


def group_by_lecture(records: List[Dict]) -> Dict:
    """Group schedule records by lecture sections."""
    grouped = defaultdict(lambda: {'lecture': None, 'tutorials': [], 'labs': []})
    
    for record in records:
        subject = record['subject']
        catalog = record['catalog']
        section = record['section']
        component = record['componentcode']
        
        if not should_include_course(subject, catalog):
            continue
        
        base_section = extract_base_section(section, component)
        key = (subject, catalog, base_section)
        
        if component == 'LEC':
            grouped[key]['lecture'] = record
        elif component == 'TUT':
            grouped[key]['tutorials'].append(record)
        elif component == 'LAB':
            grouped[key]['labs'].append(record)
    
    return grouped


def count_unique_sections(components: List[Dict]) -> int:
    """Count unique sections based on section identifiers."""
    sections = set()
    for comp in components:
        section = comp.get('section', '')
        sections.add(section)
    
    return len(sections)


def determine_lab_frequency(labs: List[Dict]) -> int:
    """Determine biweekly lab frequency (default to 1 = once every two weeks)."""
    if not labs:
        return 0
    return 1


def determine_tutorial_frequency(tutorials: List[Dict]) -> int:
    """Determine weekly tutorial frequency (default to 1 = once per week)."""
    if not tutorials:
        return 0
    return 1


def generate_data_csv(output_path: str = "Data.csv", 
                     year: int = 2025, 
                     season_code: int = 2) -> int:
    """Generate Data.csv from database scheduleterm table."""
    previous_year = year - 1
    termcode = build_termcode(previous_year, season_code)
    
    records = fetch_schedule_data(termcode, "ELECCOEN")
    
    if not records:
        return 0
    
    grouped = group_by_lecture(records)
    
    rows = []
    
    for (subject, catalog, classnumber), data in sorted(grouped.items()):
        lecture = data['lecture']
        
        if not lecture:
            continue
        
        day_pattern = parse_day_pattern(lecture)
        start_time = parse_time_to_dotted(lecture['classstarttime'])
        end_time = parse_time_to_dotted(lecture['classendtime'])
        
        tut_count = count_unique_sections(data['tutorials'])
        tut_duration = 0
        weekly_tut_freq = 0
        
        if data['tutorials']:
            tut = data['tutorials'][0]
            tut_duration = calculate_duration_minutes(
                tut['classstarttime'], 
                tut['classendtime']
            )
            weekly_tut_freq = determine_tutorial_frequency(data['tutorials'])
        
        lab_count = count_unique_sections(data['labs'])
        lab_duration = 0
        biweekly_lab_freq = 0
        
        if data['labs']:
            lab = data['labs'][0]
            lab_duration = calculate_duration_minutes(
                lab['classstarttime'], 
                lab['classendtime']
            )
            biweekly_lab_freq = determine_lab_frequency(data['labs'])
        
        row = {
            'subject': subject,
            'catalog_nbr': catalog,
            'class_nbr': classnumber,
            'day_of_week': day_pattern,
            'start_time': start_time,
            'end_time': end_time,
            'lab_count': lab_count if lab_count > 0 else '',
            'biweekly_lab_freq': biweekly_lab_freq if lab_count > 0 else '',
            'lab_duration': lab_duration if lab_count > 0 else '',
            'tut_count': tut_count if tut_count > 0 else '',
            'weekly_tut_freq': weekly_tut_freq if tut_count > 0 else '',
            'tut_duration': tut_duration if tut_count > 0 else ''
        }
        
        rows.append(row)
    
    fieldnames = [
        'subject', 'catalog_nbr', 'class_nbr', 'day_of_week',
        'start_time', 'end_time', 'lab_count', 'biweekly_lab_freq',
        'lab_duration', 'tut_count', 'weekly_tut_freq', 'tut_duration'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    return len(rows)


def display_data_summary(output_path: str = "Data.csv"):
    """Display a summary of the generated Data.csv file."""
    with open(output_path, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)


def extract_and_generate_course_data(output_path: str = "Data.csv",
                                     year: int = 2025,
                                     season_code: int = 2,
                                     show_summary: bool = True) -> bool:
    """Main function to extract course schedule data and generate Data.csv."""
    try:
        num_rows = generate_data_csv(output_path, year, season_code)
        
        if num_rows == 0:
            return False
        
        if show_summary:
            display_data_summary(output_path)
        
        return True
        
    except Exception:
        return False


if __name__ == "__main__":
    import sys
    from genetic_algo.config import TARGET_SEASON
    
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    season = TARGET_SEASON
    
    extract_and_generate_course_data(year=year, season_code=season, show_summary=True)
