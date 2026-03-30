import datetime as dt
from unittest.mock import MagicMock

import pytest

from waitlist_algorithm.algorithm.database_results import (
    minutes_to_time,
    save_lab_results_to_db,
)


def test_minutes_to_time_basic_conversion():
    t = minutes_to_time(525)
    assert t == dt.time(8, 45)


def test_save_lab_results_to_db_no_results_does_not_execute():
    cur = MagicMock()

    save_lab_results_to_db(
        cur=cur,
        subject="COEN",
        catalog="352",
        lab_duration_min=110,
        results={},
    )

    cur.execute.assert_not_called()


def test_save_lab_results_to_db_single_insert_values():
    cur = MagicMock()

    results = {
        (1, 525): [1001, 1002],
    }

    save_lab_results_to_db(
        cur=cur,
        subject="COEN",
        catalog="352",
        lab_duration_min=110,
        results=results,
    )

    # 1 DELETE + 1 INSERT
    assert cur.execute.call_count == 2

    del_sql, del_params = cur.execute.call_args_list[0][0]
    assert "DELETE FROM lab_slot_result" in del_sql
    assert del_params == ("COEN", "352")

    sql, params = cur.execute.call_args_list[1][0]

    assert "INSERT INTO lab_slot_result" in sql
    assert params[0] == "COEN"
    assert params[1] == "352"
    assert params[2] == dt.time(8, 45)
    assert params[3] == dt.time(10, 35)

    assert params[4] is True
    assert params[5] is False
    assert params[6] is False
    assert params[7] is False
    assert params[8] is False
    assert params[9] is False
    assert params[10] is False

    assert params[11] == [1001, 1002]
    assert params[12] == 1


def test_save_lab_results_to_db_multiple_rows_and_isodow_mapping():
    cur = MagicMock()

    results = {
        (1, 600): [1],
        (7, 600): [2],
        (8, 600): [3],
    }

    save_lab_results_to_db(
        cur=cur,
        subject="ENGR",
        catalog="101",
        lab_duration_min=60,
        results=results,
    )

    # 1 DELETE + 3 INSERTs
    assert cur.execute.call_count == 4

    # Skip the DELETE (index 0), get INSERT params only
    calls = [c[0][1] for c in cur.execute.call_args_list[1:]]

    monday = calls[0]
    sunday = calls[1]
    monday_week2 = calls[2]

    assert monday[4] is True
    assert monday[10] is False
    assert monday[12] == 1

    assert sunday[10] is True
    assert sunday[4] is False
    assert sunday[12] == 1

    assert monday_week2[4] is True
    assert monday_week2[12] == 2


def test_save_lab_results_to_db_casts_studyids_to_int():
    cur = MagicMock()

    results = {
        (3, 540): ["10", "20"],
    }

    save_lab_results_to_db(
        cur=cur,
        subject="COEN",
        catalog="999",
        lab_duration_min=30,
        results=results,
    )

    _, params = cur.execute.call_args_list[1][0]

    assert params[11] == [10, 20]
    assert params[12] == 1
