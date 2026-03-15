from dataclasses import dataclass

@dataclass(frozen=True, slots=True)

class TimeBlock:
    day: int
    start: int
    end: int


def overlaps(a,b):

    if a.day != b.day:
        return False
    return (a.start < b.end) and (b.start < a.end)

def overlaps_any(block,blocks):

    for other in blocks:
        if overlaps(block,other):
            return True
    return False

def m(hh,mm):

    return hh*60 + mm

def format_time(mins):

    hh = mins//60
    mm = mins%60

    return f"{hh:02d}:{mm:02d}"

def slot_block(day,start,duration):

    return TimeBlock(day=day,start=start, end = start+duration)

def to_minutes(t) -> int:
    if isinstance(t, int):
        return t


    if hasattr(t, "hour") and hasattr(t, "minute"):
        return t.hour * 60 + t.minute


    s = str(t)
    hh, mm = s.split(":")[0], s.split(":")[1]
    return int(hh) * 60 + int(mm)
