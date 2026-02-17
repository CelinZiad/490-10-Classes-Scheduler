import pytest
from day import Day, parse_day_pattern


def test_day_enum_values():
    assert Day.MO.value == (1, 8)
    assert Day.TU.value == (2, 9)
    assert Day.WE.value == (3, 10)
    assert Day.TH.value == (4, 11)
    assert Day.FR.value == (5, 12)


def test_day_first_second_properties():
    assert Day.MO.first == 1
    assert Day.MO.second == 8
    assert Day.FR.first == 5
    assert Day.FR.second == 12


def test_day_as_list():
    assert Day.MO.as_list() == [1, 8]
    assert Day.WE.as_list() == [3, 10]


def test_parse_day_pattern_two_days():
    result = parse_day_pattern("MoWe")
    assert result == (Day.MO, Day.WE)


def test_parse_day_pattern_tuth():
    result = parse_day_pattern("TuTh")
    assert result == (Day.TU, Day.TH)


def test_parse_day_pattern_single():
    result = parse_day_pattern("Mo")
    assert result == (Day.MO,)


def test_parse_day_pattern_invalid_raises():
    with pytest.raises(ValueError):
        parse_day_pattern("Xx")


def test_parse_day_pattern_empty_raises():
    with pytest.raises(ValueError):
        parse_day_pattern("")
