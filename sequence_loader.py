# sequence_loader.py
"""
Module to load and manage multiple sequence plans from Sequences.csv.
Replaces the hardcoded sequence.py with dynamic database-driven sequences.
"""

import csv
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class SequenceTerm:
    """Represents one term in a sequence plan."""
    sequencetermid: int
    planid: int
    planname: str
    program: str
    yearnumber: int
    season: str
    season_code: int
    courses: List[str]  # List of course codes (e.g., ["COEN212", "COEN231"])
    
    def __repr__(self):
        return f"SequenceTerm(Y{self.yearnumber} {self.season}: {', '.join(self.courses[:3])}...)"


@dataclass
class SequencePlan:
    """Represents a complete sequence plan with all its terms."""
    planid: int
    planname: str
    program: str
    terms: List[SequenceTerm]
    
    def get_terms_for_season(self, season_code: int) -> List[SequenceTerm]:
        """Get all terms matching a specific season."""
        return [t for t in self.terms if t.season_code == season_code]
    
    def get_all_course_lists(self) -> List[List[str]]:
        """Get all course lists from all terms (for compatibility with old fitness function)."""
        return [term.courses for term in self.terms]
    
    def __repr__(self):
        return f"SequencePlan({self.planname}: {len(self.terms)} terms)"


class SequenceManager:
    """Manages all sequence plans loaded from CSV."""
    
    def __init__(self, csv_path: str = "Sequences.csv"):
        """
        Initialize by loading sequences from CSV.
        
        Args:
            csv_path: Path to Sequences.csv file
        """
        self.plans: Dict[int, SequencePlan] = {}
        self.load_from_csv(csv_path)
    
    def load_from_csv(self, csv_path: str):
        """Load all sequences from CSV file."""
        print(f"\nLoading sequences from {csv_path}...")
        
        # Read CSV
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            print("Warning: No sequences found in CSV")
            return
        
        # Group by planid
        plan_terms = {}
        for row in rows:
            planid = int(row['planid'])
            
            if planid not in plan_terms:
                plan_terms[planid] = {
                    'planname': row['planname'],
                    'program': row['program'],
                    'terms': []
                }
            
            # Parse courses
            courses = [c.strip() for c in row['courses'].split(',') if c.strip()]
            
            # Create term
            term = SequenceTerm(
                sequencetermid=int(row['sequencetermid']),
                planid=planid,
                planname=row['planname'],
                program=row['program'],
                yearnumber=int(row['yearnumber']),
                season=row['season'],
                season_code=int(row['season_code']),
                courses=courses
            )
            
            plan_terms[planid]['terms'].append(term)
        
        # Create SequencePlan objects
        for planid, data in plan_terms.items():
            self.plans[planid] = SequencePlan(
                planid=planid,
                planname=data['planname'],
                program=data['program'],
                terms=data['terms']
            )
        
        print(f"  Loaded {len(self.plans)} sequence plans")
        for plan in self.plans.values():
            print(f"    {plan.planname}: {len(plan.terms)} terms")
    
    def get_plan(self, planid: int) -> SequencePlan:
        """Get a specific sequence plan by ID."""
        return self.plans.get(planid)
    
    def get_all_plans(self) -> List[SequencePlan]:
        """Get all sequence plans."""
        return list(self.plans.values())
    
    def get_plans_by_program(self, program: str) -> List[SequencePlan]:
        """Get all plans for a specific program (COEN or ELEC)."""
        return [p for p in self.plans.values() if p.program.upper() == program.upper()]
    
    def get_all_course_sequences(self) -> List[List[str]]:
        """
        Get all course sequences from all plans.
        Returns a flat list of all term course lists.
        Used for compatibility with existing fitness function.
        """
        all_sequences = []
        for plan in self.plans.values():
            all_sequences.extend(plan.get_all_course_lists())
        return all_sequences
    
    def get_course_sequences_for_season(self, season_code: int) -> List[List[str]]:
        """
        Get course sequences for a specific season across all plans.
        
        Args:
            season_code: 2=fall, 4=winter, 6=summer
        
        Returns:
            List of course lists for the specified season
        """
        sequences = []
        for plan in self.plans.values():
            for term in plan.get_terms_for_season(season_code):
                sequences.append(term.courses)
        return sequences
    
    def display_summary(self):
        """Display a summary of all loaded sequences."""
        print("\n" + "=" * 70)
        print("LOADED SEQUENCE PLANS SUMMARY")
        print("=" * 70)
        
        if not self.plans:
            print("No sequence plans loaded")
            return
        
        print(f"Total plans: {len(self.plans)}")
        
        for plan in sorted(self.plans.values(), key=lambda p: p.planid):
            print(f"\n{plan.planname} (ID: {plan.planid})")
            print(f"  Program: {plan.program}")
            print(f"  Total terms: {len(plan.terms)}")
            
            # Group by season
            seasons = {}
            for term in plan.terms:
                if term.season not in seasons:
                    seasons[term.season] = []
                seasons[term.season].append(term)
            
            for season in ['fall', 'winter', 'summer']:
                if season in seasons:
                    print(f"  {season.capitalize()} terms: {len(seasons[season])}")
            
            # Show sample terms
            print(f"  Sample terms:")
            for term in plan.terms[:2]:
                print(f"    Year {term.yearnumber} {term.season}: {', '.join(term.courses[:4])}...")
        
        print("=" * 70)


# Backward compatibility: create a Sequence-like object
class Sequence:
    """
    Backward compatibility wrapper to replace old sequence.py.
    Now loads from database-generated CSV instead of hardcoded values.
    """
    
    def __init__(self, csv_path: str = "Sequences.csv", season_filter: int = None):
        """
        Initialize sequence manager.
        
        Args:
            csv_path: Path to Sequences.csv
            season_filter: Optional season code to filter (2=fall, 4=winter)
        """
        self.manager = SequenceManager(csv_path)
        self.season_filter = season_filter
        
        # For backward compatibility: provide 'year' attribute
        # This contains all course sequences (list of lists)
        if season_filter:
            self.year = self.manager.get_course_sequences_for_season(season_filter)
        else:
            self.year = self.manager.get_all_course_sequences()
        
        print(f"\nSequence initialized with {len(self.year)} terms")
        if season_filter:
            season_name = {2: 'Fall', 4: 'Winter', 6: 'Summer'}.get(season_filter, 'Unknown')
            print(f"Filtered for: {season_name} term")
    
    def get_all_plans(self) -> List[SequencePlan]:
        """Get all sequence plans."""
        return self.manager.get_all_plans()
    
    def display_summary(self):
        """Display summary of loaded sequences."""
        self.manager.display_summary()


# Usage example:
if __name__ == "__main__":
    # Load all sequences
    seq = Sequence()
    seq.display_summary()
    
    print(f"\nTotal course sequences: {len(seq.year)}")
    print("Sample sequences:")
    for i, courses in enumerate(seq.year[:3]):
        print(f"  Sequence {i+1}: {courses}")
