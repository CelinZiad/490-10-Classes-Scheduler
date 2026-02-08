from typing import Dict,List, Tuple
from .time_block import TimeBlock, overlaps_any, slot_block

def propose_waitlist_slots(
        waitlisted_students,
        students_busy,
        room_busy,
        lab_start_times,
        lab_duration_min= 180 ,

):

    results = {}


    day_canditates = list(range(1,6))+ list(range(8,13))

    for day in day_canditates:
        for start in lab_start_times:
            canditates = slot_block(day, start, lab_duration_min)


            if overlaps_any(canditates, room_busy):
                continue


            available_student = []
            for student_id in waitlisted_students:
                busy_blocks = students_busy.get(student_id, [])
                if not overlaps_any(canditates,busy_blocks):
                    available_student.append(student_id)


            if available_student:
                results[day,start] = available_student

    return results




