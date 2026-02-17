import importlib
import os


def test_config_loads_env_vars(monkeypatch):
    monkeypatch.setenv("DB_HOST", "testhost")
    monkeypatch.setenv("DB_PORT", "5555")
    monkeypatch.setenv("DB_NAME", "testdb")
    monkeypatch.setenv("DB_USER", "testuser")
    monkeypatch.setenv("DB_PASSWORD", "testpass")

    import config
    importlib.reload(config)

    assert config.DB_HOST == "testhost"
    assert config.DB_PORT == 5555
    assert config.DB_NAME == "testdb"
    assert config.DB_USER == "testuser"
    assert config.DB_PASSWORD == "testpass"


def test_config_defaults(monkeypatch):
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_PORT", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **kw: None)

    import config
    importlib.reload(config)

    assert config.DB_HOST == "localhost"
    assert config.DB_PORT == 9999
    assert config.DB_PASSWORD == ""


def test_config_algorithm_params():
    import config
    assert config.POPULATION_SIZE == 4
    assert config.ALPHA == 0.75
    assert config.MUTATION_COUNT == 1
    assert config.LIMIT_POPULATION_GENERATION == 100
    assert config.LIMIT_FITTEST_UNCHANGED_GENERATION == 15
    assert config.FITNESS_RATIO_THRESHOLD == 0.9
