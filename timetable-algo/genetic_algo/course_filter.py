# course_filter.py
"""
Utility module for filtering courses to only include relevant subjects.

The system schedules only:
- COEN courses (all)
- ELEC courses (all EXCEPT 430, 434, 436, 438, 443, 446, 498)
- ENGR 290 (specific course)

All other courses (SOEN, other ENGR, ENCS, etc.) are excluded from scheduling.
"""

# ELEC courses that should be completely excluded
EXCLUDED_ELEC_COURSES = {'430', '434', '436', '438', '443', '446', '498'}


def should_include_course(subject: str, catalog: str) -> bool:
    """
    Determine if a course should be included in scheduling.
    
    Include only:
    - COEN courses (all catalog numbers)
    - ELEC courses (EXCEPT 430, 434, 436, 438, 443, 446, 498)
    - ENGR 290 (specific course only)
    
    Args:
        subject: Course subject code (e.g., "COEN", "ELEC", "ENGR")
        catalog: Course catalog number (e.g., "212", "290", "311")
    
    Returns:
        True if course should be included in scheduling, False otherwise
    
    Examples:
        >>> should_include_course("COEN", "212")
        True
        >>> should_include_course("ELEC", "273")
        True
        >>> should_include_course("ELEC", "430")
        False
        >>> should_include_course("ELEC", "438")
        False
        >>> should_include_course("ENGR", "290")
        True
        >>> should_include_course("ENGR", "201")
        False
        >>> should_include_course("SOEN", "341")
        False
    """
    subject = subject.upper().strip()
    catalog = catalog.strip()
    
    # Include all COEN courses
    if subject == "COEN":
        return True
    
    # Include ELEC courses EXCEPT excluded ones
    if subject == "ELEC":
        return catalog not in EXCLUDED_ELEC_COURSES
    
    # Include only ENGR 290 (not other ENGR courses)
    if subject == "ENGR" and catalog == "290":
        return True
    
    # Exclude all other courses
    return False


def get_included_subjects() -> list:
    """
    Get list of fully included subjects.
    
    Returns:
        List of subject codes that are fully included
    """
    return ["COEN", "ELEC"]


def get_partial_subjects() -> dict:
    """
    Get dictionary of partially included subjects with their rules.
    
    Returns:
        Dictionary mapping subject to inclusion rules
    """
    return {
        "ENGR": ["290"],
        "ELEC": f"All except {', '.join(sorted(EXCLUDED_ELEC_COURSES))}"
    }


def display_filter_info():
    """Display information about course filtering."""
    print("\n" + "=" * 70)
    print("COURSE FILTERING RULES")
    print("=" * 70)
    print("Fully included subjects:")
    for subject in get_included_subjects():
        if subject == "ELEC":
            print(f"  ✓ {subject} - All courses EXCEPT {', '.join(sorted(EXCLUDED_ELEC_COURSES))}")
        else:
            print(f"  ✓ {subject} - All courses")
    
    print("\nPartially included subjects:")
    for subject, info in get_partial_subjects().items():
        if subject == "ELEC":
            continue  # Already shown above
        if isinstance(info, list):
            print(f"  ✓ {subject} - Only: {', '.join(info)}")
        else:
            print(f"  ✓ {subject} - {info}")
    
    print("\nExcluded subjects:")
    excluded = ["SOEN", "ENCS", "ENGR (except 290)", "COMP", "MECH", "INDU", "BLDG", "CIVI"]
    for subject in excluded:
        print(f"  ✗ {subject}")
    
    print("\nExcluded ELEC courses:")
    for course in sorted(EXCLUDED_ELEC_COURSES):
        print(f"  ✗ ELEC {course}")
    
    print("=" * 70)


def filter_course_list(courses: list, subject_field: str = 'subject', 
                       catalog_field: str = 'catalog') -> tuple:
    """
    Filter a list of course dictionaries.
    
    Args:
        courses: List of course dictionaries
        subject_field: Name of subject field in dictionary
        catalog_field: Name of catalog field in dictionary
    
    Returns:
        Tuple of (filtered_courses, filtered_count)
    """
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


# For testing
if __name__ == "__main__":
    display_filter_info()
    
    print("\nTest cases:")
    test_cases = [
        ("COEN", "212", True),
        ("COEN", "490", True),
        ("ELEC", "273", True),
        ("ELEC", "490", True),
        ("ELEC", "430", False),  # Excluded
        ("ELEC", "434", False),  # Excluded
        ("ELEC", "436", False),  # Excluded
        ("ELEC", "438", False),  # Excluded
        ("ELEC", "443", False),  # Excluded
        ("ELEC", "446", False),  # Excluded
        ("ELEC", "498", False),  # Excluded
        ("ENGR", "290", True),
        ("ENGR", "201", False),
        ("ENGR", "391", False),
        ("SOEN", "341", False),
        ("ENCS", "282", False),
        ("COMP", "232", False),
    ]
    
    print(f"{'Subject':<10} {'Catalog':<10} {'Expected':<10} {'Result':<10} {'Status':<10}")
    print("-" * 50)
    
    for subject, catalog, expected in test_cases:
        result = should_include_course(subject, catalog)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        print(f"{subject:<10} {catalog:<10} {str(expected):<10} {str(result):<10} {status:<10}")
