# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

POPULATION_SIZE = 4
ALPHA = 0.75
MUTATION_COUNT = 1

LIMIT_POPULATION_GENERATION = 100
LIMIT_FITTEST_UNCHANGED_GENERATION = 15
FITNESS_RATIO_THRESHOLD = 0.9

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 9999))
DB_NAME = os.environ.get("DB_NAME", "uvo490_3")
DB_USER = os.environ.get("DB_USER", "uvo490_3")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

TARGET_SEASON = 2  # 1=Summer, 2=Fall, 3=Fall+Winter, 4=Winter
ACADEMIC_YEAR = 2026
