# fitness.py
from itertools import product
from overlap_utils import times_overlap, get_course_by_code, has_valid_sequence_combination

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