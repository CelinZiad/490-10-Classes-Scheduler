# test_waitlist.py
import unittest

from waitlist_algorithm.lab_generator import propose_waitlist_slots
from waitlist_algorithm.time_block import TimeBlock,m




class TestWaitlist(unittest.TestCase):

    def test_slot_available_includes_free_students(self):
        # One candidate slot: day 9 @ 14:45
        waitlisted = [111, 222]
        students_busy = {111: [], 222: []}
        room_busy = []
        lab_start_times = [m(14, 45)]

        results = propose_waitlist_slots(
            waitlisted_students=waitlisted,
            students_busy=students_busy,
            room_busy=room_busy,
            lab_start_times=lab_start_times,
        )

        self.assertIn((9, m(14, 45)), results)
        self.assertEqual(results[(9, m(14, 45))], [111, 222])

    def test_room_busy_blocks_slot(self):
        waitlisted = [111]
        students_busy = {111: []}
        lab_start_times = [m(14, 45)]

        # Room is busy exactly during the candidate slot on day 9
        room_busy = [TimeBlock(day=9, start=m(14, 45), end=m(17, 45))]

        results = propose_waitlist_slots(
            waitlisted_students=waitlisted,
            students_busy=students_busy,
            room_busy=room_busy,
            lab_start_times=lab_start_times,
        )

        self.assertNotIn((9, m(14, 45)), results)


    def test_student_busy_excluded_but_slot_still_returned_for_others(self):
        waitlisted = [111, 222]
        room_busy = []
        lab_start_times = [m(14, 45)]

        # Student 111 is busy during candidate slot, 222 is free
        students_busy = {
            111: [TimeBlock(day=9, start=m(14, 45), end=m(17, 45))],
            222: [],
        }

        results = propose_waitlist_slots(
            waitlisted_students=waitlisted,
            students_busy=students_busy,
            room_busy=room_busy,
            lab_start_times=lab_start_times,
        )

        self.assertIn((9, m(14, 45)), results)
        self.assertEqual(results[(9, m(14, 45))], [222])

    def test_biweekly_day_9_is_considered(self):
        # This test specifically checks that day=9 appears in the search space.
        waitlisted = [111]
        students_busy = {111: []}
        room_busy = []
        lab_start_times = [m(14, 45)]

        results = propose_waitlist_slots(
            waitlisted_students=waitlisted,
            students_busy=students_busy,
            room_busy=room_busy,
            lab_start_times=lab_start_times,
        )

        # If day 9 isn't in the candidate days, this would never show up.
        self.assertIn((9, m(14, 45)), results)


if __name__ == "__main__":
    unittest.main()
