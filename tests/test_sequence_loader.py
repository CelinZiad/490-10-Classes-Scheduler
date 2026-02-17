import os
import csv
import pytest
from helper.sequence_loader import SequenceTerm, SequencePlan, SequenceManager, Sequence


def _write_csv(path, rows):
    """Write a CSV file from a list of dicts."""
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _sample_rows():
    return [
        {
            'planid': '1', 'planname': 'COEN-General',
            'program': 'COEN', 'sequencetermid': '10',
            'yearnumber': '1', 'season': 'fall', 'season_code': '2',
            'courses': 'COEN212,COEN231,COEN243'
        },
        {
            'planid': '1', 'planname': 'COEN-General',
            'program': 'COEN', 'sequencetermid': '11',
            'yearnumber': '1', 'season': 'winter', 'season_code': '4',
            'courses': 'COEN244,COEN311,ELEC273'
        },
        {
            'planid': '2', 'planname': 'ELEC-General',
            'program': 'ELEC', 'sequencetermid': '20',
            'yearnumber': '1', 'season': 'fall', 'season_code': '2',
            'courses': 'ELEC273,ELEC275'
        },
    ]


# --- SequenceTerm ---

def test_sequence_term_repr():
    term = SequenceTerm(
        sequencetermid=10, planid=1, planname='COEN-General',
        program='COEN', yearnumber=1, season='fall', season_code=2,
        courses=['COEN212', 'COEN231']
    )
    assert 'Y1' in repr(term)
    assert 'fall' in repr(term)


# --- SequencePlan ---

def test_plan_get_terms_for_season():
    t1 = SequenceTerm(10, 1, 'P', 'COEN', 1, 'fall', 2, ['COEN212'])
    t2 = SequenceTerm(11, 1, 'P', 'COEN', 1, 'winter', 4, ['COEN311'])
    plan = SequencePlan(planid=1, planname='P', program='COEN', terms=[t1, t2])
    fall_terms = plan.get_terms_for_season(2)
    assert len(fall_terms) == 1
    assert fall_terms[0].season == 'fall'


def test_plan_get_all_course_lists():
    t1 = SequenceTerm(10, 1, 'P', 'COEN', 1, 'fall', 2, ['COEN212', 'COEN231'])
    t2 = SequenceTerm(11, 1, 'P', 'COEN', 1, 'winter', 4, ['COEN311'])
    plan = SequencePlan(planid=1, planname='P', program='COEN', terms=[t1, t2])
    lists = plan.get_all_course_lists()
    assert len(lists) == 2
    assert 'COEN212' in lists[0]


def test_plan_repr():
    plan = SequencePlan(planid=1, planname='COEN-General', program='COEN', terms=[])
    assert 'COEN-General' in repr(plan)


# --- SequenceManager ---

def test_manager_load(tmp_path):
    csv_path = str(tmp_path / "seq.csv")
    _write_csv(csv_path, _sample_rows())
    mgr = SequenceManager(csv_path)
    assert len(mgr.plans) == 2
    assert 1 in mgr.plans
    assert 2 in mgr.plans


def test_manager_get_plan(tmp_path):
    csv_path = str(tmp_path / "seq.csv")
    _write_csv(csv_path, _sample_rows())
    mgr = SequenceManager(csv_path)
    plan = mgr.get_plan(1)
    assert plan is not None
    assert plan.planname == 'COEN-General'


def test_manager_get_plan_missing(tmp_path):
    csv_path = str(tmp_path / "seq.csv")
    _write_csv(csv_path, _sample_rows())
    mgr = SequenceManager(csv_path)
    assert mgr.get_plan(999) is None


def test_manager_get_all_plans(tmp_path):
    csv_path = str(tmp_path / "seq.csv")
    _write_csv(csv_path, _sample_rows())
    mgr = SequenceManager(csv_path)
    plans = mgr.get_all_plans()
    assert len(plans) == 2


def test_manager_get_plans_by_program(tmp_path):
    csv_path = str(tmp_path / "seq.csv")
    _write_csv(csv_path, _sample_rows())
    mgr = SequenceManager(csv_path)
    coen_plans = mgr.get_plans_by_program('COEN')
    assert len(coen_plans) == 1
    elec_plans = mgr.get_plans_by_program('ELEC')
    assert len(elec_plans) == 1


def test_manager_get_all_course_sequences(tmp_path):
    csv_path = str(tmp_path / "seq.csv")
    _write_csv(csv_path, _sample_rows())
    mgr = SequenceManager(csv_path)
    seqs = mgr.get_all_course_sequences()
    assert len(seqs) == 3


def test_manager_get_sequences_for_season(tmp_path):
    csv_path = str(tmp_path / "seq.csv")
    _write_csv(csv_path, _sample_rows())
    mgr = SequenceManager(csv_path)
    fall_seqs = mgr.get_course_sequences_for_season(2)
    assert len(fall_seqs) == 2  # COEN fall + ELEC fall
    winter_seqs = mgr.get_course_sequences_for_season(4)
    assert len(winter_seqs) == 1


def test_manager_empty_csv(tmp_path):
    csv_path = str(tmp_path / "seq.csv")
    _write_csv(csv_path, [])
    # Empty file with just headers
    with open(csv_path, 'w') as f:
        f.write("planid,planname,program,sequencetermid,yearnumber,season,season_code,courses\n")
    mgr = SequenceManager(csv_path)
    assert len(mgr.plans) == 0


# --- Sequence wrapper ---

def test_sequence_all(tmp_path):
    csv_path = str(tmp_path / "seq.csv")
    _write_csv(csv_path, _sample_rows())
    seq = Sequence(csv_path)
    assert len(seq.year) == 3


def test_sequence_season_filter(tmp_path):
    csv_path = str(tmp_path / "seq.csv")
    _write_csv(csv_path, _sample_rows())
    seq = Sequence(csv_path, season_filter=2)
    assert len(seq.year) == 2  # fall only


def test_sequence_get_all_plans(tmp_path):
    csv_path = str(tmp_path / "seq.csv")
    _write_csv(csv_path, _sample_rows())
    seq = Sequence(csv_path)
    plans = seq.get_all_plans()
    assert len(plans) == 2
