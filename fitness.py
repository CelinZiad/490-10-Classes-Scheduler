from itertools import product

def calculate_variety_score(elements):
    """
    Calculate variety score for a list of course elements (labs or tutorials).
    Returns a score between 0 and 1 based on day and time diversity.
    
    Higher score = more variety (different days and times)
    Lower score = less variety (same days and times)
    """
    if not elements or len(elements) <= 1:
        return 1.0  # Single or no elements = perfect variety
    
    # Filter out None elements
    valid_elements = [e for e in elements if e is not None]
    
    if len(valid_elements) <= 1:
        return 1.0
    
    n = len(valid_elements)
    
    # Calculate day variety score
    unique_days = set()
    for element in valid_elements:
        unique_days.update(element.day)
    
    total_days = sum(len(element.day) for element in valid_elements)
    day_variety = len(unique_days) / total_days if total_days > 0 else 0
    
    # Calculate time variety score
    unique_times = len(set(element.start for element in valid_elements))
    time_variety = unique_times / n
    
    # Combined score (weighted average)
    variety_score = 0.5 * day_variety + 0.5 * time_variety
    
    return variety_score


def times_overlap(element1, element2):
    """
    Check if two course elements overlap in time.
    Returns True if they overlap, False otherwise.
    """
    if element1 is None or element2 is None:
        return False
    
    # Check if they share any days
    days1 = set(element1.day)
    days2 = set(element2.day)
    
    if not days1.intersection(days2):
        return False  # Different days = no overlap
    
    # Same day(s), check time overlap
    return element1.start < element2.end and element2.start < element1.end


def count_lecture_conflicts(course):
    """
    Count conflicts between a course's lecture and its tutorials/labs.
    
    NOTE: This operates on a single Course object, which already has a unique class_nbr.
    Therefore, type (i) conflicts are automatically scoped to the specific class_nbr.
    For example, COEN212 with class_nbr 4886 is checked separately from 
    COEN212 with class_nbr 4889.
    
    Returns:
        Number of conflicts (tutorial or lab overlapping with lecture)
    """
    conflicts = 0
    
    if not course.lecture:
        return 0
    
    # Check tutorial overlaps with lecture
    if course.tutorial:
        for tut in course.tutorial:
            if tut is not None and times_overlap(course.lecture, tut):
                conflicts += 1
    
    # Check lab overlaps with lecture
    if course.lab:
        for lab in course.lab:
            if lab is not None and times_overlap(course.lecture, lab):
                conflicts += 1
    
    return conflicts


def get_course_by_code(schedule, course_code, class_nbr=None):
    """
    Find a course in the schedule by its subject+catalog_nbr and optionally class_nbr.
    Example: 'COEN212' -> finds course with subject='COEN' and catalog_nbr='212'
    
    Args:
        schedule: List of Course objects
        course_code: Course code like 'COEN212'
        class_nbr: Optional class number to distinguish between sections
    
    Returns:
        Course object if found, None otherwise
    """
    subject = ''.join(c for c in course_code if c.isalpha())
    catalog = ''.join(c for c in course_code if c.isdigit())
    
    for course in schedule:
        if course.subject == subject and course.catalog_nbr == catalog:
            if class_nbr is None or course.class_nbr == class_nbr:
                return course
    return None


