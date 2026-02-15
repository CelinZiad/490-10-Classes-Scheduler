# main.py
import csv
from initialization import initialize_course_with_validation
from course import Course
from typing import List
from config import (POPULATION_SIZE, MUTATION_COUNT, 
                    LIMIT_POPULATION_GENERATION, LIMIT_FITTEST_UNCHANGED_GENERATION,
                    FITNESS_RATIO_THRESHOLD, TARGET_SEASON, ACADEMIC_YEAR)
from copy import deepcopy
from fitness import evaluate_population, fitness_function, display_fitness_details, display_schedule_structure
from sequence_loader import Sequence
from sequence_validation import has_valid_sequence_combination
from parent_selection import select_parents
from recombination import uniform_crossover
from mutation import mutate
from replacement import replace_worst_individuals, display_replacement_summary
from termination import (should_terminate, display_termination_status, 
                        display_final_statistics)
from room_management import load_room_assignments, create_room_timetables, display_room_timetable, validate_room_timetables
from export_utils import export_fittest_individual, display_export_summary
from conflict_export import export_conflicts_csv
from scheduleterm_export import export_to_scheduleterm_format
from db_room_extractor import extract_and_generate_room_data
from db_sequence_extractor import extract_and_generate_sequences
from db_course_extractor import extract_and_generate_course_data

def should_include_course(subject: str, catalog: str) -> bool:
    """
    Determine if a course should be included in scheduling.
    
    Include only:
    - COEN courses
    - ELEC courses  
    - ENGR 290
    """
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
        for i, row in enumerate(reader, start=2):  # line 1 is header, so data starts at 2
            try:
                # Check if course should be included
                subject = row.get('subject', '').strip()
                catalog = row.get('catalog_nbr', '').strip()
                
                if not should_include_course(subject, catalog):
                    filtered_count += 1
                    continue
                
                courses.append(Course.from_csv_row(row))
            except Exception as e:
                raise ValueError(f"Error parsing CSV at line {i}: {e}\nRow={row}") from e
    
    if filtered_count > 0:
        print(f"  Filtered out {filtered_count} non-COEN/ELEC/ENGR290 courses")
    
    return courses


def initialize_population(courses: List[Course], population_size: int, 
                           room_assignments=None) -> List[List[Course]]:
    """Initialize the population with random valid schedules."""
    population: List[List[Course]] = []
    
    print(f"\n=== Initializing Population (Size: {population_size}) ===")
    for i in range(population_size):
        individual = []
        for c in courses:
            course_copy = deepcopy(c)
            # Pass room_assignments and existing schedule for room conflict checking
            if not initialize_course_with_validation(course_copy, 
                                                     room_assignments=room_assignments,
                                                     existing_schedule=individual):
                print(f"Warning: Could not find valid schedule for {c.subject} {c.catalog_nbr} (class_nbr: {c.class_nbr})")
            individual.append(course_copy)
        population.append(individual)
        print(f"Individual {i + 1}/{population_size} initialized")
    
    return population


def run_one_generation(population: List[List[Course]], 
                       fitness_scores: List[float],
                       seq: Sequence,
                       room_assignments,
                       num_offspring: int = 2) -> tuple[List[List[Course]], List[float]]:
    """
    Run one generation of the genetic algorithm.
    
    Returns:
        Tuple of (new_population, new_fitness_scores)
    """
    offspring_list = []
    
    # Generate offspring
    for _ in range(num_offspring):
        # Select parents
        parent_indices = select_parents(fitness_scores, num_parents=2)
        parent1 = population[parent_indices[0]]
        parent2 = population[parent_indices[1]]
        
        # Crossover
        offspring = uniform_crossover(
            parent1=parent1,
            parent2=parent2,
            core_sequences=seq.year,
            crossover_rate=0.5,
            room_assignments=room_assignments
        )
        
        # Mutation
        mutated = mutate(
            offspring=offspring,
            core_sequences=seq.year,
            mutation_count=MUTATION_COUNT,
            room_assignments=room_assignments
        )
        
        offspring_list.append(mutated)
    
    # Evaluate offspring (now including room conflicts)
    offspring_fitness = [fitness_function(off, core_sequences=seq.year, room_assignments=room_assignments) 
                        for off in offspring_list]
    
    # Replace worst individuals
    new_population, new_fitness_scores = replace_worst_individuals(
        population, fitness_scores, offspring_list, offspring_fitness
    )
    
    return new_population, new_fitness_scores


