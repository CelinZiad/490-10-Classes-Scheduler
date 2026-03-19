# academic_calendar.py
"""
Academic calendar date calculations for Concordia University schedule generation.

Season codes:
  1 = Summer
  2 = Fall
  3 = Fall+Winter (8-month span)
  4 = Winter

Session codes (summer only):
  "13W" = 4-month (May–August)
  "6H1" = 6-week first half (May–June)
  "6H2" = 6-week second half (July–August)

Day numbering in the genetic algorithm:
  Days 1–5  = Week 1 (Mon–Fri)
  Days 8–12 = Week 2 (Mon–Fri)

Labs are biweekly. A lab on days 1–5 starts in "Week A" (2 weeks after semester start).
A lab on days 8–12 starts in "Week B" (3 weeks after semester start, i.e. one week after Week A).
Subsequent labs are every 2 weeks, except for a 3-week gap over reading week.

Each lab section produces 6 meeting pattern rows (meetingpatternnumber 1–6).
"""

from datetime import date, timedelta
from typing import List, Tuple, Optional


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _monday_on_or_after(d: date) -> date:
    """Return *d* itself if it is a Monday, otherwise the next Monday."""
    days_ahead = (7 - d.weekday()) % 7  # weekday(): Mon=0
    return d + timedelta(days=days_ahead)


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """Return the *n*-th occurrence of *weekday* (0=Mon) in the given month."""
    first = date(year, month, 1)
    first_weekday = first.weekday()
    diff = (weekday - first_weekday) % 7
    return first + timedelta(days=diff + 7 * (n - 1))


def labour_day(year: int) -> date:
    """First Monday in September."""
    return _nth_weekday_of_month(year, 9, 0, 1)  # 0 = Monday


def canada_day(year: int) -> date:
    """July 1."""
    return date(year, 7, 1)


def _day_number_to_weekday_offset(day_num: int) -> int:
    """Convert GA day number (1-5 or 8-12) to weekday offset from Monday (0-4)."""
    if 1 <= day_num <= 5:
        return day_num - 1
    elif 8 <= day_num <= 12:
        return day_num - 8
    raise ValueError(f"Invalid day number: {day_num}")


def _is_week1(day_num: int) -> bool:
    return 1 <= day_num <= 5


def _is_week2(day_num: int) -> bool:
    return 8 <= day_num <= 12


def _week_start_end(target_date: date) -> Tuple[date, date]:
    """Return (Monday, Saturday) of the week containing *target_date*."""
    monday = target_date - timedelta(days=target_date.weekday())
    saturday = monday + timedelta(days=5)
    return monday, saturday


# ---------------------------------------------------------------------------
# Semester anchor dates
# ---------------------------------------------------------------------------

