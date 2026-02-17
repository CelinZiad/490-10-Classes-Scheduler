# course_filter.py
EXCLUDED_ELEC_COURSES = {'430', '434', '436', '438', '443', '446', '498'}


def should_include_course(subject: str, catalog: str) -> bool:
    """Determine if a course should be included in scheduling (COEN, ELEC except excluded, ENGR 290)."""
    subject = subject.upper().strip()
    catalog = catalog.strip()
    
    if subject == "COEN":
        return True
    
    if subject == "ELEC":
        return catalog not in EXCLUDED_ELEC_COURSES
    
    if subject == "ENGR" and catalog == "290":
        return True
    
    return False


def get_included_subjects() -> list:
    """Get list of fully included subjects."""
    return ["COEN", "ELEC"]


def get_partial_subjects() -> dict:
    """Get dictionary of partially included subjects with their rules."""
    return {
        "ENGR": ["290"],
        "ELEC": f"All except {', '.join(sorted(EXCLUDED_ELEC_COURSES))}"
    }


def display_filter_info():
    """Display information about course filtering."""
    pass


def filter_course_list(courses: list, subject_field: str = 'subject', 
                       catalog_field: str = 'catalog') -> tuple:
    """Filter a list of course dictionaries."""
    filtered_courses = []
    filtered_count = 0
    
    for course in courses:
        subject = course.get(subject_field, '')
        catalog = course.get(catalog_field, '')
        
        if should_include_course(subject, catalog):
            filtered_courses.append(course)
        else:
            filtered_count += 1
    
    return filtered_courses, filtered_count


if __name__ == "__main__":
    display_filter_info()
