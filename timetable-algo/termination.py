# termination.py
from typing import List, Tuple

def check_generation_limit(current_generation: int, max_generations: int) -> Tuple[bool, str]:
    """
    Check if the algorithm has reached the maximum generation limit.
    
    Args:
        current_generation: Current generation number
        max_generations: Maximum number of generations (g)
    
    Returns:
        Tuple of (should_terminate, reason)
    """
    if current_generation >= max_generations:
        return True, f"Generation limit reached: {current_generation}/{max_generations}"
    return False, ""


def check_fitness_ratio(fitness_scores: List[float], ratio_threshold: float = 0.9) -> Tuple[bool, str]:
    """
    Check if the ratio of mean fitness to max fitness exceeds threshold.
    
    Condition: mean_fitness / max_fitness >= 0.9
    
    Args:
        fitness_scores: List of fitness scores for the population
        ratio_threshold: Threshold ratio (default 0.9)
    
    Returns:
        Tuple of (should_terminate, reason)
    """
    if not fitness_scores:
        return False, ""
    
    mean_fitness = sum(fitness_scores) / len(fitness_scores)
    max_fitness = max(fitness_scores)
    
    # Handle edge case where max_fitness is 0 or negative
    if max_fitness <= 0:
        return False, ""
    
    ratio = mean_fitness / max_fitness
    
    if ratio >= ratio_threshold:
        return True, f"Fitness ratio threshold reached: {ratio:.4f} >= {ratio_threshold}"
    
    return False, ""


def check_stagnation(fitness_history: List[float], unchanged_limit: int) -> Tuple[bool, str]:
    """
    Check if the fittest individual has not changed over the past n generations.
    
    Args:
        fitness_history: List of best fitness scores from each generation
        unchanged_limit: Number of generations without improvement (n)
    
    Returns:
        Tuple of (should_terminate, reason)
    """
    if len(fitness_history) < unchanged_limit:
        return False, ""
    
    # Check the last n generations
    recent_history = fitness_history[-unchanged_limit:]
    
    # Check if all values are the same (no improvement)
    first_value = recent_history[0]
    
    # Use a small epsilon for floating point comparison
    epsilon = 1e-6
    all_same = all(abs(fitness - first_value) < epsilon for fitness in recent_history)
    
    if all_same:
        return True, f"No improvement in best fitness over {unchanged_limit} generations (best: {first_value:.4f})"
    
    return False, ""


def should_terminate(current_generation: int, 
                    fitness_scores: List[float], 
                    fitness_history: List[float],
                    max_generations: int,
                    unchanged_limit: int,
                    ratio_threshold: float = 0.9) -> Tuple[bool, str]:
    """
    Check all termination conditions and return whether to terminate.
    
    Termination occurs when ANY of these conditions are met:
    (i)   Current generation >= max_generations (g)
    (ii)  mean_fitness / max_fitness >= 0.9
    (iii) Best fitness unchanged for n generations
    
    Args:
        current_generation: Current generation number (starts at 0)
        fitness_scores: List of fitness scores for current population
        fitness_history: List of best fitness scores from each generation
        max_generations: Maximum number of generations (g from config)
        unchanged_limit: Number of generations without improvement (n from config)
        ratio_threshold: Fitness ratio threshold (default 0.9)
    
    Returns:
        Tuple of (should_terminate, termination_reason)
    """
    # Check condition (i): Generation limit
    terminate, reason = check_generation_limit(current_generation, max_generations)
    if terminate:
        return True, f"(i) {reason}"
    
    # Check condition (ii): Fitness ratio
    terminate, reason = check_fitness_ratio(fitness_scores, ratio_threshold)
    if terminate:
        return True, f"(ii) {reason}"
    
    # Check condition (iii): Stagnation
    terminate, reason = check_stagnation(fitness_history, unchanged_limit)
    if terminate:
        return True, f"(iii) {reason}"
    
    return False, "Continue evolution"