def has_valid_sequence_combination(schedule, sequence_courses):
    """
    Check if there's at least one valid combination of tutorials and labs
    for a sequence of courses without any overlaps.
    
    Args:
        schedule: List of Course objects
        sequence_courses: List of course codes (e.g., ["COEN212", "COEN231", "COEN243"])
    
    Returns:
        True if at least one valid combination exists, False otherwise
    """
    # Get all courses in the sequence
    courses = []
    for course_code in sequence_courses:
        course = get_course_by_code(schedule, course_code)
        if course is None:
            return False  # Course not found = invalid
        courses.append(course)
    
    # Collect all tutorials and labs for each course
    all_tutorials = []
    all_labs = []
    
    for course in courses:
        if course.tutorial:
            valid_tuts = [t for t in course.tutorial if t is not None]
            if valid_tuts:
                all_tutorials.append(valid_tuts)
        
        if course.lab:
            valid_labs = [l for l in course.lab if l is not None]
            if valid_labs:
                all_labs.append(valid_labs)
    
    # If no tutorials or labs, no conflict possible
    if not all_tutorials and not all_labs:
        return True
    
    # Generate all possible combinations of tutorials
    tut_combinations = list(product(*all_tutorials)) if all_tutorials else [[]]
    
    # Generate all possible combinations of labs
    lab_combinations = list(product(*all_labs)) if all_labs else [[]]
    
    # Check each combination of tutorials with each combination of labs
    for tut_combo in tut_combinations:
        # Check if tutorials in this combination overlap with each other
        tut_has_overlap = False
        for i, tut1 in enumerate(tut_combo):
            for tut2 in tut_combo[i+1:]:
                if times_overlap(tut1, tut2):
                    tut_has_overlap = True
                    break
            if tut_has_overlap:
                break
        
        if tut_has_overlap:
            continue  # Skip this tutorial combination
        
        # Now check lab combinations with this valid tutorial combination
        for lab_combo in lab_combinations:
            # Check if labs in this combination overlap with each other
            lab_has_overlap = False
            for i, lab1 in enumerate(lab_combo):
                for lab2 in lab_combo[i+1:]:
                    if times_overlap(lab1, lab2):
                        lab_has_overlap = True
                        break
                if lab_has_overlap:
                    break
            
            if lab_has_overlap:
                continue  # Skip this lab combination
            
            # Check if any lab overlaps with any tutorial
            tut_lab_overlap = False
            for tut in tut_combo:
                for lab in lab_combo:
                    if times_overlap(tut, lab):
                        tut_lab_overlap = True
                        break
                if tut_lab_overlap:
                    break
            
            if not tut_lab_overlap:
                return True  # Found a valid combination!
    
    return False  # No valid combination found


def count_sequence_conflicts(schedule, core_sequences):
    """
    Count the number of semester sequences that have no valid combination.
    
    Args:
        schedule: List of Course objects
        core_sequences: List of lists of course codes (e.g., [["COEN212", "COEN231"], ["COEN244"]])
    
    Returns:
        Number of sequences with conflicts (no valid combination)
    """
    conflicts = 0
    
    for semester_courses in core_sequences:
        if not has_valid_sequence_combination(schedule, semester_courses):
            conflicts += 1
    
    return conflicts


def fitness_function(schedule, core_sequences=None, room_assignments=None):
    """
    Evaluate a single schedule (list of Course objects).
    
    Fitness = variety_score + (-2 * number_of_conflicts)
    
    Conflicts include:
    (i) Overlaps between course lecture and associated tutorial or lab
    (ii) No possible sequence of core course tutorials and labs (for each semester)
    (iii) Room conflicts (if room_assignments provided)
    
    Args:
        schedule: List of Course objects
        core_sequences: List of lists of course codes (e.g., from Sequence.year)
        room_assignments: List of RoomAssignment objects (optional)
    
    Returns:
        Fitness score (can be negative due to conflict penalties)
    """
    if not schedule:
        return 0.0
    
    # Calculate variety score (same as before)
    total_variety = 0.0
    variety_count = 0
    
    for course in schedule:
        # Evaluate tutorial variety
        if course.tutorial and course.tut_count > 0:
            tut_score = calculate_variety_score(course.tutorial)
            total_variety += tut_score
            variety_count += 1
        
        # Evaluate lab variety
        if course.lab and course.lab_count > 0:
            lab_score = calculate_variety_score(course.lab)
            total_variety += lab_score
            variety_count += 1
    
    variety_score = total_variety / variety_count if variety_count > 0 else 1.0
    
    # Count conflicts
    total_conflicts = 0
    
    # (i) Count lecture-tutorial/lab overlaps for all courses
    for course in schedule:
        total_conflicts += count_lecture_conflicts(course)
    
    # (ii) Count sequence conflicts (if core_sequences provided)
    if core_sequences:
        total_conflicts += count_sequence_conflicts(schedule, core_sequences)
    
    # (iii) Count room conflicts (if room_assignments provided)
    if room_assignments:
        from room_management import count_room_conflicts
        room_conflicts = count_room_conflicts(schedule, room_assignments)
        total_conflicts += room_conflicts
    
    # Calculate final fitness
    fitness = variety_score + (-2 * total_conflicts)
    
    return fitness


def evaluate_population(population, core_sequences=None, room_assignments=None):
    """
    Evaluate all schedules in the population.
    Returns a list of fitness scores.
    
    Args:
        population: List of schedules
        core_sequences: List of lists of course codes (optional)
        room_assignments: List of RoomAssignment objects (optional)
    """
    fitness_scores = []
    
    for i, schedule in enumerate(population):
        score = fitness_function(schedule, core_sequences, room_assignments)
        fitness_scores.append(score)
        print(f"Schedule {i + 1}: Fitness = {score:.4f}")
    
    return fitness_scores


