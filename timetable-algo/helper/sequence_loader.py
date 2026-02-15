# sequence_loader.py
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
    courses: List[str]
    
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
        """Get all course lists from all terms."""
        return [term.courses for term in self.terms]
    
    def __repr__(self):
        return f"SequencePlan({self.planname}: {len(self.terms)} terms)"


class SequenceManager:
    """Manages all sequence plans loaded from CSV."""
    
    def __init__(self, csv_path: str = "Sequences.csv"):
        """Initialize by loading sequences from CSV."""
        self.plans: Dict[int, SequencePlan] = {}
        self.load_from_csv(csv_path)
    
    def load_from_csv(self, csv_path: str):
        """Load all sequences from CSV file."""
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            return
        
        plan_terms = {}
        for row in rows:
            planid = int(row['planid'])
            
            if planid not in plan_terms:
                plan_terms[planid] = {
                    'planname': row['planname'],
                    'program': row['program'],
                    'terms': []
                }
            
            courses = [c.strip() for c in row['courses'].split(',') if c.strip()]
            
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
        
        for planid, data in plan_terms.items():
            self.plans[planid] = SequencePlan(
                planid=planid,
                planname=data['planname'],
                program=data['program'],
                terms=data['terms']
            )
    
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
        """Get all course sequences from all plans (flat list of all term course lists)."""
        all_sequences = []
        for plan in self.plans.values():
            all_sequences.extend(plan.get_all_course_lists())
        return all_sequences
    
    def get_course_sequences_for_season(self, season_code: int) -> List[List[str]]:
        """Get course sequences for a specific season across all plans (2=fall, 4=winter, 6=summer)."""
        sequences = []
        for plan in self.plans.values():
            for term in plan.get_terms_for_season(season_code):
                sequences.append(term.courses)
        return sequences
    
    def display_summary(self):
        """Display a summary of all loaded sequences."""
        pass


class Sequence:
    """Backward compatibility wrapper to replace old sequence.py."""
    
    def __init__(self, csv_path: str = "Sequences.csv", season_filter: int = None):
        """Initialize sequence manager."""
        self.manager = SequenceManager(csv_path)
        self.season_filter = season_filter
        
        if season_filter:
            self.year = self.manager.get_course_sequences_for_season(season_filter)
        else:
            self.year = self.manager.get_all_course_sequences()
    
    def get_all_plans(self) -> List[SequencePlan]:
        """Get all sequence plans."""
        return self.manager.get_all_plans()
    
    def display_summary(self):
        """Display summary of loaded sequences."""
        self.manager.display_summary()


if __name__ == "__main__":
    seq = Sequence()
    seq.display_summary()