def display_termination_status(current_generation: int,
                               fitness_scores: List[float],
                               fitness_history: List[float],
                               max_generations: int,
                               unchanged_limit: int,
                               ratio_threshold: float = 0.9):
    """
    Display the status of all termination conditions.
    Useful for monitoring convergence progress.
    """
    print("\n" + "=" * 70)
    print(f"TERMINATION STATUS - Generation {current_generation}")
    print("=" * 70)
    
    # Condition (i): Generation limit
    progress_pct = (current_generation / max_generations) * 100
    print(f"(i) Generation Progress: {current_generation}/{max_generations} ({progress_pct:.1f}%)")
    
    # Condition (ii): Fitness ratio
    if fitness_scores:
        mean_fitness = sum(fitness_scores) / len(fitness_scores)
        max_fitness = max(fitness_scores)
        ratio = mean_fitness / max_fitness if max_fitness > 0 else 0
        print(f"(ii) Fitness Ratio: {ratio:.4f} (threshold: {ratio_threshold})")
        print(f"     Mean: {mean_fitness:.4f}, Max: {max_fitness:.4f}")
    
    # Condition (iii): Stagnation check
    if len(fitness_history) >= unchanged_limit:
        recent_history = fitness_history[-unchanged_limit:]
        first_value = recent_history[0]
        epsilon = 1e-6
        unchanged = all(abs(fitness - first_value) < epsilon for fitness in recent_history)
        status = "STAGNANT" if unchanged else "IMPROVING"
        print(f"(iii) Stagnation: {status} (last {unchanged_limit} generations)")
        print(f"      Recent best: {recent_history}")
    else:
        print(f"(iii) Stagnation: Need {unchanged_limit - len(fitness_history)} more generations to check")
    
    print("=" * 70)


def display_final_statistics(fitness_history: List[float], 
                            final_generation: int,
                            termination_reason: str):
    """
    Display final statistics when the algorithm terminates.
    """
    print("\n" + "=" * 70)
    print("GENETIC ALGORITHM TERMINATED")
    print("=" * 70)
    print(f"Termination Reason: {termination_reason}")
    print(f"Total Generations: {final_generation}")
    
    if fitness_history:
        print(f"\nFitness Evolution:")
        print(f"  Initial Best Fitness: {fitness_history[0]:.4f}")
        print(f"  Final Best Fitness: {fitness_history[-1]:.4f}")
        print(f"  Improvement: {fitness_history[-1] - fitness_history[0]:+.4f}")
        
        # Find the generation with best fitness
        best_fitness = max(fitness_history)
        best_gen = fitness_history.index(best_fitness)
        print(f"  Best Fitness Ever: {best_fitness:.4f} (Generation {best_gen})")
    
    print("=" * 70)


# Usage example:
# from config import LIMIT_POPULATION_GENERATION, LIMIT_FITTEST_UNCHANGED_GENERATION
# 
# current_gen = 0
# fitness_history = []  # Stores best fitness from each generation
# 
# while True:
#     # Run one generation of GA
#     fitness_scores = evaluate_population(population, core_sequences=seq.year)
#     best_fitness = max(fitness_scores)
#     fitness_history.append(best_fitness)
#     
#     # Check termination
#     terminate, reason = should_terminate(
#         current_generation=current_gen,
#         fitness_scores=fitness_scores,
#         fitness_history=fitness_history,
#         max_generations=LIMIT_POPULATION_GENERATION,
#         unchanged_limit=LIMIT_FITTEST_UNCHANGED_GENERATION
#     )
#     
#     if terminate:
#         display_final_statistics(fitness_history, current_gen, reason)
#         break
#     
#     # Display status periodically
#     if current_gen % 10 == 0:
#         display_termination_status(current_gen, fitness_scores, fitness_history,
#                                    LIMIT_POPULATION_GENERATION, LIMIT_FITTEST_UNCHANGED_GENERATION)
#     
#     # Continue evolution...
#     current_gen += 1
