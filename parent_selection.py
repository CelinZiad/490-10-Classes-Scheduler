import numpy as np
from typing import List, Tuple
from config import ALPHA

def rank_individuals(fitness_scores):
    """
    Rank individuals based on fitness scores.
    
    Args:
        fitness_scores: List of fitness scores
    
    Returns:
        List of tuples (index, rank) sorted by rank (best=1, worst=N)
    """
    # Create list of (index, score) tuples
    indexed_scores = [(i, score) for i, score in enumerate(fitness_scores)]
    
    # Sort by score descending (highest score = best = rank 1)
    sorted_scores = sorted(indexed_scores, key=lambda x: x[1], reverse=True)
    
    # Assign ranks (1 to N)
    ranked = [(idx, rank + 1) for rank, (idx, score) in enumerate(sorted_scores)]
    
    return ranked


def calculate_selection_probabilities(fitness_scores, alpha):
    """
    Calculate parent selection probabilities using exponential ranking selection.
    
    Formula: P(i) = (alpha^(rank_i - 1)) / sum(alpha^(rank_j - 1) for all j)
    
    Args:
        fitness_scores: List of fitness scores
        alpha: Exponential ranking parameter (0 < alpha < 1)
               - Smaller alpha = more selective (favors best individuals)
               - Larger alpha = less selective (more uniform selection)
    
    Returns:
        List of selection probabilities (same order as fitness_scores)
    """
    if not fitness_scores:
        return []
    
    N = len(fitness_scores)
    
    # Get rankings
    ranked = rank_individuals(fitness_scores)
    
    # Calculate exponential weights for each rank
    # rank 1 (best) gets alpha^0 = 1
    # rank N (worst) gets alpha^(N-1)
    weights = {}
    for idx, rank in ranked:
        weights[idx] = alpha ** (rank - 1)
    
    # Normalize to get probabilities
    total_weight = sum(weights.values())
    probabilities = [weights[i] / total_weight for i in range(N)]
    
    return probabilities


def select_parents(fitness_scores, num_parents=2):
    """
    Select parents using exponential ranking selection.
    
    Args:
        fitness_scores: List of fitness scores
        num_parents: Number of parents to select
    
    Returns:
        List of selected parent indices
    """
    probabilities = calculate_selection_probabilities(fitness_scores, ALPHA)
    
    # Select parents based on probabilities (with replacement)
    parent_indices = np.random.choice(
        len(fitness_scores),
        size=num_parents,
        replace=False,
        p=probabilities
    )
    
    return parent_indices.tolist()


def display_selection_info(fitness_scores):
    """
    Display ranking and selection probability information.
    Useful for debugging and understanding selection pressure.
    """
    ranked = rank_individuals(fitness_scores)
    probabilities = calculate_selection_probabilities(fitness_scores, ALPHA)
    
    print(f"\nExponential Ranking Selection (α = {ALPHA})")
    print("=" * 60)
    print(f"{'Index':<8} {'Fitness':<12} {'Rank':<8} {'Probability':<12}")
    print("-" * 60)
    
    for idx, rank in sorted(ranked, key=lambda x: x[1]):
        fitness = fitness_scores[idx]
        prob = probabilities[idx]
        print(f"{idx:<8} {fitness:<12.4f} {rank:<8} {prob:<12.4f}")
    
    print("=" * 60)
    print(f"Sum of probabilities: {sum(probabilities):.6f}")


# Usage example:
# from config import ALPHA
# 
# # After calculating fitness scores
# fitness_scores = evaluate_population(population)
# 
# # View selection information
# display_selection_info(fitness_scores)
# 
# # Select 2 parents
# parent_indices = select_parents(fitness_scores, num_parents=2)
# parent1 = population[parent_indices[0]]
# parent2 = population[parent_indices[1]]
# 
# # Or get just the probabilities
# probabilities = calculate_selection_probabilities(fitness_scores, ALPHA)