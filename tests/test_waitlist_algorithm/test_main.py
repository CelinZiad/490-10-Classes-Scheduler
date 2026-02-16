from unittest.mock import MagicMock
import pytest
import waitlist_algorithm.algorithm.main as mod


def test_main_happy_path(monkeypatch, capsys):
    fake_cur = MagicMock()
    fake_conn = MagicMock()
    fake_conn.cursor.return_value = fake_cur

    monkeypatch.setattr(mod, "get_conn", lambda: fake_conn)
    monkeypatch.setattr(
        mod,
        "get_waitlisted_students_and_course_from_user",
        lambda cur: ([5001, 5002], ("COEN", "243")),
    )
    monkeypatch.setattr(
        mod,
        "load_students_busy_from_db",
        lambda cur, ids: {5001: [], 5002: []},
    )
    monkeypatch.setattr(
        mod,
        "load_room_busy_for_course",
        lambda cur, subject, catalog: [],
    )
    monkeypatch.setattr(
        mod,
        "propose_waitlist_slots",
        lambda **kwargs: {(1, 525): [5001], (2, 705): [5002, 5001]},
    )

    mod.main()

    out = capsys.readouterr().out
    assert "--- Proposed Lab Slots ---" in out
    assert "1,08:45,5001" in out
    assert "2,11:45,5002,5001" in out


def test_main_no_results(monkeypatch, capsys):
    fake_cur = MagicMock()
    fake_conn = MagicMock()
    fake_conn.cursor.return_value = fake_cur

    monkeypatch.setattr(mod, "get_conn", lambda: fake_conn)
    monkeypatch.setattr(
        mod,
        "get_waitlisted_students_and_course_from_user",
        lambda cur: ([5001], ("COEN", "243")),
    )
    monkeypatch.setattr(mod, "load_students_busy_from_db", lambda cur, ids: {5001: []})
    monkeypatch.setattr(mod, "load_room_busy_for_course", lambda cur, s, c: [])
    monkeypatch.setattr(mod, "propose_waitlist_slots", lambda **kwargs: {})

    mod.main()

    out = capsys.readouterr().out
    assert "--- Proposed Lab Slots ---" in out


def test_main_calls_propose_with_expected_arguments(monkeypatch):
    fake_cur = MagicMock()
    fake_conn = MagicMock()
    fake_conn.cursor.return_value = fake_cur

    captured = {}

    def fake_propose_waitlist_slots(**kwargs):
        captured.update(kwargs)
        return {}

    monkeypatch.setattr(mod, "get_conn", lambda: fake_conn)
    monkeypatch.setattr(
        mod,
        "get_waitlisted_students_and_course_from_user",
        lambda cur: ([5001, 5002], ("COEN", "243")),
    )

    fake_students_busy = {5001: [], 5002: []}
    fake_room_busy = []

    monkeypatch.setattr(mod, "load_students_busy_from_db", lambda cur, ids: fake_students_busy)
    monkeypatch.setattr(mod, "load_room_busy_for_course", lambda cur, s, c: fake_room_busy)
    monkeypatch.setattr(mod, "propose_waitlist_slots", fake_propose_waitlist_slots)

    mod.main()

    assert captured["waitlisted_students"] == [5001, 5002]
    assert captured["students_busy"] is fake_students_busy
    assert captured["room_busy"] is fake_room_busy
    assert captured["lab_start_times"] == [mod.m(8, 45), mod.m(11, 45), mod.m(14, 45), mod.m(17, 45)]
