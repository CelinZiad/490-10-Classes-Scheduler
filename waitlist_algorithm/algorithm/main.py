from lab_generator import propose_waitlist_slots
from time_block import format_time,m

from waitlist_algorithm.algorithm.students_busy import load_students_busy_from_db
from waitlist_algorithm.algorithm.room_busy import load_room_busy_for_course
from users_prompt import get_waitlisted_students_and_course_from_user

from waitlist_algorithm.database_connection.db import get_conn




def main():



    lab_start_time = [m(8,45),m(11,45),m(14,45),m(17,45)]


    cur = get_conn().cursor()



    waitlisted_students,course= get_waitlisted_students_and_course_from_user(cur)
    subject, catalog = course

    students_busy = load_students_busy_from_db(cur, waitlisted_students)
    room_busy = load_room_busy_for_course(cur, subject,catalog)



    results = propose_waitlist_slots(waitlisted_students= waitlisted_students, students_busy= students_busy,room_busy= room_busy,lab_start_times= lab_start_time)

    print("\n--- Proposed Lab Slots ---")
    for(day,start), students in sorted(results.items()):
        print(f"{day},{format_time(start)},"+",".join(str(s)for s in students))


if __name__ == "__main__":
    main()


