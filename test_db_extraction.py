#!/usr/bin/env python3
"""
Test script for database room extraction.
Run this to verify database connectivity and Room_data.csv generation.
"""

from db_room_extractor import (
    verify_database_connection,
    fetch_lab_rooms,
    fetch_course_lab_assignments,
    group_courses_by_room,
    extract_and_generate_room_data
)

def test_database_connection():
    """Test basic database connectivity."""
    print("\n" + "=" * 70)
    print("TEST 1: Database Connection")
    print("=" * 70)
    
    result = verify_database_connection()
    if result:
        print("✓ PASSED: Database connection successful")
    else:
        print("✗ FAILED: Database connection failed")
    
    return result


def test_fetch_lab_rooms():
    """Test fetching lab room data."""
    print("\n" + "=" * 70)
    print("TEST 2: Fetch Lab Rooms")
    print("=" * 70)
    
    try:
        lab_rooms = fetch_lab_rooms()
        print(f"✓ PASSED: Retrieved {len(lab_rooms)} lab rooms")
        
        # Display first few rooms
        print("\nSample lab rooms:")
        for labroomid in sorted(lab_rooms.keys())[:5]:
            room = lab_rooms[labroomid]
            print(f"  ID {labroomid}: {room['building']}-{room['room']} "
                  f"(capacity: {room['capacity']}/{room['capacitymax']})")
        
        return True
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_fetch_course_assignments():
    """Test fetching course-lab assignments."""
    print("\n" + "=" * 70)
    print("TEST 3: Fetch Course Assignments")
    print("=" * 70)
    
    try:
        assignments = fetch_course_lab_assignments()
        print(f"✓ PASSED: Retrieved {len(assignments)} course assignments")
        
        # Display first few assignments
        print("\nSample assignments:")
        for assignment in assignments[:5]:
            print(f"  {assignment['subject']} {assignment['catalog']} -> "
                  f"Room ID {assignment['labroomid']}")
        
        return True
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_group_courses():
    """Test grouping courses by room."""
    print("\n" + "=" * 70)
    print("TEST 4: Group Courses by Room")
    print("=" * 70)
    
    try:
        assignments = fetch_course_lab_assignments()
        room_courses = group_courses_by_room(assignments)
        
        print(f"✓ PASSED: Grouped into {len(room_courses)} rooms")
        
        # Display sample grouping
        print("\nSample groupings:")
        for labroomid in sorted(room_courses.keys())[:5]:
            courses = room_courses[labroomid]
            course_list = [f"{subj}{cat}" for subj, cat in courses[:3]]
            if len(courses) > 3:
                course_list.append(f"... and {len(courses) - 3} more")
            print(f"  Room ID {labroomid}: {', '.join(course_list)}")
        
        return True
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_generate_csv():
    """Test generating Room_data.csv."""
    print("\n" + "=" * 70)
    print("TEST 5: Generate Room_data.csv")
    print("=" * 70)
    
    try:
        success = extract_and_generate_room_data(
            output_path="Room_data_test.csv",
            show_summary=True
        )
        
        if success:
            print("✓ PASSED: Room_data_test.csv generated successfully")
            
            # Verify file contents
            import csv
            with open("Room_data_test.csv", 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                print(f"\nVerification:")
                print(f"  Total rows: {len(rows)}")
                print(f"  Columns: {', '.join(reader.fieldnames)}")
            
            return True
        else:
            print("✗ FAILED: Could not generate CSV")
            return False
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "=" * 70)
    print("DATABASE ROOM EXTRACTOR TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Fetch Lab Rooms", test_fetch_lab_rooms),
        ("Fetch Course Assignments", test_fetch_course_assignments),
        ("Group Courses by Room", test_group_courses),
        ("Generate CSV", test_generate_csv)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ EXCEPTION in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return True
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
