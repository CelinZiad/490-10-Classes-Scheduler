from waitlist_algorithm.time_block import TimeBlock, minutes, overlaps, overlaps_any, slot_block


def test_minutes():
    assert minutes(8, 45) == 8 * 60 + 45
    assert minutes(0, 0) == 0
    assert minutes(23, 59) == 23 * 60 + 59


def test_overlaps_same_day_true():
    a = TimeBlock(day=1, start=500, end=600)
    b = TimeBlock(day=1, start=550, end=650)
    assert overlaps(a, b)


def test_overlaps_same_day_false_touching_edges():
    a = TimeBlock(day=1, start=500, end=600)
    b = TimeBlock(day=1, start=600, end=700)
    assert not overlaps(a, b)


def test_overlaps_false_different_days():
    a = TimeBlock(day=1, start=500, end=600)
    b = TimeBlock(day=2, start=550, end=650)
    assert not overlaps(a, b)


def test_overlaps_any():
    candidate = TimeBlock(day=3, start=600, end=780)
    busy = [
        TimeBlock(day=3, start=500, end=550),
        TimeBlock(day=3, start=700, end=800),  # overlaps
        TimeBlock(day=4, start=600, end=780),
    ]
    assert overlaps_any(candidate, busy)


def test_slot_block_end_time():
    tb = slot_block(day=5, start=525, duration=180)
    assert tb.start == 525
    assert tb.end == 705
