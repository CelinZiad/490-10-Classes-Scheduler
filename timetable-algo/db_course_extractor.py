# db_course_extractor.py
"""
Module to extract course schedule data from the scheduleterm database table
and generate Data.csv for the genetic algorithm.
"""

import csv
from collections import defaultdict
from typing import List, Dict, Tuple
from datetime import datetime, time
from db import fetch_all
from course_filter import should_include_course


def build_termcode(year: int, season_code: int) -> str:
    """
    Build termcode from year and season.
    
    Format: 2 + YY + S
    Where: 2 is constant, YY is last 2 digits of year, S is season code
    
    Args:
        year: Academic year (e.g., 2025)
        season_code: 2=fall, 4=winter, 6=summer
    
    Returns:
        Termcode string (e.g., "2252" for Fall 2025)
    
    Examples:
        >>> build_termcode(2025, 2)
        '2252'
        >>> build_termcode(2025, 4)
        '2254'
    """
    year_suffix = str(year)[-2:]  # Last 2 digits
    return f"2{year_suffix}{season_code}"


def parse_time_to_dotted(time_obj) -> str:
    """
    Convert time object to dotted format (HH.MM.SS).
    
    Args:
        time_obj: datetime.time object or time string
    
    Returns:
        Time in HH.MM.SS format
    """
    if isinstance(time_obj, str):
        # Parse string time
        try:
            time_obj = datetime.strptime(time_obj, "%H:%M:%S").time()
        except:
            return "00.00.00"
    
    if isinstance(time_obj, time):
        return f"{time_obj.hour:02d}.{time_obj.minute:02d}.{time_obj.second:02d}"
    
    return "00.00.00"


def calculate_duration_minutes(start_time, end_time) -> int:
    """
    Calculate duration in minutes between start and end times.
    
    Args:
        start_time: Start time (time object or string)
        end_time: End time (time object or string)
    
    Returns:
        Duration in minutes
    """
    if isinstance(start_time, str):
        start_time = datetime.strptime(start_time, "%H:%M:%S").time()
    if isinstance(end_time, str):
        end_time = datetime.strptime(end_time, "%H:%M:%S").time()
    
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    
    return end_minutes - start_minutes


def parse_day_pattern(row: Dict) -> str:
    """
    Build day pattern from boolean day columns.
    
    Args:
        row: Database row with monday, tuesday, etc. columns
    
    Returns:
        Day pattern string (e.g., "MoWe", "TuTh")
    """
    day_map = [
        ('mondays', 'Mo'),
        ('tuesdays', 'Tu'),
        ('wednesdays', 'We'),
        ('thursdays', 'Th'),
        ('fridays', 'Fr'),
        ('saturdays', 'Sa'),
        ('sundays', 'Su')
    ]
    
    days = []
    for col, abbrev in day_map:
        if row.get(col) == True or str(row.get(col)).lower() == 'true':
            days.append(abbrev)
    
    return ''.join(days)


