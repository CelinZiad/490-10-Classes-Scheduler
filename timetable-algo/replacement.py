from typing import List, Tuple
from course import Course

def replace_worst_individuals(population, fitness_scores, offspring_list, offspring_fitness_scores):
    """
    Replace the n worst individuals in the population with n offspring.
    
    Args:
        population: List of schedules (each schedule is a list of Course objects)
        fitness_scores: List of fitness scores for the population
        offspring_list: List of offspring schedules to insert
        offspring_fitness_scores: List of fitness scores for the offspring
    
    Returns:
        Tuple of (new_population, new_fitness_scores)
    """
    n = len(offspring_list)
    
    if n == 0:
        return population, fitness_scores
    
    if n > len(population):
        raise ValueError(f"Cannot replace {n} individuals in population of size {len(population)}")
    
    # Create list of (index, fitness, schedule) tuples
    indexed_population = [(i, fitness_scores[i], population[i]) for i in range(len(population))]
    
    # Sort by fitness (ascending order - worst first)
    sorted_population = sorted(indexed_population, key=lambda x: x[1])
    
    # Get indices of worst n individuals
    worst_indices = [item[0] for item in sorted_population[:n]]
    
    # Create new population and fitness lists
    new_population = population.copy()
    new_fitness_scores = fitness_scores.copy()
    
    # Replace worst individuals with offspring
    for i, worst_idx in enumerate(worst_indices):
        new_population[worst_idx] = offspring_list[i]
        new_fitness_scores[worst_idx] = offspring_fitness_scores[i]
        print(f"Replaced individual {worst_idx} (fitness: {fitness_scores[worst_idx]:.4f}) "
              f"with offspring {i} (fitness: {offspring_fitness_scores[i]:.4f})")
    
    return new_population, new_fitness_scores


def elitist_replacement(population, fitness_scores, offspring_list, offspring_fitness_scores):
    """
    Replace individuals only if offspring have better fitness (elitist strategy).
    
    Args:
        population: List of schedules
        fitness_scores: List of fitness scores for the population
        offspring_list: List of offspring schedules
        offspring_fitness_scores: List of fitness scores for the offspring
    
    Returns:
        Tuple of (new_population, new_fitness_scores)
    """
    n = len(offspring_list)
    
    if n == 0:
        return population, fitness_scores
    
    # Create list of (index, fitness, schedule) for population
    indexed_population = [(i, fitness_scores[i], population[i]) for i in range(len(population))]
    
    # Sort by fitness (ascending order - worst first)
    sorted_population = sorted(indexed_population, key=lambda x: x[1])
    
    # Create new population and fitness lists
    new_population = population.copy()
    new_fitness_scores = fitness_scores.copy()
    
    replacements = 0
    for i in range(n):
        worst_idx, worst_fitness, _ = sorted_population[i]
        
        # Only replace if offspring is better
        if offspring_fitness_scores[i] > worst_fitness:
            new_population[worst_idx] = offspring_list[i]
            new_fitness_scores[worst_idx] = offspring_fitness_scores[i]
            print(f"✓ Replaced individual {worst_idx} (fitness: {worst_fitness:.4f}) "
                  f"with offspring {i} (fitness: {offspring_fitness_scores[i]:.4f})")
            replacements += 1
        else:
            print(f"✗ Kept individual {worst_idx} (fitness: {worst_fitness:.4f}) "
                  f"over offspring {i} (fitness: {offspring_fitness_scores[i]:.4f})")
    
    print(f"\nTotal replacements: {replacements}/{n}")
    
    return new_population, new_fitness_scores


def display_replacement_summary(old_fitness, new_fitness):
    """
    Display summary statistics before and after replacement.
    """
    print("\n" + "=" * 60)
    print("REPLACEMENT SUMMARY")
    print("=" * 60)
    print(f"{'Metric':<20} {'Before':<15} {'After':<15} {'Change':<15}")
    print("-" * 60)
    
    old_avg = sum(old_fitness) / len(old_fitness)
    new_avg = sum(new_fitness) / len(new_fitness)
    print(f"{'Average Fitness':<20} {old_avg:<15.4f} {new_avg:<15.4f} {new_avg - old_avg:+.4f}")
    
    old_best = max(old_fitness)
    new_best = max(new_fitness)
    print(f"{'Best Fitness':<20} {old_best:<15.4f} {new_best:<15.4f} {new_best - old_best:+.4f}")
    
    old_worst = min(old_fitness)
    new_worst = min(new_fitness)
    print(f"{'Worst Fitness':<20} {old_worst:<15.4f} {new_worst:<15.4f} {new_worst - old_worst:+.4f}")
    
    print("=" * 60)


# Usage example:
# from fitness import fitness_function
# 
# # Create offspring
# offspring_list = []
# for _ in range(5):  # Generate 5 offspring
#     parent_indices = select_parents(fitness_scores, num_parents=2)
#     offspring = uniform_crossover(
#         population[parent_indices[0]],
#         population[parent_indices[1]],
#         seq.year
#     )
#     mutated = mutate(offspring, seq.year)
#     offspring_list.append(mutated)
# 
# # Evaluate offspring
# offspring_fitness = [fitness_function(off) for off in offspring_list]
# 
# # Replace worst individuals (always replaces)
# population, fitness_scores = replace_worst_individuals(
#     population, fitness_scores, offspring_list, offspring_fitness
# )
# 
# # OR use elitist replacement (only replaces if offspring is better)
# population, fitness_scores = elitist_replacement(
#     population, fitness_scores, offspring_list, offspring_fitness
# )
# 
# # Show summary
# display_replacement_summary(old_fitness_scores, fitness_scores)
