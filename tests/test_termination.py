from termination import (
    check_generation_limit,
    check_fitness_ratio,
    check_stagnation,
    should_terminate,
)


def test_generation_limit_reached():
    terminate, reason = check_generation_limit(100, 100)
    assert terminate is True
    assert "100" in reason


def test_generation_limit_not_reached():
    terminate, reason = check_generation_limit(50, 100)
    assert terminate is False


def test_fitness_ratio_converged():
    scores = [0.95, 0.96, 0.97, 0.98]
    terminate, reason = check_fitness_ratio(scores, 0.9)
    assert terminate is True


def test_fitness_ratio_not_converged():
    scores = [0.1, 0.2, 0.3, 0.9]
    terminate, reason = check_fitness_ratio(scores, 0.9)
    assert terminate is False


def test_fitness_ratio_empty():
    terminate, _ = check_fitness_ratio([], 0.9)
    assert terminate is False


def test_fitness_ratio_all_negative():
    terminate, _ = check_fitness_ratio([-5.0, -3.0, -1.0], 0.9)
    assert terminate is False


def test_stagnation_detected():
    history = [5.0, 5.0, 5.0, 5.0, 5.0]
    terminate, reason = check_stagnation(history, 5)
    assert terminate is True


def test_stagnation_not_enough_history():
    history = [5.0, 5.0]
    terminate, _ = check_stagnation(history, 5)
    assert terminate is False


def test_stagnation_improving():
    history = [1.0, 2.0, 3.0, 4.0, 5.0]
    terminate, _ = check_stagnation(history, 5)
    assert terminate is False


def test_should_terminate_generation_limit():
    terminate, reason = should_terminate(
        current_generation=100,
        fitness_scores=[0.5, 0.6],
        fitness_history=[0.5, 0.6],
        max_generations=100,
        unchanged_limit=15,
    )
    assert terminate is True
    assert "(i)" in reason


def test_should_terminate_fitness_ratio():
    terminate, reason = should_terminate(
        current_generation=10,
        fitness_scores=[0.95, 0.96, 0.97, 0.98],
        fitness_history=[0.5],
        max_generations=100,
        unchanged_limit=15,
    )
    assert terminate is True
    assert "(ii)" in reason


def test_should_terminate_stagnation():
    terminate, reason = should_terminate(
        current_generation=10,
        fitness_scores=[0.1, 0.5],
        fitness_history=[5.0] * 15,
        max_generations=100,
        unchanged_limit=15,
    )
    assert terminate is True
    assert "(iii)" in reason


def test_should_continue():
    terminate, reason = should_terminate(
        current_generation=10,
        fitness_scores=[0.1, 0.5],
        fitness_history=[1.0, 2.0, 3.0],
        max_generations=100,
        unchanged_limit=15,
    )
    assert terminate is False
    assert "Continue" in reason
