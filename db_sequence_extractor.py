# db_sequence_extractor.py
"""
Module to extract sequence plan data from the database and generate Sequences.csv.
Handles multiple sequence plans with terms and courses.
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
    
    Args:
        subject: Course subject (e.g., "COEN", "ELEC", "ENGR")
        catalog: Course catalog number (e.g., "212", "290")
    
    Returns:
        True if course should be included, False otherwise
    """
    subject = subject.upper().strip()
    catalog = catalog.strip()
    
    # Include all COEN courses
    if subject == "COEN":
        return True
    
    # Include all ELEC courses
    if subject == "ELEC":
        return True
    
    # Include only ENGR 290
    if subject == "ENGR" and catalog == "290":
        return True
    
    # Exclude all other courses
    return False


def fetch_sequence_plans() -> List[Dict]:
    """
    Fetch all sequence plans from the database.
    
    Returns:
        List of sequence plan dictionaries
    """
    sql = """
        SELECT planid, planname, program, entryterm, option, durationyears, publishedon
        FROM sequenceplan
        ORDER BY planid
    """
    
    return fetch_all(sql)


def fetch_sequence_terms() -> List[Dict]:
    """
    Fetch all sequence terms from the database.
    
    Returns:
        List of sequence term dictionaries
    """
    sql = """
        SELECT sequencetermid, planid, yearnumber, season, workterm, notes
        FROM sequenceterm
        ORDER BY planid, yearnumber, 
                 CASE season 
                     WHEN 'fall' THEN 1 
                     WHEN 'winter' THEN 2 
                     WHEN 'summer' THEN 3 
                 END
    """
    
    return fetch_all(sql)


def fetch_sequence_courses() -> List[Dict]:
    """
    Fetch all sequence courses from the database.
    
    Returns:
        List of sequence course dictionaries
    """
    sql = """
        SELECT sequencetermid, subject, catalog, label, iselective
        FROM sequencecourse
        ORDER BY sequencetermid, subject, catalog
    """
    
    return fetch_all(sql)


def season_to_number(season: str) -> int:
    """Convert season name to number (2=fall, 4=winter, 6=summer)."""
    season_map = {
        'fall': 2,
        'winter': 4,
        'summer': 6
    }
    return season_map.get(season.lower(), 0)


def build_sequence_structure():
    """
    Build the complete sequence structure from database.
    
    Returns:
        Dictionary with structure:
        {
            planid: {
                'info': plan_info,
                'terms': {
                    sequencetermid: {
                        'info': term_info,
                        'courses': [list of course codes]
                    }
                }
            }
        }
    """
    print("\n" + "=" * 70)
    print("BUILDING SEQUENCE STRUCTURE FROM DATABASE")
    print("=" * 70)
    
    # Fetch all data
    print("Fetching sequence plans...")
    plans = fetch_sequence_plans()
    print(f"  Found {len(plans)} sequence plans")
    
    print("Fetching sequence terms...")
    terms = fetch_sequence_terms()
    print(f"  Found {len(terms)} sequence terms")
    
    print("Fetching sequence courses...")
    courses = fetch_sequence_courses()
    print(f"  Found {len(courses)} course assignments")
    
    # Build structure
    structure = {}
    
    # Add plans
    for plan in plans:
        structure[plan['planid']] = {
            'info': {
                'planname': plan['planname'],
                'program': plan['program'],
                'entryterm': plan['entryterm'],
                'option': plan['option'],
                'durationyears': plan['durationyears']
            },
            'terms': {}
        }
    
    # Add terms
    for term in terms:
        planid = term['planid']
        if planid in structure:
            structure[planid]['terms'][term['sequencetermid']] = {
                'info': {
                    'yearnumber': term['yearnumber'],
                    'season': term['season'],
                    'season_code': season_to_number(term['season']),
                    'workterm': term['workterm'],
                    'notes': term['notes'] or ''
                },
                'courses': []
            }
    
    # Add courses to terms (with filtering)
    filtered_count = 0
    for course in courses:
        # Filter courses - only COEN, ELEC, and ENGR 290
        if not should_include_course(course['subject'], course['catalog']):
            filtered_count += 1
            continue
        
        sequencetermid = course['sequencetermid']
        course_code = f"{course['subject']}{course['catalog']}"
        
        # Find which plan this term belongs to
        for planid, plan_data in structure.items():
            if sequencetermid in plan_data['terms']:
                plan_data['terms'][sequencetermid]['courses'].append(course_code)
                break
    
    if filtered_count > 0:
        print(f"  Filtered out {filtered_count} non-COEN/ELEC/ENGR290 courses")
    
    return structure