class SemesterDates:
    """Holds all key dates for a given semester/session."""

    def __init__(self, year: int, season: int, session: str = "13W"):
        self.year = year
        self.season = season
        self.session = session

        # Compute all anchors
        if season == 2:       # Fall
            self._init_fall(year)
        elif season == 4:     # Winter
            self._init_winter(year)
        elif season == 3:     # Fall+Winter
            self._init_fall_winter(year)
        elif season == 1:     # Summer
            if session == "6H1":
                self._init_summer_6h1(year)
            elif session == "6H2":
                self._init_summer_6h2(year)
            else:
                self._init_summer_13w(year)

    # -- Fall ---------------------------------------------------------------
    def _init_fall(self, year: int):
        ld = labour_day(year)
        self.classes_start = ld + timedelta(days=1)  # day after Labour Day (Tuesday)
        self.classes_end = _nth_weekday_of_month(year, 12, 0, 1)  # first Monday in December

        # Labs begin 2 weeks after Labour Day
        self.lab_week_a_start = ld + timedelta(weeks=2)  # Monday, 2 weeks after LD
        self.lab_week_b_start = self.lab_week_a_start + timedelta(weeks=1)

        # Reading week: 7th week after semester begins
        # Semester week 1 starts on classes_start's Monday
        sem_monday = self.classes_start - timedelta(days=self.classes_start.weekday())
        self.reading_week_start = sem_monday + timedelta(weeks=6)  # week 7 (0-indexed week 6)

        self.has_reading_week = True
        self.lab_count = 6
        self.weekly_labs = False

    # -- Winter -------------------------------------------------------------
    def _init_winter(self, year: int):
        # Second Monday in January
        self.classes_start = _nth_weekday_of_month(year, 1, 0, 2)
        # Second Monday in April
        self.classes_end = _nth_weekday_of_month(year, 4, 0, 2)

        # Labs begin 2 weeks after first week of classes
        self.lab_week_a_start = self.classes_start + timedelta(weeks=2)
        self.lab_week_b_start = self.lab_week_a_start + timedelta(weeks=1)

        # Reading week: first week of March
        self.reading_week_start = _nth_weekday_of_month(year, 3, 0, 1)

        self.has_reading_week = True
        self.lab_count = 6
        self.weekly_labs = False

    # -- Fall + Winter (8-month) -------------------------------------------
    def _init_fall_winter(self, year: int):
        ld = labour_day(year)
        self.classes_start = ld + timedelta(days=1)
        # End same as winter of next year
        next_year = year + 1
        self.classes_end = _nth_weekday_of_month(next_year, 4, 0, 2)

        # Labs same as fall start
        self.lab_week_a_start = ld + timedelta(weeks=2)
        self.lab_week_b_start = self.lab_week_a_start + timedelta(weeks=1)

        # Reading week same as fall
        sem_monday = self.classes_start - timedelta(days=self.classes_start.weekday())
        self.reading_week_start = sem_monday + timedelta(weeks=6)

        self.has_reading_week = True
        self.lab_count = 6
        self.weekly_labs = False

    # -- Summer 13W (May–August, 4 months) ---------------------------------
    def _init_summer_13w(self, year: int):
        # Second Monday in May
        self.classes_start = _nth_weekday_of_month(year, 5, 0, 2)
        # Second Wednesday in August
        second_wed_aug = _nth_weekday_of_month(year, 8, 2, 2)  # 2 = Wednesday
        self.classes_end = second_wed_aug

        # Labs begin 2 weeks after classes start
        self.lab_week_a_start = self.classes_start + timedelta(weeks=2)
        self.lab_week_b_start = self.lab_week_a_start + timedelta(weeks=1)

        # Reading week for 13W: the day after the 6H1 classenddate, lasting 7 days
        # 6H1 ends 6 weeks after classes_start (which is also the 13W start)
        h1_end = self.classes_start + timedelta(weeks=6) - timedelta(days=1)
        # The reading week starts the day after 6H1 ends
        # But more precisely: 6H1 classenddate = 6 weeks after classstartdate
        # so reading week Monday = classes_start + 6 weeks
        self.reading_week_start = self.classes_start + timedelta(weeks=6)

        self.has_reading_week = True
        self.lab_count = 6
        self.weekly_labs = False

    # -- Summer 6H1 (May–June, 6 weeks) ------------------------------------
    def _init_summer_6h1(self, year: int):
        self.classes_start = _nth_weekday_of_month(year, 5, 0, 2)
        # classenddate is 6 weeks after classstartdate
        self.classes_end = self.classes_start + timedelta(weeks=6)

        # Labs are weekly for 6H sessions
        self.lab_week_a_start = self.classes_start + timedelta(weeks=1)
        self.lab_week_b_start = self.lab_week_a_start  # same (weekly)

        self.has_reading_week = False
        self.reading_week_start = None
        self.lab_count = 6
        self.weekly_labs = True

    # -- Summer 6H2 (July–August, 6 weeks) ---------------------------------
    def _init_summer_6h2(self, year: int):
        # classstartdate = day after Canada Day
        cd = canada_day(year)
        self.classes_start = cd + timedelta(days=1)

        # classenddate = second Wednesday in August
        self.classes_end = _nth_weekday_of_month(year, 8, 2, 2)

        # Labs are weekly
        self.lab_week_a_start = self.classes_start + timedelta(weeks=1)
        self.lab_week_b_start = self.lab_week_a_start

        self.has_reading_week = False
        self.reading_week_start = None
        self.lab_count = 6
        self.weekly_labs = True


# ---------------------------------------------------------------------------
# Lecture / Tutorial date ranges
# ---------------------------------------------------------------------------

