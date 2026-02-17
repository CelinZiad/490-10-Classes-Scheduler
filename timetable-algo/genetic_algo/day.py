# day.py
from __future__ import annotations
from enum import Enum
from typing import Tuple, List
import re

class Day(Enum):
    MO = (1, 8)
    TU = (2, 9)
    WE = (3, 10)
    TH = (4, 11)
    FR = (5, 12)
    SA = (6, 13)
    SU = (7, 14)

    @property
    def first(self) -> int:
        return self.value[0]

    @property
    def second(self) -> int:
        return self.value[1]

    def as_list(self) -> List[int]:
        return list(self.value)


_DAY_TOKEN_TO_ENUM = {
    "Mo": Day.MO, "Tu": Day.TU, "We": Day.WE, "Th": Day.TH,
    "Fr": Day.FR, "Sa": Day.SA, "Su": Day.SU,
}


def parse_day_pattern(raw: str) -> Tuple[Day, ...]:
    """Parse day patterns like 'MoWe' -> (Day.MO, Day.WE), 'TuTh' -> (Day.TU, Day.TH)."""
    s = (raw or "").strip()
    if not s:
        raise ValueError("day_of_week is empty")

    s = re.sub(r"[\s,/;-]+", "", s)

    days: list[Day] = []
    i = 0
    while i < len(s):
        token = s[i : i + 2]
        if token not in _DAY_TOKEN_TO_ENUM:
            raise ValueError(f"Invalid day token '{token}' in '{raw}'")
        days.append(_DAY_TOKEN_TO_ENUM[token])
        i += 2

    return tuple(days)