def generate_sequences_csv(output_path: str = "Sequences.csv", 
                           target_season: int = None) -> int:
    """
    Generate Sequences.csv from database tables.
    
    Format:
    planid,planname,program,sequencetermid,yearnumber,season,season_code,courses
    
    Args:
        output_path: Path to output CSV file
        target_season: Optional filter (2=fall, 4=winter, 6=summer)
    
    Returns:
        Number of rows written
    """
    print("\n" + "=" * 70)
    print("GENERATING SEQUENCES CSV")
    if target_season:
        season_name = {2: 'FALL', 4: 'WINTER', 6: 'SUMMER'}.get(target_season, 'UNKNOWN')
        print(f"Filtering for season: {season_name} (code: {target_season})")
    print("=" * 70)
    
    # Build structure
    structure = build_sequence_structure()
    
    # Prepare rows
    rows = []
    
    for planid in sorted(structure.keys()):
        plan_data = structure[planid]
        plan_info = plan_data['info']
        
        for sequencetermid in sorted(plan_data['terms'].keys()):
            term_data = plan_data['terms'][sequencetermid]
            term_info = term_data['info']
            
            # Skip work terms (no courses)
            if term_info['workterm']:
                continue
            
            # Filter by season if specified
            if target_season is not None and term_info['season_code'] != target_season:
                continue
            
            # Skip if no courses
            if not term_data['courses']:
                continue
            
            # Create row
            row = {
                'planid': planid,
                'planname': plan_info['planname'],
                'program': plan_info['program'],
                'sequencetermid': sequencetermid,
                'yearnumber': term_info['yearnumber'],
                'season': term_info['season'],
                'season_code': term_info['season_code'],
                'courses': ','.join(term_data['courses'])
            }
            
            rows.append(row)
    
    # Write to CSV
    if rows:
        fieldnames = ['planid', 'planname', 'program', 'sequencetermid', 
                     'yearnumber', 'season', 'season_code', 'courses']
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    
    print(f"\nGenerated {output_path}:")
    print(f"  {len(rows)} sequence terms")
    
    # Display summary by plan
    plan_counts = defaultdict(int)
    for row in rows:
        plan_counts[row['planname']] += 1
    
    print(f"\nTerms per plan:")
    for planname in sorted(plan_counts.keys()):
        print(f"  {planname}: {plan_counts[planname]} terms")
    
    print("=" * 70)
    
    return len(rows)


def display_sequence_summary(output_path: str = "Sequences.csv"):
    """Display a summary of the generated Sequences.csv file."""
    print("\n" + "=" * 70)
    print("SEQUENCE DATA SUMMARY")
    print("=" * 70)
    
    with open(output_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        print("No sequences found in CSV")
        return
    
    # Group by plan
    plans = defaultdict(list)
    for row in rows:
        plans[row['planname']].append(row)
    
    print(f"Total plans: {len(plans)}")
    print(f"Total terms: {len(rows)}")
    
    # Display each plan
    for planname in sorted(plans.keys()):
        plan_rows = plans[planname]
        print(f"\n{planname}:")
        print(f"  Program: {plan_rows[0]['program']}")
        print(f"  Terms: {len(plan_rows)}")
        
        # Sample terms
        for i, row in enumerate(plan_rows[:3]):
            courses = row['courses'].split(',')
            course_list = ', '.join(courses[:5])
            if len(courses) > 5:
                course_list += f", ... ({len(courses)} total)"
            print(f"    Year {row['yearnumber']} {row['season']}: {course_list}")
        
        if len(plan_rows) > 3:
            print(f"    ... and {len(plan_rows) - 3} more terms")
    
    print("=" * 70)


def extract_and_generate_sequences(output_path: str = "Sequences.csv",
                                   target_season: int = None,
                                   show_summary: bool = True) -> bool:
    """
    Main function to extract sequences from database and generate CSV.
    
    Args:
        output_path: Path to output CSV file
        target_season: Optional season filter (2=fall, 4=winter, 6=summer)
        show_summary: Whether to display summary after generation
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Generate the CSV
        num_rows = generate_sequences_csv(output_path, target_season)
        
        # Display summary if requested
        if show_summary:
            display_sequence_summary(output_path)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error generating Sequences.csv: {e}")
        import traceback
        traceback.print_exc()
        return False


# Standalone execution
if __name__ == "__main__":
    import sys
    
    print("Sequence Data Extractor")
    print("=" * 70)
    
    # Check for season argument
    target_season = None
    if len(sys.argv) > 1:
        season_arg = sys.argv[1].lower()
        if season_arg in ['fall', '2']:
            target_season = 2
        elif season_arg in ['winter', '4']:
            target_season = 4
        elif season_arg in ['summer', '6']:
            target_season = 6
    
    success = extract_and_generate_sequences(target_season=target_season)
    
    if success:
        print("\n✓ Sequences.csv generated successfully!")
    else:
        print("\n✗ Failed to generate Sequences.csv")
        sys.exit(1)