def fetch_schedule_data(termcode: str, department_code: str = "ELECCOEN") -> List[Dict]:
    """
    Fetch schedule data from database for specified term and department.
    
    Args:
        termcode: Term code (e.g., "2252" for Fall 2025)
        department_code: Department code (default "ELECCOEN")
    
    Returns:
        List of schedule records
    """
    sql = """
        SELECT subject, catalog, section, componentcode, termcode, classnumber,
               buildingcode, room, classstarttime, classendtime,
               mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays,
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
    """
    Extract the base lecture section identifier from a section string.
    
    The lecture section is the base identifier. Tutorials and labs append
    suffixes to this base:
    - Tutorials: space + letters (e.g., 'J' -> 'J JA', 'J JB')
    - Labs: letters + dash + suffix (e.g., 'J' -> 'JI-X', 'JK-X')
    
    Examples:
        'J' (LEC) -> 'J'
        'J JA' (TUT) -> 'J'
        'JI-X' (LAB) -> 'J'
        'AA' (LEC) -> 'AA'
        'AA AA' (TUT) -> 'AA'
        'AA-LA' (LAB) -> 'AA'
    
    Args:
        section: Section identifier from database
        componentcode: Component code (LEC, TUT, LAB)
    
    Returns:
        Base section identifier
    """
    if componentcode == 'LEC':
        # Lecture section is already the base
        return section.strip()
    
    # For TUT and LAB, extract the base section
    section = section.strip()
    
    # Tutorial format: "BASE SUFFIX" (e.g., "J JA")
    # Extract part before space
    if ' ' in section:
        return section.split()[0]
    
    # Lab format: "BASELETTERS-SUFFIX" (e.g., "JI-X")
    # Extract part before dash and remove appended letters
    if '-' in section:
        base = section.split('-')[0]
        # Remove trailing letters that are not part of base
        # E.g., "JI" -> "J", "AAL" -> "AA"
        # Strategy: Find the longest prefix that could be a lecture section
        # Typically 1-2 letters
        if len(base) > 1:
            # Try removing last letter
            return base[:-1] if base[:-1] else base
        return base
    
    # No space or dash - return as-is
    return section


def group_by_lecture(records: List[Dict]) -> Dict:
    """
    Group schedule records by lecture sections.
    
    Associates tutorials and labs with their parent lecture using the section field.
    
    Structure:
    {
        (subject, catalog, base_section): {
            'lecture': {...},
            'tutorials': [...],
            'labs': [...]
        }
    }
    
    Args:
        records: List of database records
    
    Returns:
        Grouped dictionary
    """
    grouped = defaultdict(lambda: {'lecture': None, 'tutorials': [], 'labs': []})
    
    for record in records:
        subject = record['subject']
        catalog = record['catalog']
        section = record['section']
        component = record['componentcode']
        
        # Filter courses
        if not should_include_course(subject, catalog):
            continue
        
        # Extract base section identifier (e.g., 'J' from 'J JA' or 'JI-X')
        base_section = extract_base_section(section, component)
        
        # Group by (subject, catalog, base_section)
        key = (subject, catalog, base_section)
        
        if component == 'LEC':
            grouped[key]['lecture'] = record
        elif component == 'TUT':
            grouped[key]['tutorials'].append(record)
        elif component == 'LAB':
            grouped[key]['labs'].append(record)
    
    return grouped


def count_unique_sections(components: List[Dict]) -> int:
    """
    Count unique sections based on section identifiers.
    
    Args:
        components: List of tutorial or lab records
    
    Returns:
        Number of unique sections
    """
    sections = set()
    for comp in components:
        # Use section identifier to count unique sections
        section = comp.get('section', '')
        sections.add(section)
    
    return len(sections)


def determine_lab_frequency(labs: List[Dict]) -> int:
    """
    Determine biweekly lab frequency.
    
    Logic:
    - Count unique sections
    - If sections meet on different weeks, it's biweekly with frequency 1
    - If sections repeat on same days every week, frequency is 2
    - Default to 1 (once every two weeks)
    
    Args:
        labs: List of lab records
    
    Returns:
        Frequency (1 = once every 2 weeks, 2 = twice every 2 weeks)
    """
    if not labs:
        return 0
    
    # For now, default to 1 (once every two weeks)
    # This can be enhanced by analyzing meeting patterns
    return 1


def determine_tutorial_frequency(tutorials: List[Dict]) -> int:
    """
    Determine weekly tutorial frequency.
    
    Logic:
    - Tutorials typically meet weekly
    - Default to 1 (once per week)
    
    Args:
        tutorials: List of tutorial records
    
    Returns:
        Frequency (1 = once per week)
    """
    if not tutorials:
        return 0
    
    # Tutorials are typically weekly
    return 1


def generate_data_csv(output_path: str = "Data.csv", 
                     year: int = 2025, 
                     season_code: int = 2) -> int:
    """
    Generate Data.csv from database scheduleterm table.
    
    Args:
        output_path: Path to output CSV file
        year: Academic year (e.g., 2025)
        season_code: Season code from config (2=fall, 4=winter)
    
    Returns:
        Number of rows written
    """
    print("\n" + "=" * 70)
    print("EXTRACTING COURSE SCHEDULE DATA FROM DATABASE")
    season_name = {2: 'FALL', 4: 'WINTER', 6: 'SUMMER'}.get(season_code, 'UNKNOWN')
    print(f"Academic Year: {year}, Term: {season_name} ({season_code})")
    print("=" * 70)
    
    # Build termcode
    termcode = build_termcode(year, season_code)
    print(f"Termcode: {termcode}")
    
    # Fetch data
    print("Fetching schedule data...")
    records = fetch_schedule_data(termcode, "ELECCOEN")
    print(f"  Found {len(records)} schedule records")
    
    if not records:
        print("  Warning: No schedule data found for this term")
        return 0
    
    # Group by lecture
    print("Grouping by lecture sections...")
    grouped = group_by_lecture(records)
    print(f"  Found {len(grouped)} lecture sections")
    
    # Build CSV rows
    rows = []
    skipped = 0
    
    for (subject, catalog, classnumber), data in sorted(grouped.items()):
        lecture = data['lecture']
        
        if not lecture:
            skipped += 1
            continue
        
        # Parse lecture info
        day_pattern = parse_day_pattern(lecture)
        start_time = parse_time_to_dotted(lecture['classstarttime'])
        end_time = parse_time_to_dotted(lecture['classendtime'])
        
        # Count tutorials
        tut_count = count_unique_sections(data['tutorials'])
        tut_duration = 0
        weekly_tut_freq = 0
        
        if data['tutorials']:
            # Get duration from first tutorial
            tut = data['tutorials'][0]
            tut_duration = calculate_duration_minutes(
                tut['classstarttime'], 
                tut['classendtime']
            )
            weekly_tut_freq = determine_tutorial_frequency(data['tutorials'])
        
        # Count labs
        lab_count = count_unique_sections(data['labs'])
        lab_duration = 0
        biweekly_lab_freq = 0
        
        if data['labs']:
            # Get duration from first lab
            lab = data['labs'][0]
            lab_duration = calculate_duration_minutes(
                lab['classstarttime'], 
                lab['classendtime']
            )
            biweekly_lab_freq = determine_lab_frequency(data['labs'])
        
        # Create row
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
    
    if skipped > 0:
        print(f"  Skipped {skipped} entries without lectures")
    
    # Write to CSV
    fieldnames = [
        'subject', 'catalog_nbr', 'class_nbr', 'day_of_week',
        'start_time', 'end_time', 'lab_count', 'biweekly_lab_freq',
        'lab_duration', 'tut_count', 'weekly_tut_freq', 'tut_duration'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\nGenerated {output_path}:")
    print(f"  {len(rows)} course sections")
    
    # Display summary
    subject_counts = defaultdict(int)
    for row in rows:
        subject_counts[row['subject']] += 1
    
    print("\nCourses per subject:")
    for subject in sorted(subject_counts.keys()):
        print(f"  {subject}: {subject_counts[subject]} sections")
    
    # Lab/Tutorial summary
    with_labs = sum(1 for r in rows if r['lab_count'])
    with_tuts = sum(1 for r in rows if r['tut_count'])
    print(f"\nComponents:")
    print(f"  Sections with labs: {with_labs}")
    print(f"  Sections with tutorials: {with_tuts}")
    
    print("=" * 70)
    
    return len(rows)


def display_data_summary(output_path: str = "Data.csv"):
    """Display a summary of the generated Data.csv file."""
    print("\n" + "=" * 70)
    print("DATA.CSV SUMMARY")
    print("=" * 70)
    
    with open(output_path, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        print("No data found in CSV")
        return
    
    print(f"Total sections: {len(rows)}")
    
    # Display sample rows
    print("\nSample entries:")
    print(f"{'Subject':<8} {'Catalog':<8} {'Class#':<8} {'Days':<8} {'Labs':<6} {'Tuts':<6}")
    print("-" * 50)
    
    for row in rows[:10]:
        print(f"{row['subject']:<8} {row['catalog_nbr']:<8} {row['class_nbr']:<8} "
              f"{row['day_of_week']:<8} {row['lab_count']:<6} {row['tut_count']:<6}")
    
    if len(rows) > 10:
        print(f"  ... and {len(rows) - 10} more sections")
    
    print("=" * 70)


def extract_and_generate_course_data(output_path: str = "Data.csv",
                                     year: int = 2025,
                                     season_code: int = 2,
                                     show_summary: bool = True) -> bool:
    """
    Main function to extract course schedule data and generate Data.csv.
    
    Args:
        output_path: Path to output CSV file
        year: Academic year
        season_code: Season code from config
        show_summary: Whether to display summary
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Generate the CSV
        num_rows = generate_data_csv(output_path, year, season_code)
        
        if num_rows == 0:
            print("\n⚠ Warning: No data generated")
            return False
        
        # Display summary if requested
        if show_summary:
            display_data_summary(output_path)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error generating Data.csv: {e}")
        import traceback
        traceback.print_exc()
        return False


# Standalone execution
if __name__ == "__main__":
    import sys
    from config import TARGET_SEASON
    
    print("Course Schedule Data Extractor")
    print("=" * 70)
    
    # Get year from command line or use default
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    season = TARGET_SEASON
    
    success = extract_and_generate_course_data(
        year=year,
        season_code=season,
        show_summary=True
    )
    
    if success:
        print("\n✓ Data.csv generated successfully!")
    else:
        print("\n✗ Failed to generate Data.csv")
        sys.exit(1)
