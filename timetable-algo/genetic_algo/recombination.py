# recombination.py
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
    """Check if there's at least one valid combination of tutorials/labs without overlaps."""
    from itertools import product
    
    courses = []
    for course_code in sequence_courses:
        subject = ''.join(c for c in course_code if c.isalpha())
        catalog = ''.join(c for c in course_code if c.isdigit())
        
        for course in schedule:
            if course.subject == subject and course.catalog_nbr == catalog:
                courses.append(course)
                break
    
    if len(courses) != len(sequence_courses):
        return False
    
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
    
    tut_iter = product(*all_tutorials) if all_tutorials else iter([[]])
    lab_list = list(product(*all_labs)) if all_labs else [[]]

    for tut_combo in tut_iter:
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

        for lab_combo in lab_list:
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


def is_core_sequence_course(course, core_sequences):
    """Check if a course is part of any core sequence."""
    course_code = course.subject + course.catalog_nbr
    
    for semester_courses in core_sequences:
        if course_code in semester_courses:
            return True, semester_courses
    
    return False, None


def minimize_overlap_placement(course, offspring, core_sequence_courses, 
                               room_assignments=None, max_attempts=50):
    """Randomly place tutorials and labs with minimal overlap to other core courses."""
    best_config = None
    min_overlaps = float('inf')
    
    other_elements = []
    for other_course in offspring:
        other_code = other_course.subject + other_course.catalog_nbr
        if other_code in core_sequence_courses and other_code != (course.subject + course.catalog_nbr):
            if other_course.tutorial:
                other_elements.extend([t for t in other_course.tutorial if t is not None])
            if other_course.lab:
                other_elements.extend([l for l in other_course.lab if l is not None])
    
    room_timetable = None
    if room_assignments is not None:
        other_courses = [c for c in offspring 
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
        temp_course = deepcopy(course)
        
        insert_tut_into_timetable(temp_course)
        insert_lab_into_timetable(temp_course, room_timetable)
        
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
        
        if overlaps < min_overlaps:
            min_overlaps = overlaps
            best_config = temp_course
            
            if overlaps == 0:
                break
    
    return best_config if best_config else course


def uniform_crossover(parent1, parent2, core_sequences, crossover_rate=0.5, 
                     room_assignments=None):
    """Perform uniform crossover between two parent schedules."""
    offspring = []
    
    for i in range(len(parent1)):
        course1 = parent1[i]
        course2 = parent2[i]
        
        if course1.subject != course2.subject or course1.catalog_nbr != course2.catalog_nbr:
            raise ValueError(f"Parents have mismatched courses at index {i}")
        
        if random.random() < crossover_rate:
            selected_course = deepcopy(course1)
            backup_course = deepcopy(course2)
        else:
            selected_course = deepcopy(course2)
            backup_course = deepcopy(course1)
        
        is_core, sequence_list = is_core_sequence_course(selected_course, core_sequences)
        
        if is_core:
            temp_offspring = offspring + [selected_course]
            
            if has_valid_sequence_combination(temp_offspring, sequence_list):
                offspring.append(selected_course)
            else:
                temp_offspring = offspring + [backup_course]
                
                if has_valid_sequence_combination(temp_offspring, sequence_list):
                    offspring.append(backup_course)
                else:
                    selected_course = minimize_overlap_placement(
                        selected_course, offspring, sequence_list, room_assignments
                    )
                    offspring.append(selected_course)
        else:
            offspring.append(selected_course)
    
    return offspring
