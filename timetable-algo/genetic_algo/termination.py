# termination.py
from typing import List, Tuple

def check_generation_limit(current_generation: int, max_generations: int) -> Tuple[bool, str]:
    """Check if the algorithm has reached the maximum generation limit."""
    if current_generation >= max_generations:
        return True, f"Generation limit reached: {current_generation}/{max_generations}"
    return False, ""


def check_fitness_ratio(fitness_scores: List[float], ratio_threshold: float = 0.9) -> Tuple[bool, str]:
    """Check if the ratio of mean fitness to max fitness exceeds threshold (mean/max >= 0.9)."""
    if not fitness_scores:
        return False, ""
    
    mean_fitness = sum(fitness_scores) / len(fitness_scores)
    max_fitness = max(fitness_scores)
    
    if max_fitness <= 0:
        return False, ""
    
    ratio = mean_fitness / max_fitness
    
    if ratio >= ratio_threshold:
        return True, f"Fitness ratio threshold reached: {ratio:.4f} >= {ratio_threshold}"
    
    return False, ""


def check_stagnation(fitness_history: List[float], unchanged_limit: int) -> Tuple[bool, str]:
    """Check if the fittest individual has not changed over the past n generations."""
    if len(fitness_history) < unchanged_limit:
        return False, ""
    
    recent_history = fitness_history[-unchanged_limit:]
    first_value = recent_history[0]
    
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
    """Check all termination conditions: (i) generation limit, (ii) fitness ratio, (iii) stagnation."""
    terminate, reason = check_generation_limit(current_generation, max_generations)
    if terminate:
        return True, f"(i) {reason}"
    
    terminate, reason = check_fitness_ratio(fitness_scores, ratio_threshold)
    if terminate:
        return True, f"(ii) {reason}"
    
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
    """Display the status of all termination conditions."""
    pass


def display_final_statistics(fitness_history: List[float], 
                            final_generation: int,
                            termination_reason: str):
    """Display final statistics when the algorithm terminates."""
    pass
