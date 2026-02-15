# main.py
import sys
import os
from pathlib import Path

# Add parent directory to path to access helper module
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

import csv
from initialization import initialize_course_with_validation
from course import Course
from typing import List
from config import (POPULATION_SIZE, MUTATION_COUNT, 
                    LIMIT_POPULATION_GENERATION, LIMIT_FITTEST_UNCHANGED_GENERATION,
                    FITNESS_RATIO_THRESHOLD, TARGET_SEASON, ACADEMIC_YEAR)
from copy import deepcopy
from fitness import evaluate_population, fitness_function, display_fitness_details, display_schedule_structure
from helper.sequence_loader import Sequence
from sequence_validation import has_valid_sequence_combination
from parent_selection import select_parents
from recombination import uniform_crossover
from mutation import mutate
from replacement import replace_worst_individuals, display_replacement_summary
from termination import (should_terminate, display_termination_status, 
                        display_final_statistics)
from room_management import load_room_assignments, create_room_timetables, display_room_timetable, validate_room_timetables
from helper.export_utils import export_fittest_individual, display_export_summary
from helper.conflict_export import export_conflicts_csv
from helper.scheduleterm_export import export_to_scheduleterm_format
from helper.db_room_extractor import extract_and_generate_room_data
from helper.db_sequence_extractor import extract_and_generate_sequences
from helper.db_course_extractor import extract_and_generate_course_data

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


def read_courses_from_csv(path: str) -> List[Course]:
    """Read courses from CSV file and return list of Course objects (filtered)."""
    courses: List[Course] = []
    filtered_count = 0
    
    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            try:
                subject = row.get('subject', '').strip()
                catalog = row.get('catalog_nbr', '').strip()
                
                if not should_include_course(subject, catalog):
                    filtered_count += 1
                    continue
                
                courses.append(Course.from_csv_row(row))
            except Exception as e:
                raise ValueError(f"Error parsing CSV at line {i}: {e}\nRow={row}") from e
    
    return courses


def initialize_population(courses: List[Course], population_size: int, 
                           room_assignments=None) -> List[List[Course]]:
    """Initialize the population with random valid schedules."""
    population: List[List[Course]] = []
    
    for i in range(population_size):
        individual = []
        for c in courses:
            course_copy = deepcopy(c)
            if not initialize_course_with_validation(course_copy, 
                                                     room_assignments=room_assignments,
                                                     existing_schedule=individual):
                pass
            individual.append(course_copy)
        population.append(individual)
    
    return population


def run_one_generation(population: List[List[Course]], 
                       fitness_scores: List[float],
                       seq: Sequence,
                       room_assignments,
                       num_offspring: int = 2) -> tuple[List[List[Course]], List[float]]:
    """Run one generation of the genetic algorithm."""
    offspring_list = []
    
    for _ in range(num_offspring):
        parent_indices = select_parents(fitness_scores, num_parents=2)
        parent1 = population[parent_indices[0]]
        parent2 = population[parent_indices[1]]
        
        offspring = uniform_crossover(
            parent1=parent1,
            parent2=parent2,
            core_sequences=seq.year,
            crossover_rate=0.5,
            room_assignments=room_assignments
        )
        
        mutated = mutate(
            offspring=offspring,
            core_sequences=seq.year,
            mutation_count=MUTATION_COUNT,
            room_assignments=room_assignments
        )
        
        offspring_list.append(mutated)
    
    offspring_fitness = [fitness_function(off, core_sequences=seq.year, room_assignments=room_assignments) 
                        for off in offspring_list]
    
    new_population, new_fitness_scores = replace_worst_individuals(
        population, fitness_scores, offspring_list, offspring_fitness
    )
    
    return new_population, new_fitness_scores


if __name__ == "__main__":
    extract_and_generate_sequences("Sequences.csv", 
                                   target_season=TARGET_SEASON, 
                                   show_summary=True)
    
    extract_and_generate_room_data("Room_data.csv", show_summary=True)
    
    extract_and_generate_course_data("Data.csv", 
                                     year=ACADEMIC_YEAR,
                                     season_code=TARGET_SEASON,
                                     show_summary=True)
    
    courses = read_courses_from_csv("Data.csv")
    room_assignments = load_room_assignments("Room_data.csv")
    population = initialize_population(courses, POPULATION_SIZE, room_assignments)
    
    for i, individual in enumerate(population):
        timetables = create_room_timetables(individual, room_assignments)
    
    seq = Sequence("Sequences.csv", season_filter=TARGET_SEASON)
    seq.display_summary()
    
    display_schedule_structure(population[0])
    
    for i, individual in enumerate(population):
        for semester_idx, semester_courses in enumerate(seq.year):
            is_valid = has_valid_sequence_combination(individual, semester_courses)
    
    fitness_scores = []
    for i, individual in enumerate(population):
        score = fitness_function(individual, core_sequences=seq.year, room_assignments=room_assignments)
        fitness_scores.append(score)
    
    fitness_history = []
    best_fitness = max(fitness_scores)
    fitness_history.append(best_fitness)
    
    current_generation = 0
    num_offspring = 2
    
    while True:
        current_generation += 1
        
        population, fitness_scores = run_one_generation(
            population, fitness_scores, seq, room_assignments, num_offspring
        )
        
        best_fitness = max(fitness_scores)
        fitness_history.append(best_fitness)
        
        if current_generation % 5 == 0:
            display_termination_status(
                current_generation=current_generation,
                fitness_scores=fitness_scores,
                fitness_history=fitness_history,
                max_generations=LIMIT_POPULATION_GENERATION,
                unchanged_limit=LIMIT_FITTEST_UNCHANGED_GENERATION,
                ratio_threshold=FITNESS_RATIO_THRESHOLD
            )
        
        terminate, reason = should_terminate(
            current_generation=current_generation,
            fitness_scores=fitness_scores,
            fitness_history=fitness_history,
            max_generations=LIMIT_POPULATION_GENERATION,
            unchanged_limit=LIMIT_FITTEST_UNCHANGED_GENERATION,
            ratio_threshold=FITNESS_RATIO_THRESHOLD
        )
        
        if terminate:
            display_final_statistics(fitness_history, current_generation, reason)
            break
    
    best_idx = fitness_scores.index(max(fitness_scores))
    display_fitness_details(population[best_idx], core_sequences=seq.year, room_assignments=room_assignments)
    
    for semester_idx, semester_courses in enumerate(seq.year):
        is_valid = has_valid_sequence_combination(population[best_idx], semester_courses)
    
    best_timetables = create_room_timetables(population[best_idx], room_assignments)
    is_valid = validate_room_timetables(best_timetables)
    
    for i, ((bldg, room), timetable) in enumerate(best_timetables.items()):
        if i < 3:
            display_room_timetable(timetable)
    
    display_export_summary(population[best_idx], "Room_data.csv")
    
    export_fittest_individual(
        schedule=population[best_idx],
        room_assignments_path="Room_data.csv",
        course_output_path="best_course_timetable.csv",
        room_output_path="best_room_timetable.csv"
    )
    
    num_conflicts = export_conflicts_csv(
        schedule=population[best_idx],
        core_sequences=seq.year,
        room_assignments=room_assignments,
        output_path="conflicts.csv"
    )
    
    try:
        success = export_to_scheduleterm_format(
            schedule=population[best_idx],
            room_assignments=room_assignments,
            year=ACADEMIC_YEAR,
            season=TARGET_SEASON
        )
    except Exception:
        pass

