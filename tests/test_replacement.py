import pytest
from replacement import replace_worst_individuals, elitist_replacement


def test_replace_worst_basic():
    population = ["A", "B", "C", "D"]
    fitness = [3.0, 1.0, 4.0, 2.0]
    offspring = ["X"]
    offspring_fitness = [5.0]

    new_pop, new_fit = replace_worst_individuals(population, fitness, offspring, offspring_fitness)
    assert len(new_pop) == 4
    assert "X" in new_pop
    assert new_pop[1] == "X"  # B had lowest fitness (1.0)


def test_replace_worst_empty_offspring():
    population = ["A", "B"]
    fitness = [1.0, 2.0]
    new_pop, new_fit = replace_worst_individuals(population, fitness, [], [])
    assert new_pop == ["A", "B"]


def test_replace_worst_too_many_raises():
    with pytest.raises(ValueError):
        replace_worst_individuals(["A"], [1.0], ["X", "Y"], [2.0, 3.0])


def test_replace_preserves_size():
    population = ["A", "B", "C", "D"]
    fitness = [1.0, 2.0, 3.0, 4.0]
    offspring = ["X", "Y"]
    offspring_fitness = [5.0, 6.0]
    new_pop, new_fit = replace_worst_individuals(population, fitness, offspring, offspring_fitness)
    assert len(new_pop) == 4
    assert len(new_fit) == 4


def test_elitist_replaces_when_better():
    population = ["A", "B", "C"]
    fitness = [1.0, 2.0, 3.0]
    offspring = ["X"]
    offspring_fitness = [5.0]

    new_pop, new_fit = elitist_replacement(population, fitness, offspring, offspring_fitness)
    assert "X" in new_pop


def test_elitist_keeps_when_worse():
    population = ["A", "B", "C"]
    fitness = [5.0, 6.0, 7.0]
    offspring = ["X"]
    offspring_fitness = [1.0]

    new_pop, new_fit = elitist_replacement(population, fitness, offspring, offspring_fitness)
    assert "X" not in new_pop
    assert new_pop == ["A", "B", "C"]
