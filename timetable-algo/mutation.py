import random
from copy import deepcopy
from typing import List, Optional
from course import Course
from initialization import (insert_tut_into_timetable, insert_lab_into_timetable, 
                           build_room_timetable_for_schedule, find_conflict_free_lab_slot)
from config import MUTATION_COUNT

def times_overlap(element1, element2):
    """Check if two course elements overlap in time."""
    if element1 is None or element2 is None:
        return False
    
    days1 = set(element1.day)
    days2 = set(element2.day)
    
    if not days1.intersection(days2):
        return False
    
    return element1.start < element2.end and element2.start < element1.end


def is_core_sequence_course(course, core_sequences):
    """Check if a course is part of any core sequence."""
    course_code = course.subject + course.catalog_nbr
    
    for semester_courses in core_sequences:
        if course_code in semester_courses:
            return True
    
    return False


def has_internal_overlap(course):
    """
    Check if a course has overlaps between its own components:
    - Tutorial vs Tutorial
    - Lab vs Lab
    - Tutorial vs Lab
    - Tutorial/Lab vs Lecture
    """
    elements = []
    
    # Collect all elements
    if course.lecture:
        elements.append(course.lecture)
    
    if course.tutorial:
        elements.extend([t for t in course.tutorial if t is not None])
    
    if course.lab:
        elements.extend([l for l in course.lab if l is not None])
    
    # Check all pairs for overlap
    for i in range(len(elements)):
        for j in range(i + 1, len(elements)):
            if times_overlap(elements[i], elements[j]):
                return True
    
    return False


def reschedule_course_safely(course, max_attempts=100, room_assignments=None, 
                            existing_schedule=None):
    """
    Reschedule a course's tutorials and labs to avoid internal overlaps and room conflicts.
    
    Args:
        course: Course object to reschedule
        max_attempts: Maximum number of attempts to find valid schedule
        room_assignments: Optional list of RoomAssignment objects for room conflict checking
        existing_schedule: Optional list of other courses already scheduled
    
    Returns:
        New Course object with rescheduled tutorials/labs, or original if failed
    """
    # Build room timetable from existing schedule (excluding this course)
    room_timetable = None
    if room_assignments is not None and existing_schedule is not None:
        # Exclude the current course from the schedule
        other_courses = [c for c in existing_schedule 
                        if not (c.subject == course.subject and 
                               c.catalog_nbr == course.catalog_nbr and
                               c.class_nbr == course.class_nbr)]
        
        room_timetable = build_room_timetable_for_schedule(other_courses, room_assignments)
        
        # Filter to only this course's room
        from room_management import find_room_for_course
        room_info = find_room_for_course(course, room_assignments)
        if room_info is not None:
            bldg, room = room_info
            if (bldg, room) in room_timetable:
                room_timetable = {(bldg, room): room_timetable[(bldg, room)]}
            else:
                room_timetable = {(bldg, room): []}
    
    for attempt in range(max_attempts):
        # Create a deep copy to modify
        new_course = deepcopy(course)
        
        # Reschedule tutorials and labs
        if new_course.tutorial and new_course.tut_count > 0:
            insert_tut_into_timetable(new_course)
        
        if new_course.lab and new_course.lab_count > 0:
            insert_lab_into_timetable(new_course, room_timetable)
        
        # Check if this configuration is valid (no internal overlaps)
        if not has_internal_overlap(new_course):
            return new_course
    
    # If we couldn't find a valid schedule, return the original
    print(f"Warning: Could not reschedule {course.subject} {course.catalog_nbr} without overlaps")
    return course


def mutate(offspring, core_sequences, mutation_count=None, room_assignments=None):
    """
    Perform mutation on offspring by randomly rescheduling non-core courses.
    Now includes room conflict avoidance.
    
    Args:
        offspring: List of Course objects (the offspring to mutate)
        core_sequences: List of lists of course codes (e.g., Sequence.year)
        mutation_count: Number of courses to mutate (uses MUTATION_COUNT from config if None)
        room_assignments: Optional list of RoomAssignment objects for room conflict checking
    
    Returns:
        Mutated offspring (list of Course objects)
    """
    if mutation_count is None:
        mutation_count = MUTATION_COUNT
    
    # Identify non-core sequence courses
    non_core_courses = []
    for i, course in enumerate(offspring):
        if not is_core_sequence_course(course, core_sequences):
            non_core_courses.append(i)
    
    # If there are fewer non-core courses than mutation_count, mutate all of them
    num_to_mutate = min(mutation_count, len(non_core_courses))
    
    if num_to_mutate == 0:
        print("Warning: No non-core courses available for mutation")
        return offspring
    
    # Randomly select which non-core courses to mutate
    courses_to_mutate = random.sample(non_core_courses, num_to_mutate)
    
    # Create mutated offspring
    mutated_offspring = []
    for i, course in enumerate(offspring):
        if i in courses_to_mutate:
            # Reschedule this course with room conflict checking
            mutated_course = reschedule_course_safely(
                course, 
                room_assignments=room_assignments,
                existing_schedule=mutated_offspring  # Courses already processed
            )
            mutated_offspring.append(mutated_course)
            print(f"Mutated: {course.subject} {course.catalog_nbr}")
        else:
            # Keep original
            mutated_offspring.append(course)
    
    return mutated_offspring


def mutate_population(population, core_sequences, mutation_rate=0.1, room_assignments=None):
    """
    Apply mutation to multiple individuals in a population.
    
    Args:
        population: List of schedules (each schedule is a list of Course objects)
        core_sequences: List of lists of course codes
        mutation_rate: Probability that an individual gets mutated (0 to 1)
        room_assignments: Optional list of RoomAssignment objects
    
    Returns:
        Mutated population
    """
    mutated_population = []
    
    for i, individual in enumerate(population):
        if random.random() < mutation_rate:
            print(f"\n--- Mutating individual {i + 1} ---")
            mutated_individual = mutate(individual, core_sequences, 
                                       room_assignments=room_assignments)
            mutated_population.append(mutated_individual)
        else:
            mutated_population.append(individual)
    
    return mutated_population


# Usage example:
# from sequence import Sequence
# from config import MUTATION_COUNT
# from room_management import load_room_assignments
# 
# seq = Sequence()
# room_assignments = load_room_assignments("Room_data.csv")
# 
# # Mutate a single offspring with room conflict checking
# mutated_offspring = mutate(
#     offspring=offspring,
#     core_sequences=seq.year,
#     room_assignments=room_assignments
# )
# 
# # Or mutate entire population with a mutation rate
# new_population = mutate_population(
#     population=population,
#     core_sequences=seq.year,
#     mutation_rate=0.1,
#     room_assignments=room_assignments
# )
