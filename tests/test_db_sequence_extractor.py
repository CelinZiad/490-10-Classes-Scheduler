import pytest
from helper.db_sequence_extractor import (
    should_include_course,
    season_to_number,
)


# --- should_include_course ---

def test_include_coen():
    assert should_include_course("COEN", "311") is True


def test_include_elec():
    assert should_include_course("ELEC", "273") is True


def test_include_engr_290():
    assert should_include_course("ENGR", "290") is True


def test_exclude_math():
    assert should_include_course("MATH", "201") is False


# --- season_to_number ---

def test_season_fall():
    assert season_to_number("fall") == 2


def test_season_winter():
    assert season_to_number("winter") == 4


def test_season_summer():
    assert season_to_number("summer") == 6


def test_season_unknown():
    assert season_to_number("spring") == 0


def test_season_case_insensitive():
    assert season_to_number("Fall") == 2
    assert season_to_number("WINTER") == 4
