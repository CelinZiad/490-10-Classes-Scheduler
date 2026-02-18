# replacement.py
from typing import List, Tuple
from course import Course

def replace_worst_individuals(population, fitness_scores, offspring_list, offspring_fitness_scores):
    """Replace the n worst individuals in the population with n offspring."""
    n = len(offspring_list)
    
    if n == 0:
        return population, fitness_scores
    
    if n > len(population):
        raise ValueError(f"Cannot replace {n} individuals in population of size {len(population)}")
    
    indexed_population = [(i, fitness_scores[i], population[i]) for i in range(len(population))]
    sorted_population = sorted(indexed_population, key=lambda x: x[1])
    worst_indices = [item[0] for item in sorted_population[:n]]
    
    new_population = population.copy()
    new_fitness_scores = fitness_scores.copy()
    
    for i, worst_idx in enumerate(worst_indices):
        new_population[worst_idx] = offspring_list[i]
        new_fitness_scores[worst_idx] = offspring_fitness_scores[i]
    
    return new_population, new_fitness_scores


def elitist_replacement(population, fitness_scores, offspring_list, offspring_fitness_scores):
    """Replace individuals only if offspring have better fitness (elitist strategy)."""
    n = len(offspring_list)
    
    if n == 0:
        return population, fitness_scores
    
    indexed_population = [(i, fitness_scores[i], population[i]) for i in range(len(population))]
    sorted_population = sorted(indexed_population, key=lambda x: x[1])
    
    new_population = population.copy()
    new_fitness_scores = fitness_scores.copy()
    
    replacements = 0
    for i in range(n):
        worst_idx, worst_fitness, _ = sorted_population[i]
        
        if offspring_fitness_scores[i] > worst_fitness:
            new_population[worst_idx] = offspring_list[i]
            new_fitness_scores[worst_idx] = offspring_fitness_scores[i]
            replacements += 1
    
    return new_population, new_fitness_scores


def display_replacement_summary(old_fitness, new_fitness):
    """Display summary statistics before and after replacement."""
    pass
