# mutation.py
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
    """Check if a course has overlaps between its own components."""
    elements = []
    
    if course.lecture:
        elements.append(course.lecture)
    
    if course.tutorial:
        elements.extend([t for t in course.tutorial if t is not None])
    
    if course.lab:
        elements.extend([l for l in course.lab if l is not None])
    
    for i in range(len(elements)):
        for j in range(i + 1, len(elements)):
            if times_overlap(elements[i], elements[j]):
                return True
    
    return False


def reschedule_course_safely(course, max_attempts=100, room_assignments=None, 
                            existing_schedule=None):
    """Reschedule a course's tutorials and labs to avoid internal overlaps and room conflicts."""
    room_timetable = None
    if room_assignments is not None and existing_schedule is not None:
        other_courses = [c for c in existing_schedule 
                        if not (c.subject == course.subject and 
                               c.catalog_nbr == course.catalog_nbr and
                               c.class_nbr == course.class_nbr)]
        
        room_timetable = build_room_timetable_for_schedule(other_courses, room_assignments)
        
        from room_management import find_room_for_course
        room_info = find_room_for_course(course, room_assignments)
        if room_info is not None:
            bldg, room = room_info
            if (bldg, room) in room_timetable:
                room_timetable = {(bldg, room): room_timetable[(bldg, room)]}
            else:
                room_timetable = {(bldg, room): []}
    
    for attempt in range(max_attempts):
        new_course = deepcopy(course)
        
        if new_course.tutorial and new_course.tut_count > 0:
            insert_tut_into_timetable(new_course)
        
        if new_course.lab and new_course.lab_count > 0:
            insert_lab_into_timetable(new_course, room_timetable)
        
        if not has_internal_overlap(new_course):
            return new_course
    
    return course


def mutate(offspring, core_sequences, mutation_count=None, room_assignments=None):
    """Perform mutation on offspring by randomly rescheduling non-core courses."""
    if mutation_count is None:
        mutation_count = MUTATION_COUNT
    
    non_core_courses = []
    for i, course in enumerate(offspring):
        if not is_core_sequence_course(course, core_sequences):
            non_core_courses.append(i)
    
    num_to_mutate = min(mutation_count, len(non_core_courses))
    
    if num_to_mutate == 0:
        return offspring
    
    courses_to_mutate = random.sample(non_core_courses, num_to_mutate)
    
    mutated_offspring = []
    for i, course in enumerate(offspring):
        if i in courses_to_mutate:
            mutated_course = reschedule_course_safely(
                course, 
                room_assignments=room_assignments,
                existing_schedule=mutated_offspring
            )
            mutated_offspring.append(mutated_course)
        else:
            mutated_offspring.append(course)
    
    return mutated_offspring


def mutate_population(population, core_sequences, mutation_rate=0.1, room_assignments=None):
    """Apply mutation to multiple individuals in a population."""
    mutated_population = []
    
    for i, individual in enumerate(population):
        if random.random() < mutation_rate:
            mutated_individual = mutate(individual, core_sequences, 
                                       room_assignments=room_assignments)
            mutated_population.append(mutated_individual)
        else:
            mutated_population.append(individual)
    
    return mutated_population
