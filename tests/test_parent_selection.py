import pytest
from parent_selection import (
    rank_individuals,
    calculate_selection_probabilities,
    select_parents,
)


def test_rank_individuals_ordering():
    scores = [0.5, 0.9, 0.1, 0.7]
    ranked = rank_individuals(scores)
    rank_map = {idx: rank for idx, rank in ranked}
    assert rank_map[1] == 1  # 0.9 is best
    assert rank_map[3] == 2  # 0.7 is second
    assert rank_map[0] == 3  # 0.5 is third
    assert rank_map[2] == 4  # 0.1 is worst


def test_selection_probabilities_sum_to_one():
    scores = [0.5, 0.9, 0.1, 0.7]
    probs = calculate_selection_probabilities(scores, 0.75)
    assert abs(sum(probs) - 1.0) < 1e-6


def test_selection_probabilities_best_gets_highest():
    scores = [0.5, 0.9, 0.1, 0.7]
    probs = calculate_selection_probabilities(scores, 0.75)
    assert probs[1] > probs[0]  # 0.9 > 0.5
    assert probs[1] > probs[2]  # 0.9 > 0.1


def test_selection_probabilities_empty():
    assert calculate_selection_probabilities([], 0.75) == []


def test_select_parents_returns_two():
    scores = [0.5, 0.9, 0.1, 0.7]
    parents = select_parents(scores, num_parents=2)
    assert len(parents) == 2
    assert parents[0] != parents[1]
    assert all(0 <= p < 4 for p in parents)