def get_lec_tut_dates(sem: SemesterDates) -> Tuple[date, date]:
    """Return (classstartdate, classenddate) for lectures and tutorials."""
    return (sem.classes_start, sem.classes_end)


# ---------------------------------------------------------------------------
# Lab meeting-pattern date calculations
# ---------------------------------------------------------------------------

def compute_lab_meeting_dates(
    sem: SemesterDates,
    day_numbers: List[int],
    num_meetings: int = 6,
) -> List[Tuple[date, date]]:
    """
    Compute (classstartdate, classenddate) for each meeting pattern (1..num_meetings).

    *day_numbers* are the GA day codes for ONE lab section (e.g. [2] or [2, 9]).

    Returns a list of (start_date, end_date) tuples — one per meeting pattern.
    Each date pair brackets the week containing the actual lab day.
    """
    if not day_numbers:
        return []

    # Determine if the lab falls in Week A (days 1-5) or Week B (days 8-12)
    has_week1 = any(_is_week1(d) for d in day_numbers)
    has_week2 = any(_is_week2(d) for d in day_numbers)

    # Pick a representative weekday offset (0=Mon .. 4=Fri)
    representative_day = day_numbers[0]
    weekday_offset = _day_number_to_weekday_offset(representative_day)

    if sem.weekly_labs:
        # 6H1/6H2: labs are weekly, output as 1 row with session date range
        return [(sem.classes_start, sem.classes_end)]

    # Biweekly labs
    # The first lab's week depends on whether the lab is in Week A or Week B
    if has_week1:
        first_lab_week_monday = sem.lab_week_a_start
    elif has_week2:
        first_lab_week_monday = sem.lab_week_b_start
    else:
        first_lab_week_monday = sem.lab_week_a_start

    first_lab_date = first_lab_week_monday + timedelta(days=weekday_offset)

    # Generate all 6 meeting dates with biweekly spacing + reading week gap
    meeting_dates: List[date] = []
    current = first_lab_date

    for i in range(num_meetings):
        meeting_dates.append(current)

        # Advance 2 weeks normally
        next_date = current + timedelta(weeks=2)

        # Check if reading week falls between current and next_date
        if sem.has_reading_week and sem.reading_week_start is not None:
            reading_start = sem.reading_week_start
            reading_end = reading_start + timedelta(days=6)  # Sunday of reading week

            # If the next lab would land during reading week, push it one more week
            if reading_start <= next_date <= reading_end:
                next_date += timedelta(weeks=1)
            # If reading week falls strictly between current and next, the gap
            # absorbs the extra week (3-week gap instead of 2)
            elif current < reading_start < next_date:
                next_date += timedelta(weeks=1)

        current = next_date

    # Convert each meeting date to a (week_start, week_end) pair
    results: List[Tuple[date, date]] = []
    for md in meeting_dates:
        ws, we = _week_start_end(md)
        results.append((ws, we))

    return results


def _compute_weekly_lab_dates(
    sem: SemesterDates,
    weekday_offset: int,
    num_meetings: int,
) -> List[Tuple[date, date]]:
    """Compute meeting dates for weekly labs (6H1, 6H2 summer sessions)."""
    first_lab_week_monday = sem.lab_week_a_start
    first_lab_date = first_lab_week_monday + timedelta(days=weekday_offset)

    meeting_dates: List[date] = []
    current = first_lab_date

    for _ in range(num_meetings):
        meeting_dates.append(current)
        current += timedelta(weeks=1)

    results: List[Tuple[date, date]] = []
    for md in meeting_dates:
        ws, we = _week_start_end(md)
        results.append((ws, we))

    return results


# ---------------------------------------------------------------------------
# Public convenience
# ---------------------------------------------------------------------------

def get_session_code(season: int, previous_session: str = None) -> str:
    """Get session code based on season."""
    if season == 2 or season == 4:
        return "13W"
    elif season == 3:
        return "26W"
    elif season == 1:
        return previous_session if previous_session else "13W"
    return "13W"


def format_date(d: Optional[date]) -> Optional[str]:
    """Format a date as YYYY-MM-DD string, or None."""
    return d.isoformat() if d else None