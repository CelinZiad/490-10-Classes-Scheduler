# Genetic Algorithm Parameters
POPULATION_SIZE = 4
ALPHA = 0.75
MUTATION_COUNT = 1

# Termination conditions
LIMIT_POPULATION_GENERATION = 100  # Maximum number of generations (g) - to be tuned
LIMIT_FITTEST_UNCHANGED_GENERATION = 15  # Generations without improvement (n) - to be tuned
FITNESS_RATIO_THRESHOLD = 0.9  # Threshold for mean/max fitness ratio
# Genetic Algorithm Parameters
POPULATION_SIZE = 4
ALPHA = 0.75
MUTATION_COUNT = 1

# Termination conditions
LIMIT_POPULATION_GENERATION = 100  # Maximum number of generations (g) - to be tuned
LIMIT_FITTEST_UNCHANGED_GENERATION = 15  # Generations without improvement (n) - to be tuned
FITNESS_RATIO_THRESHOLD = 0.9  # Threshold for mean/max fitness ratio

# Database connection
DB_HOST = "localhost"
DB_PORT = 9999
DB_NAME = "uvo490_3"
DB_USER = "uvo490_3"
DB_PASSWORD = "coolbird18"

# Season/Term selection
# Season codes:
# 1 = Summer term
# 2 = Fall term
# 3 = Fall + Winter (26-week course)
# 4 = Winter term
TARGET_SEASON = 2  # Default to Fall term
ACADEMIC_YEAR = 2026  # Academic year for schedule generation

# Database connection
DB_HOST = "localhost"
DB_PORT = 9999
DB_NAME = "uvo490_3"
DB_USER = "uvo490_3"
DB_PASSWORD = "password"

# Season/Term selection
# 2 = Fall term
# 4 = Winter term
# 6 = Summer term (not typically used for scheduling)
TARGET_SEASON = 2  # Default to Fall term
ACADEMIC_YEAR = 2025  # Academic year for schedule extraction
