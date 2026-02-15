# parent_selection.py
import numpy as np
from typing import List, Tuple
from config import ALPHA

def rank_individuals(fitness_scores):
    """Rank individuals based on fitness scores (best=1, worst=N)."""
    indexed_scores = [(i, score) for i, score in enumerate(fitness_scores)]
    sorted_scores = sorted(indexed_scores, key=lambda x: x[1], reverse=True)
    ranked = [(idx, rank + 1) for rank, (idx, score) in enumerate(sorted_scores)]
    
    return ranked


def calculate_selection_probabilities(fitness_scores, alpha):
    """Calculate parent selection probabilities using exponential ranking selection."""
    if not fitness_scores:
        return []
    
    N = len(fitness_scores)
    ranked = rank_individuals(fitness_scores)
    
    weights = {}
    for idx, rank in ranked:
        weights[idx] = alpha ** (rank - 1)
    
    total_weight = sum(weights.values())
    probabilities = [weights[i] / total_weight for i in range(N)]
    
    return probabilities


def select_parents(fitness_scores, num_parents=2):
    """Select parents using exponential ranking selection."""
    probabilities = calculate_selection_probabilities(fitness_scores, ALPHA)
    
    parent_indices = np.random.choice(
        len(fitness_scores),
        size=num_parents,
        replace=False,
        p=probabilities
    )
    
    return parent_indices.tolist()


def display_selection_info(fitness_scores):
    """Display ranking and selection probability information."""
    pass