def display_fitness_details(schedule, core_sequences=None, room_assignments=None):
    """
    Display detailed breakdown of fitness score for a schedule.
    Useful for debugging and understanding fitness components.
    """
    print("\n" + "=" * 60)
    print("FITNESS BREAKDOWN")
    print("=" * 60)
    
    # Calculate variety score
    total_variety = 0.0
    variety_count = 0
    
    for course in schedule:
        if course.tutorial and course.tut_count > 0:
            tut_score = calculate_variety_score(course.tutorial)
            total_variety += tut_score
            variety_count += 1
            print(f"{course.subject}{course.catalog_nbr} (class_nbr: {course.class_nbr}) Tutorial Variety: {tut_score:.4f}")
        
        if course.lab and course.lab_count > 0:
            lab_score = calculate_variety_score(course.lab)
            total_variety += lab_score
            variety_count += 1
            print(f"{course.subject}{course.catalog_nbr} (class_nbr: {course.class_nbr}) Lab Variety: {lab_score:.4f}")
    
    variety_score = total_variety / variety_count if variety_count > 0 else 1.0
    
    print(f"\nAverage Variety Score: {variety_score:.4f}")
    
    # Count conflicts
    lecture_conflicts = 0
    print("\nLecture-Tutorial/Lab Conflicts (by class_nbr):")
    for course in schedule:
        conflicts = count_lecture_conflicts(course)
        if conflicts > 0:
            print(f"  {course.subject}{course.catalog_nbr} (class_nbr: {course.class_nbr}): {conflicts} conflict(s)")
        lecture_conflicts += conflicts
    
    if lecture_conflicts == 0:
        print("  No lecture conflicts found")
    
    print(f"Total Lecture Conflicts: {lecture_conflicts}")
    
    sequence_conflicts = 0
    if core_sequences:
        print("\nCore Sequence Conflicts:")
        for i, semester_courses in enumerate(core_sequences):
            is_valid = has_valid_sequence_combination(schedule, semester_courses)
            if not is_valid:
                print(f"  Semester {i+1} {semester_courses}: NO VALID COMBINATION")
                sequence_conflicts += 1
            else:
                print(f"  Semester {i+1} {semester_courses}: Valid")
        
        print(f"Total Sequence Conflicts: {sequence_conflicts}")
    
    # Display room conflicts if room_assignments provided
    room_conflicts = 0
    if room_assignments:
        from room_management import count_room_conflicts
        room_conflicts = count_room_conflicts(schedule, room_assignments)
        print(f"Room Conflicts: {room_conflicts}")
    
    total_conflicts = lecture_conflicts + sequence_conflicts + room_conflicts
    fitness = variety_score + (-2 * total_conflicts)
    
    print(f"\nTotal Conflicts: {total_conflicts}")
    print(f"Conflict Penalty: {-2 * total_conflicts:.4f}")
    print(f"FINAL FITNESS: {fitness:.4f}")
    print("=" * 60)


def display_schedule_structure(schedule):
    """
    Display the structure of a schedule showing all courses with their class_nbr.
    Useful for verifying that each class_nbr is treated as a separate course.
    """
    print("\n" + "=" * 60)
    print("SCHEDULE STRUCTURE")
    print("=" * 60)
    print(f"{'Subject':<10} {'Catalog':<10} {'Class_Nbr':<12} {'Lectures':<10} {'Labs':<8} {'Tutorials':<10}")
    print("-" * 60)
    
    for course in schedule:
        lec_info = f"{course.lecture.start}-{course.lecture.end}" if course.lecture else "None"
        lab_info = f"{course.lab_count}" if course.lab_count > 0 else "0"
        tut_info = f"{course.tut_count}" if course.tut_count > 0 else "0"
        
        print(f"{course.subject:<10} {course.catalog_nbr:<10} {course.class_nbr:<12} {lec_info:<10} {lab_info:<8} {tut_info:<10}")
    
    print("=" * 60)
    print(f"Total courses in schedule: {len(schedule)}")
    
    # Count unique subject+catalog combinations
    unique_courses = set()
    for course in schedule:
        unique_courses.add(f"{course.subject}{course.catalog_nbr}")
    print(f"Unique subject+catalog combinations: {len(unique_courses)}")
    print("=" * 60)


# Usage example:
# from sequence import Sequence
# seq = Sequence()
#
# # Display schedule structure to verify class_nbr handling
# display_schedule_structure(population[0])
#
# # Evaluate population with core sequences
# fitness_scores = evaluate_population(population, core_sequences=seq.year)
#
# # Display detailed breakdown for best schedule
# best_idx = fitness_scores.index(max(fitness_scores))
# display_fitness_details(population[best_idx], core_sequences=seq.year)