if __name__ == "__main__":
    # Determine season name for display
    season_name = {2: 'FALL', 4: 'WINTER', 6: 'SUMMER'}.get(TARGET_SEASON, 'UNKNOWN')
    
    print("\n" + "=" * 70)
    print(f"TIMETABLE GENERATION FOR {season_name} TERM (Season Code: {TARGET_SEASON})")
    print("=" * 70)
    
    # Extract sequence data from database
    print("\n" + "=" * 70)
    print("STEP 1: EXTRACTING SEQUENCE DATA FROM DATABASE")
    print("=" * 70)
    
    if not extract_and_generate_sequences("Sequences.csv", 
                                          target_season=TARGET_SEASON, 
                                          show_summary=True):
        print("\n✗ Failed to extract sequence data from database")
        print("Please check database connection and try again")
        exit(1)
    
    # Extract room data from database
    print("\n" + "=" * 70)
    print("STEP 2: EXTRACTING ROOM DATA FROM DATABASE")
    print("=" * 70)
    
    if not extract_and_generate_room_data("Room_data.csv", show_summary=True):
        print("\n✗ Failed to extract room data from database")
        print("Please check database connection and try again")
        exit(1)
    
    # Extract course data from database
    print("\n" + "=" * 70)
    print("STEP 3: EXTRACTING COURSE SCHEDULE DATA FROM DATABASE")
    print("=" * 70)
    
    if not extract_and_generate_course_data("Data.csv", 
                                            year=ACADEMIC_YEAR,
                                            season_code=TARGET_SEASON,
                                            show_summary=True):
        print("\n✗ Failed to extract course data from database")
        print("Please check database connection and try again")
        exit(1)
    
    # Read course data
    print("\n" + "=" * 70)
    print("STEP 4: LOADING COURSE DATA")
    print("=" * 70)
    courses = read_courses_from_csv("Data.csv")
    print(f"Loaded {len(courses)} courses from Data.csv")
    
    # Load room assignments
    print("\n" + "=" * 70)
    print("STEP 5: LOADING ROOM ASSIGNMENTS")
    print("=" * 70)
    room_assignments = load_room_assignments("Room_data.csv")
    print(f"Loaded {len(room_assignments)} room assignments")
    
    # Initialize population
    population = initialize_population(courses, POPULATION_SIZE, room_assignments)
    
    # Assign rooms to labs in initial population
    print("\n=== Assigning Rooms to Labs ===")
    for i, individual in enumerate(population):
        timetables = create_room_timetables(individual, room_assignments)
        print(f"Individual {i+1}: Created timetables for {len(timetables)} rooms")
    
    # Create sequence object with season filter
    print("\n" + "=" * 70)
    print("STEP 6: LOADING SEQUENCE PLANS")
    print("=" * 70)
    seq = Sequence("Sequences.csv", season_filter=TARGET_SEASON)
    seq.display_summary()
    
    # Display schedule structure to verify class_nbr handling
    print("\n=== Verifying Schedule Structure (class_nbr handling) ===")
    display_schedule_structure(population[0])
    
    # Validate initial population
    print("\n=== Validating Initial Population ===")
    for i, individual in enumerate(population):
        print(f"\nIndividual {i + 1}:")
        for semester_idx, semester_courses in enumerate(seq.year):
            is_valid = has_valid_sequence_combination(individual, semester_courses)
            print(f"  Semester {semester_idx + 1} {semester_courses}: {'Valid' if is_valid else 'INVALID'}")
    
    # Evaluate initial population (with room conflicts)
    print("\n=== Evaluating Initial Population (with Room Conflicts) ===")
    fitness_scores = []
    for i, individual in enumerate(population):
        score = fitness_function(individual, core_sequences=seq.year, room_assignments=room_assignments)
        fitness_scores.append(score)
        print(f"Individual {i + 1}: Fitness = {score:.4f}")
    
    # Track fitness history for termination
    fitness_history = []
    best_fitness = max(fitness_scores)
    fitness_history.append(best_fitness)
    
    print(f"\nInitial Best Fitness: {best_fitness:.4f}")
    
    # Evolution loop
    current_generation = 0
    num_offspring = 2  # Number of offspring per generation
    
    print("\n" + "=" * 70)
    print("STARTING GENETIC ALGORITHM EVOLUTION")
    print("=" * 70)
    
    while True:
        current_generation += 1
        
        print(f"\n{'='*70}")
        print(f"GENERATION {current_generation}")
        print(f"{'='*70}")
        
        # Run one generation
        population, fitness_scores = run_one_generation(
            population, fitness_scores, seq, room_assignments, num_offspring
        )
        
        # Track best fitness
        best_fitness = max(fitness_scores)
        fitness_history.append(best_fitness)
        
        print(f"\nGeneration {current_generation} Complete:")
        print(f"  Best Fitness: {best_fitness:.4f}")
        print(f"  Mean Fitness: {sum(fitness_scores) / len(fitness_scores):.4f}")
        print(f"  Worst Fitness: {min(fitness_scores):.4f}")
        
        # Display termination status every 5 generations
        if current_generation % 5 == 0:
            display_termination_status(
                current_generation=current_generation,
                fitness_scores=fitness_scores,
                fitness_history=fitness_history,
                max_generations=LIMIT_POPULATION_GENERATION,
                unchanged_limit=LIMIT_FITTEST_UNCHANGED_GENERATION,
                ratio_threshold=FITNESS_RATIO_THRESHOLD
            )
        
        # Check termination conditions
        terminate, reason = should_terminate(
            current_generation=current_generation,
            fitness_scores=fitness_scores,
            fitness_history=fitness_history,
            max_generations=LIMIT_POPULATION_GENERATION,
            unchanged_limit=LIMIT_FITTEST_UNCHANGED_GENERATION,
            ratio_threshold=FITNESS_RATIO_THRESHOLD
        )
        
        if terminate:
            print(f"\n{'='*70}")
            print(f"TERMINATION TRIGGERED")
            print(f"{'='*70}")
            display_final_statistics(fitness_history, current_generation, reason)
            break
    
    # Display final best schedule
    best_idx = fitness_scores.index(max(fitness_scores))
    print(f"\n{'='*70}")
    print(f"FINAL BEST SCHEDULE (Individual {best_idx + 1})")
    print(f"{'='*70}")
    display_fitness_details(population[best_idx], core_sequences=seq.year, room_assignments=room_assignments)
    
    # Validate final best schedule
    print(f"\n{'='*70}")
    print("FINAL VALIDATION")
    print(f"{'='*70}")
    for semester_idx, semester_courses in enumerate(seq.year):
        is_valid = has_valid_sequence_combination(population[best_idx], semester_courses)
        status = "✓ Valid" if is_valid else "✗ INVALID"
        print(f"Semester {semester_idx + 1} {semester_courses}: {status}")
    
    # Display room timetables for best individual
    print(f"\n{'='*70}")
    print("ROOM TIMETABLES FOR BEST INDIVIDUAL")
    print(f"{'='*70}")
    best_timetables = create_room_timetables(population[best_idx], room_assignments)
    
    # Validate room timetables
    is_valid = validate_room_timetables(best_timetables)
    if is_valid:
        print("✓ All room timetables are valid (no conflicts)")
    else:
        print("✗ Room conflicts detected")
    
    # Display a few room timetables as examples
    print("\nSample Room Timetables:")
    for i, ((bldg, room), timetable) in enumerate(best_timetables.items()):
        if i < 3:  # Show first 3 rooms
            display_room_timetable(timetable)
    
    # Export results to CSV
    print(f"\n{'='*70}")
    print("EXPORTING RESULTS")
    print(f"{'='*70}")
    
    display_export_summary(population[best_idx], "Room_data.csv")
    
    export_fittest_individual(
        schedule=population[best_idx],
        room_assignments_path="Room_data.csv",
        course_output_path="best_course_timetable.csv",
        room_output_path="best_room_timetable.csv"
    )
    
    # Export conflicts
    print(f"\n{'='*70}")
    print("EXPORTING CONFLICTS")
    print(f"{'='*70}")
    
    num_conflicts = export_conflicts_csv(
        schedule=population[best_idx],
        core_sequences=seq.year,
        room_assignments=room_assignments,
        output_path="conflicts.csv"
    )
    
    # Export to database
    print(f"\n{'='*70}")
    print("DATABASE EXPORT (SCHEDULETERM FORMAT)")
    print(f"{'='*70}")
    
    try:
        print(f"Academic year: {ACADEMIC_YEAR}, Season: {TARGET_SEASON}")
        print(f"Schedule has {len(population[best_idx])} courses")
        
        success = export_to_scheduleterm_format(
            schedule=population[best_idx],
            room_assignments=room_assignments,
            year=ACADEMIC_YEAR,
            season=TARGET_SEASON
        )
        
        if success:
            print("\n✓ Database export completed")
        else:
            print("\n✗ Database export failed")
    except Exception as e:
        print(f"\n✗ Database export error: {e}")
        import traceback
        traceback.print_exc()
    
    # Files have been generated
    print("\nGenerated files:")
    print("  - best_course_timetable.csv")
    print("  - best_room_timetable.csv")
    print("  - conflicts.csv")
    
    print(f"\n{'='*70}")
    print("GENETIC ALGORITHM COMPLETE")
    print(f"{'='*70}")
    print(f"Best fitness: {max(fitness_scores):.4f}")
    print("Course timetable saved to: best_course_timetable.csv")
    print("Room timetable saved to: best_room_timetable.csv")
    print(f"Conflicts saved to: conflicts.csv ({num_conflicts} conflicts)")
    print(f"{'='*70}")
