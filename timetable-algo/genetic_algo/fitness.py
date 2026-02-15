# fitness.py
from itertools import product

def calculate_variety_score(elements):
    """Calculate variety score for course elements (0-1, higher = more variety)."""
    if not elements or len(elements) <= 1:
        return 1.0
    
    valid_elements = [e for e in elements if e is not None]
    
    if len(valid_elements) <= 1:
        return 1.0
    
    n = len(valid_elements)
    
    unique_days = set()
    for element in valid_elements:
        unique_days.update(element.day)
    
    total_days = sum(len(element.day) for element in valid_elements)
    day_variety = len(unique_days) / total_days if total_days > 0 else 0
    
    unique_times = len(set(element.start for element in valid_elements))
    time_variety = unique_times / n
    
    variety_score = 0.5 * day_variety + 0.5 * time_variety
    
    return variety_score


def times_overlap(element1, element2):
    """Check if two course elements overlap in time."""
    if element1 is None or element2 is None:
        return False
    
    days1 = set(element1.day)
    days2 = set(element2.day)
    
    if not days1.intersection(days2):
        return False
    
    return element1.start < element2.end and element2.start < element1.end


def count_lecture_conflicts(course):
    """Count conflicts between course lecture and its tutorials/labs."""
    conflicts = 0
    
    if not course.lecture:
        return 0
    
    if course.tutorial:
        for tut in course.tutorial:
            if tut is not None and times_overlap(course.lecture, tut):
                conflicts += 1
    
    if course.lab:
        for lab in course.lab:
            if lab is not None and times_overlap(course.lecture, lab):
                conflicts += 1
    
    return conflicts


def get_course_by_code(schedule, course_code, class_nbr=None):
    """Find a course in the schedule by subject+catalog_nbr and optionally class_nbr."""
    subject = ''.join(c for c in course_code if c.isalpha())
    catalog = ''.join(c for c in course_code if c.isdigit())
    
    for course in schedule:
        if course.subject == subject and course.catalog_nbr == catalog:
            if class_nbr is None or course.class_nbr == class_nbr:
                return course
    return None


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


def count_sequence_conflicts(schedule, core_sequences):
    """Count the number of semester sequences with no valid combination."""
    conflicts = 0
    
    for semester_courses in core_sequences:
        if not has_valid_sequence_combination(schedule, semester_courses):
            conflicts += 1
    
    return conflicts


def fitness_function(schedule, core_sequences=None, room_assignments=None):
    """Evaluate a schedule: fitness = variety_score + (-2 * conflicts)."""
    if not schedule:
        return 0.0
    
    total_variety = 0.0
    variety_count = 0
    
    for course in schedule:
        if course.tutorial and course.tut_count > 0:
            tut_score = calculate_variety_score(course.tutorial)
            total_variety += tut_score
            variety_count += 1
        
        if course.lab and course.lab_count > 0:
            lab_score = calculate_variety_score(course.lab)
            total_variety += lab_score
            variety_count += 1
    
    variety_score = total_variety / variety_count if variety_count > 0 else 1.0
    
    total_conflicts = 0
    
    for course in schedule:
        total_conflicts += count_lecture_conflicts(course)
    
    if core_sequences:
        total_conflicts += count_sequence_conflicts(schedule, core_sequences)
    
    if room_assignments:
        from room_management import count_room_conflicts
        room_conflicts = count_room_conflicts(schedule, room_assignments)
        total_conflicts += room_conflicts
    
    fitness = variety_score + (-2 * total_conflicts)
    
    return fitness


def evaluate_population(population, core_sequences=None, room_assignments=None):
    """Evaluate all schedules in the population."""
    fitness_scores = []
    
    for i, schedule in enumerate(population):
        score = fitness_function(schedule, core_sequences, room_assignments)
        fitness_scores.append(score)
    
    return fitness_scores


def display_fitness_details(schedule, core_sequences=None, room_assignments=None):
    """Display detailed breakdown of fitness score."""
    pass


def display_schedule_structure(schedule):
    """Display the structure of a schedule."""
    pass
