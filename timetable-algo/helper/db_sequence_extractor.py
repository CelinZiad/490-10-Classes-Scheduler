# db_sequence_extractor.py
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


def fetch_sequence_plans() -> List[Dict]:
    """Fetch all sequence plans from the database."""
    sql = """
        SELECT planid, planname, program, entryterm, option, durationyears, publishedon
        FROM sequenceplan
        ORDER BY planid
    """
    
    return fetch_all(sql)


def fetch_sequence_terms() -> List[Dict]:
    """Fetch all sequence terms from the database."""
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
    """Fetch all sequence courses from the database."""
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
    """Build the complete sequence structure from database."""
    plans = fetch_sequence_plans()
    terms = fetch_sequence_terms()
    courses = fetch_sequence_courses()
    
    structure = {}
    
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
    
    for course in courses:
        if not should_include_course(course['subject'], course['catalog']):
            continue
        
        sequencetermid = course['sequencetermid']
        course_code = f"{course['subject']}{course['catalog']}"
        
        for planid, plan_data in structure.items():
            if sequencetermid in plan_data['terms']:
                plan_data['terms'][sequencetermid]['courses'].append(course_code)
                break
    
    return structure


def generate_sequences_csv(output_path: str = "Sequences.csv", 
                           target_season: int = None) -> int:
    """Generate Sequences.csv from database tables."""
    structure = build_sequence_structure()
    
    rows = []
    
    for planid in sorted(structure.keys()):
        plan_data = structure[planid]
        plan_info = plan_data['info']
        
        for sequencetermid in sorted(plan_data['terms'].keys()):
            term_data = plan_data['terms'][sequencetermid]
            term_info = term_data['info']
            
            if term_info['workterm']:
                continue
            
            if target_season is not None and term_info['season_code'] != target_season:
                continue
            
            if not term_data['courses']:
                continue
            
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
    
    if rows:
        fieldnames = ['planid', 'planname', 'program', 'sequencetermid', 
                     'yearnumber', 'season', 'season_code', 'courses']
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    
    return len(rows)


def display_sequence_summary(output_path: str = "Sequences.csv"):
    """Display a summary of the generated Sequences.csv file."""
    with open(output_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)


def extract_and_generate_sequences(output_path: str = "Sequences.csv",
                                   target_season: int = None,
                                   show_summary: bool = True) -> bool:
    """Main function to extract sequences from database and generate CSV."""
    try:
        num_rows = generate_sequences_csv(output_path, target_season)
        
        if show_summary:
            display_sequence_summary(output_path)
        
        return True
        
    except Exception:
        return False


if __name__ == "__main__":
    import sys
    
    target_season = None
    if len(sys.argv) > 1:
        season_arg = sys.argv[1].lower()
        if season_arg in ['fall', '2']:
            target_season = 2
        elif season_arg in ['winter', '4']:
            target_season = 4
        elif season_arg in ['summer', '6']:
            target_season = 6
    
    extract_and_generate_sequences(target_season=target_season)
