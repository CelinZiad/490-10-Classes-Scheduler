"""Wrapper around the genetic algorithm for use by the Flask app."""

import csv
import os
import sys
import time
from copy import deepcopy
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
ALGO_DIR = PROJECT_ROOT / "timetable-algo"
GENETIC_DIR = ALGO_DIR / "genetic_algo"


def _read_csv_file(path: str) -> list[dict]:
    """Read a CSV file and return rows as list of dicts."""
    if not os.path.isfile(path):
        return []
    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def get_schedule_csv_path() -> str:
    return str(GENETIC_DIR / "best_course_timetable.csv")


def get_conflicts_csv_path() -> str:
    return str(GENETIC_DIR / "conflicts.csv")


def get_room_csv_path() -> str:
    return str(GENETIC_DIR / "best_room_timetable.csv")


def load_schedule_from_csv() -> list[dict]:
    return _read_csv_file(get_schedule_csv_path())


def load_conflicts_from_csv() -> list[dict]:
    return _read_csv_file(get_conflicts_csv_path())


def run_algorithm() -> dict:
    """Run the genetic algorithm and return structured results."""
    # Save original state
    orig_dir = os.getcwd()
    orig_path = sys.path[:]

    try:
        os.chdir(str(GENETIC_DIR))

        # Add algo paths so imports resolve
        for p in [str(GENETIC_DIR), str(ALGO_DIR), str(ALGO_DIR / "helper")]:
            if p not in sys.path:
                sys.path.insert(0, p)

        # Import algo modules (inside function to avoid import at app startup)
        from main import read_courses_from_csv, initialize_population, run_one_generation
        from config import (
            POPULATION_SIZE, MUTATION_COUNT,
            LIMIT_POPULATION_GENERATION, LIMIT_FITTEST_UNCHANGED_GENERATION,
            FITNESS_RATIO_THRESHOLD, TARGET_SEASON, ACADEMIC_YEAR,
        )
        from fitness import fitness_function
        from termination import should_terminate
        from room_management import (
            load_room_assignments, create_room_timetables, validate_room_timetables,
        )
        from helper.export_utils import export_fittest_individual
        from helper.conflict_export import export_conflicts_csv
        from helper.sequence_loader import Sequence
        from helper.db_room_extractor import extract_and_generate_room_data
        from helper.db_sequence_extractor import extract_and_generate_sequences
        from helper.db_course_extractor import extract_and_generate_course_data

        start_time = time.time()

        # Step 1: Extract data from DB into CSVs
        extract_and_generate_sequences(
            "Sequences.csv", target_season=TARGET_SEASON, show_summary=False,
        )
        extract_and_generate_room_data("Room_data.csv", show_summary=False)
        extract_and_generate_course_data(
            "Data.csv", year=ACADEMIC_YEAR, season_code=TARGET_SEASON, show_summary=False,
        )

        # Step 2: Read courses, init population
        courses = read_courses_from_csv("Data.csv")
        if not courses:
            return {
                "status": "failed",
                "best_fitness": 0,
                "generations": 0,
                "termination_reason": "no_courses",
                "schedule": [],
                "conflicts": [],
                "num_conflicts": 0,
                "num_courses": 0,
            }

        room_assignments = load_room_assignments("Room_data.csv")
        population = initialize_population(courses, POPULATION_SIZE, room_assignments)
        seq = Sequence("Sequences.csv", season_filter=TARGET_SEASON)

        # Build semester labels mapping index → "Fall Year X (Program)"
        season_names = {1: "Summer", 2: "Fall", 3: "Fall/Winter", 4: "Winter"}
        season_name = season_names.get(TARGET_SEASON, "Term")
        semester_labels = {}
        sem_idx = 0
        for plan in seq.manager.get_all_plans():
            for term in plan.get_terms_for_season(TARGET_SEASON):
                sem_idx += 1
                semester_labels[str(sem_idx)] = (
                    f"{season_name} Year {term.yearnumber} ({plan.program})"
                )

        # Step 3: Initial fitness
        fitness_scores = [
            fitness_function(ind, core_sequences=seq.year, room_assignments=room_assignments)
            for ind in population
        ]
        fitness_history = [max(fitness_scores)]
        current_generation = 0

        # Step 4: Evolution loop
        while True:
            current_generation += 1
            population, fitness_scores = run_one_generation(
                population, fitness_scores, seq, room_assignments, num_offspring=2,
            )
            best_fitness = max(fitness_scores)
            fitness_history.append(best_fitness)

            terminate, reason = should_terminate(
                current_generation=current_generation,
                fitness_scores=fitness_scores,
                fitness_history=fitness_history,
                max_generations=LIMIT_POPULATION_GENERATION,
                unchanged_limit=LIMIT_FITTEST_UNCHANGED_GENERATION,
                ratio_threshold=FITNESS_RATIO_THRESHOLD,
            )
            if terminate:
                break

        # Step 5: Export best individual
        best_idx = fitness_scores.index(max(fitness_scores))
        best_individual = population[best_idx]

        export_fittest_individual(
            schedule=best_individual,
            room_assignments_path="Room_data.csv",
            course_output_path="best_course_timetable.csv",
            room_output_path="best_room_timetable.csv",
        )

        num_conflicts = export_conflicts_csv(
            schedule=best_individual,
            core_sequences=seq.year,
            room_assignments=room_assignments,
            output_path="conflicts.csv",
        )

        # Step 6: Export to optimized_schedule DB table
        try:
            from helper.scheduleterm_export import export_to_scheduleterm_format
            export_to_scheduleterm_format(
                schedule=best_individual,
                room_assignments=room_assignments,
                year=ACADEMIC_YEAR,
                season=TARGET_SEASON,
            )
            db_exported = True
        except Exception:
            db_exported = False

        duration = round(time.time() - start_time, 1)

        return {
            "status": "success",
            "best_fitness": round(best_fitness, 4),
            "generations": current_generation,
            "termination_reason": reason,
            "schedule": load_schedule_from_csv(),
            "conflicts": load_conflicts_from_csv(),
            "num_conflicts": num_conflicts if isinstance(num_conflicts, int) else 0,
            "num_courses": len(courses),
            "duration_seconds": duration,
            "db_exported": db_exported,
            "semester_labels": semester_labels,
        }

    except Exception as e:
        return {
            "status": "failed",
            "best_fitness": 0,
            "generations": 0,
            "termination_reason": str(e),
            "schedule": [],
            "conflicts": [],
            "num_conflicts": 0,
            "num_courses": 0,
            "semester_labels": {},
        }
    finally:
        os.chdir(orig_dir)
        sys.path[:] = orig_path
