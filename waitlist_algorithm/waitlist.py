from typing import Dict,List, Tuple
from time_block import TimeBlock, overlaps_any, slot_block

StudentID = int
DayCode = int
Minutes = int
SlotKey = Tuple[DayCode, Minutes]

def propose_waitlist_slots(
        waitlisted_students: List[StudentID],
        students_busy: Dict[StudentID, List[TimeBlock]],
        room_busy: List[TimeBlock],
        lecture_blocks: List[TimeBlock],
        lab_start_time:List[Minutes],
        lab_duration_min: int = 180,

):
 pass