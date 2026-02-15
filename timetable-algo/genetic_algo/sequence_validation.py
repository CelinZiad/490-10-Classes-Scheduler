# sequence_validation.py
from itertools import product

def times_overlap(element1, element2):
    """Check if two course elements overlap in time."""
    if element1 is None or element2 is None:
        return False
    
    days1 = set(element1.day)
    days2 = set(element2.day)
    
    if not days1.intersection(days2):
        return False
    
    return element1.start < element2.end and element2.start < element1.end


def get_course_by_code(schedule, course_code):
    """Find a course in the schedule by its subject+catalog_nbr."""
    subject = ''.join(c for c in course_code if c.isalpha())
    catalog = ''.join(c for c in course_code if c.isdigit())
    
    for course in schedule:
        if course.subject == subject and course.catalog_nbr == catalog:
            return course
    return None


def check_elements_overlap(element, other_elements):
    """Check if an element overlaps with any element in a list."""
    for other in other_elements:
        if times_overlap(element, other):
            return True
    return False


def has_valid_sequence_combination(schedule, sequence_courses):
    """Check if there's at least one valid combination of tutorials/labs without overlaps."""
    courses = []
    for course_code in sequence_courses:
        course = get_course_by_code(schedule, course_code)
        if course is None:
            return False
        courses.append(course)
    
    all_tutorials = []
    all_labs = []
    
    for course in courses:
        if course.tutorial:
            valid_tuts = [t for t in course.tutorial if t is not None]
            if valid_tuts:
                all_tutorials.append(valid_tuts)
        
        if course.lab:
            valid_labs = [l for l in course.lab if l is not None]
            if valid_labs:
                all_labs.append(valid_labs)
    
    if not all_tutorials and not all_labs:
        return True
    
    tut_combinations = list(product(*all_tutorials)) if all_tutorials else [[]]
    lab_combinations = list(product(*all_labs)) if all_labs else [[]]
    
    for tut_combo in tut_combinations:
        tut_has_overlap = False
        for i, tut1 in enumerate(tut_combo):
            for tut2 in tut_combo[i+1:]:
                if times_overlap(tut1, tut2):
                    tut_has_overlap = True
                    break
            if tut_has_overlap:
                break
        
        if tut_has_overlap:
            continue
        
        for lab_combo in lab_combinations:
            lab_has_overlap = False
            for i, lab1 in enumerate(lab_combo):
                for lab2 in lab_combo[i+1:]:
                    if times_overlap(lab1, lab2):
                        lab_has_overlap = True
                        break
                if lab_has_overlap:
                    break
            
            if lab_has_overlap:
                continue
            
            tut_lab_overlap = False
            for tut in tut_combo:
                for lab in lab_combo:
                    if times_overlap(tut, lab):
                        tut_lab_overlap = True
                        break
                if tut_lab_overlap:
                    break
            
            if not tut_lab_overlap:
                return True
    
    return False


def validate_all_sequences(schedule, sequence):
    """Validate all semester sequences in the Sequence class."""
    results = {}
    
    for semester_idx, semester_courses in enumerate(sequence.year):
        semester_name = f"Semester {semester_idx + 1}"
        is_valid = has_valid_sequence_combination(schedule, semester_courses)
        results[semester_name] = is_valid
    
    return results
