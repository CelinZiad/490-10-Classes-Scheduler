from lab_generator import propose_waitlist_slots
from time_block import TimeBlock,format_time,m
from waitlisted_students import get_waitlisted_students_from_user_and_db
from db import get_conn



lab_start_times= [m(8,45),m(11,45),m(14,45),m(17,45)]

def main():


    # We'll only search ONE standard lab start time ( for predictable output)
    lab_start_time = [m(8,45),m(11,45),m(14,45),m(17,45)
                      ]

    room_busy = [
        TimeBlock(day= 1,start=m(8,45),end= m(11,45)),
        TimeBlock(day=2, start=m(14, 45), end=m(17, 45)),
        TimeBlock(day=3, start=m(14, 45), end=m(17, 45)),
        TimeBlock(day=5, start=m(14, 45), end=m(17, 45))]

    students_busy = {
        12345678: [
            TimeBlock(day=1, start=m(8, 45), end=m(11, 45)),
            TimeBlock(day=2, start=m(11, 45), end=m(14, 45)),
            TimeBlock(day=3, start=m(17, 45), end=m(20, 45)),
            TimeBlock(day=8, start=m(8, 45), end=m(11, 45)),
            TimeBlock(day=10, start=m(11, 45), end=m(14, 45)),
        ],
        23456789: [
            TimeBlock(day=1, start=m(11, 45), end=m(14, 45)),
            TimeBlock(day=4, start=m(8, 45), end=m(11, 45)),
            TimeBlock(day=5, start=m(17, 45), end=m(20, 45)),
            TimeBlock(day=8, start=m(11, 45), end=m(14, 45)),
            TimeBlock(day=12, start=m(8, 45), end=m(11, 45)),
        ],
        34567890: [
            TimeBlock(day=2, start=m(8, 45), end=m(11, 45)),
            TimeBlock(day=3, start=m(11, 45), end=m(14, 45)),
            TimeBlock(day=4, start=m(17, 45), end=m(20, 45)),
            TimeBlock(day=9, start=m(14, 45), end=m(17, 45)),  # <-- BUSY at the candidate slot
            TimeBlock(day=11, start=m(8, 45), end=m(11, 45)),
        ],
        45678901: [
            TimeBlock(day=1, start=m(17, 45), end=m(20, 45)),
            TimeBlock(day=2, start=m(8, 45), end=m(11, 45)),
            TimeBlock(day=5, start=m(11, 45), end=m(14, 45)),
            TimeBlock(day=10, start=m(17, 45), end=m(20, 45)),
            TimeBlock(day=12, start=m(11, 45), end=m(14, 45)),
        ],
        56789012: [
            TimeBlock(day=1, start=m(8, 45), end=m(11, 45)),
            TimeBlock(day=3, start=m(8, 45), end=m(11, 45)),
            TimeBlock(day=5, start=m(8, 45), end=m(11, 45)),
            TimeBlock(day=9, start=m(14, 45), end=m(17, 45)),  # <-- BUSY at the candidate slot
            TimeBlock(day=11, start=m(11, 45), end=m(14, 45)),
        ],
    }
    cur = get_conn().cursor()

    waitlisted_students= get_waitlisted_students_from_user_and_db(cur)

    results = propose_waitlist_slots(waitlisted_students= waitlisted_students, students_busy= students_busy,room_busy= room_busy,lab_start_times= lab_start_time)

    print("\n--- Proposed Lab Slots ---")
    for(day,start), students in sorted(results.items()):
        print(f"{day},{format_time(start)},"+",".join(str(s)for s in students))


if __name__ == "__main__":
    main()


