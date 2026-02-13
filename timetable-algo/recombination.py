import random
from copy import deepcopy
from typing import List, Optional
from course import Course
from initialization import (insert_tut_into_timetable, insert_lab_into_timetable,
                           build_room_timetable_for_schedule)

def times_overlap(element1, element2):
    """Check if two course elements overlap in time."""
    if element1 is None or element2 is None:
        return False
    
    days1 = set(element1.day)
    days2 = set(element2.day)
    
    if not days1.intersection(days2):
        return False
    
    return element1.start < element2.end and element2.start < element1.end


def has_valid_sequence_combination(schedule, sequence_courses):
    """
    Check if there's at least one valid combination of tutorials and labs
    for a sequence of courses without any overlaps.
    """
    from itertools import product
    
    # Get courses by their subject+catalog_nbr
    courses = []
    for course_code in sequence_courses:
        subject = ''.join(c for c in course_code if c.isalpha())
        catalog = ''.join(c for c in course_code if c.isdigit())
        
        for course in schedule:
            if course.subject == subject and course.catalog_nbr == catalog:
                courses.append(course)
                break
    
    if len(courses) != len(sequence_courses):
        return False  # Not all courses found
    
    # Collect all tutorials and labs
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
    
    # Generate all combinations
    tut_combinations = list(product(*all_tutorials)) if all_tutorials else [[]]
    lab_combinations = list(product(*all_labs)) if all_labs else [[]]
    
    # Check each combination
    for tut_combo in tut_combinations:
        # Check tutorial overlaps
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
            # Check lab overlaps
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
            
            # Check tutorial-lab overlaps
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


def is_core_sequence_course(course, core_sequences):
    """
    Check if a course is part of any core sequence.
    
    Args:
        course: Course object
        core_sequences: List of lists of course codes (e.g., Sequence.year)
    
    Returns:
        Tuple (is_core, sequence_list) where sequence_list is the semester courses if core
    """
    course_code = course.subject + course.catalog_nbr
    
    for semester_courses in core_sequences:
        if course_code in semester_courses:
            return True, semester_courses
    
    return False, None


def minimize_overlap_placement(course, offspring, core_sequence_courses, 
                               room_assignments=None, max_attempts=50):
    """
    Randomly place tutorials and labs with minimal overlap to other core courses
    and avoiding room conflicts.
    
    Args:
        course: Course to place
        offspring: Current offspring schedule (for checking overlaps)
        core_sequence_courses: List of course codes in this sequence
        room_assignments: Optional room assignments for conflict checking
        max_attempts: Maximum attempts to find good placement
    
    Returns:
        Course object with optimized placement
    """
    best_config = None
    min_overlaps = float('inf')
    
    # Get all tutorials and labs from other core sequence courses
    other_elements = []
    for other_course in offspring:
        other_code = other_course.subject + other_course.catalog_nbr
        if other_code in core_sequence_courses and other_code != (course.subject + course.catalog_nbr):
            if other_course.tutorial:
                other_elements.extend([t for t in other_course.tutorial if t is not None])
            if other_course.lab:
                other_elements.extend([l for l in other_course.lab if l is not None])
    
    # Build room timetable from offspring (excluding this course)
    room_timetable = None
    if room_assignments is not None:
        other_courses = [c for c in offspring 
                        if not (c.subject == course.subject and 
                               c.catalog_nbr == course.catalog_nbr and
                               c.class_nbr == course.class_nbr)]
        room_timetable = build_room_timetable_for_schedule(other_courses, room_assignments)
        
        # Filter to this course's room
        from room_management import find_room_for_course
        room_info = find_room_for_course(course, room_assignments)
        if room_info is not None:
            bldg, room = room_info
            if (bldg, room) in room_timetable:
                room_timetable = {(bldg, room): room_timetable[(bldg, room)]}
            else:
                room_timetable = {(bldg, room): []}
    
    for attempt in range(max_attempts):
        # Create temporary copy
        temp_course = deepcopy(course)
        
        # Randomly assign times
        insert_tut_into_timetable(temp_course)
        insert_lab_into_timetable(temp_course, room_timetable)
        
        # Count overlaps with other core courses
        overlaps = 0
        for tut in temp_course.tutorial:
            if tut:
                for other in other_elements:
                    if times_overlap(tut, other):
                        overlaps += 1
        
        for lab in temp_course.lab:
            if lab:
                for other in other_elements:
                    if times_overlap(lab, other):
                        overlaps += 1
        
        # Keep best configuration
        if overlaps < min_overlaps:
            min_overlaps = overlaps
            best_config = temp_course
            
            if overlaps == 0:
                break  # Found perfect solution
    
    # Return the best configuration
    return best_config if best_config else course


def uniform_crossover(parent1, parent2, core_sequences, crossover_rate=0.5, 
                     room_assignments=None):
    """
    Perform uniform crossover between two parent schedules.
    Now includes room conflict avoidance.
    
    Args:
        parent1: List of Course objects (first parent)
        parent2: List of Course objects (second parent)
        core_sequences: List of lists of course codes (e.g., Sequence.year)
        crossover_rate: Probability of selecting from parent1 (default 0.5)
        room_assignments: Optional list of RoomAssignment objects
    
    Returns:
        Offspring schedule (list of Course objects)
    """
    offspring = []
    
    # Assume both parents have courses in the same order
    for i in range(len(parent1)):
        course1 = parent1[i]
        course2 = parent2[i]
        
        # Verify same course
        if course1.subject != course2.subject or course1.catalog_nbr != course2.catalog_nbr:
            raise ValueError(f"Parents have mismatched courses at index {i}")
        
        # Randomly select which parent to inherit from
        if random.random() < crossover_rate:
            selected_course = deepcopy(course1)
            backup_course = deepcopy(course2)
        else:
            selected_course = deepcopy(course2)
            backup_course = deepcopy(course1)
        
        # Check if this is a core sequence course
        is_core, sequence_list = is_core_sequence_course(selected_course, core_sequences)
        
        if is_core:
            # Create temporary offspring to test
            temp_offspring = offspring + [selected_course]
            
            # Check if valid combination exists
            if has_valid_sequence_combination(temp_offspring, sequence_list):
                offspring.append(selected_course)
            else:
                # Try backup parent
                temp_offspring = offspring + [backup_course]
                
                if has_valid_sequence_combination(temp_offspring, sequence_list):
                    offspring.append(backup_course)
                else:
                    # Last resort: minimize overlaps with room conflict checking
                    selected_course = minimize_overlap_placement(
                        selected_course, offspring, sequence_list, room_assignments
                    )
                    offspring.append(selected_course)
        else:
            # Not a core course, just add it
            offspring.append(selected_course)
    
    return offspring


# Usage example:
# from sequence import Sequence
# from room_management import load_room_assignments
# 
# seq = Sequence()
# room_assignments = load_room_assignments("Room_data.csv")
# 
# # Perform crossover with room conflict checking
# offspring = uniform_crossover(
#     parent1=population[0],
#     parent2=population[1],
#     core_sequences=seq.year,
#     crossover_rate=0.5,
#     room_assignments=room_assignments
# )
# 
# # Verify the offspring
# for semester_courses in seq.year:
#     is_valid = has_valid_sequence_combination(offspring, semester_courses)
#     print(f"Semester {semester_courses}: Valid = {is_valid}")
