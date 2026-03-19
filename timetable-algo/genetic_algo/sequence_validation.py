# sequence_validation.py
from overlap_utils import times_overlap, get_course_by_code, has_valid_sequence_combination


def check_elements_overlap(element, other_elements):
    """Check if an element overlaps with any element in a list."""
    for other in other_elements:
        if times_overlap(element, other):
            return True
    return False


def validate_all_sequences(schedule, sequence):
    """Validate all semester sequences in the Sequence class."""
    results = {}
    
    for semester_idx, semester_courses in enumerate(sequence.year):
        semester_name = f"Semester {semester_idx + 1}"
        is_valid = has_valid_sequence_combination(schedule, semester_courses)
        results[semester_name] = is_valid
    
    return results