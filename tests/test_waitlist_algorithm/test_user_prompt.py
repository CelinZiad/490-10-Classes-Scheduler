from unittest.mock import MagicMock
import pytest
import waitlist_algorithm.algorithm.users_prompt as mod


def test_prompt_waitlisted_studyids_empty(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert mod.prompt_waitlisted_studyids() == []


def test_prompt_waitlisted_studyids_parses_commas_and_spaces(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "5001, 5002 5003")
    assert mod.prompt_waitlisted_studyids() == [5001, 5002, 5003]


def test_prompt_waitlisted_studyids_deduplicates_preserves_order(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "5001,5002,5001 5003,5002")
    assert mod.prompt_waitlisted_studyids() == [5001, 5002, 5003]


def test_prompt_waitlisted_studyids_raises_on_invalid(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "5001,abc,5002")
    with pytest.raises(ValueError):
        mod.prompt_waitlisted_studyids()


def test_fetch_existing_studyids_empty_request():
    cur = MagicMock()
    assert mod.fetch_existing_studyids(cur, []) == []
    cur.execute.assert_not_called()


def test_fetch_existing_studyids_exec_and_returns_list():
    cur = MagicMock()
    cur.fetchall.return_value = [(5001,), (5003,)]
    out = mod.fetch_existing_studyids(cur, [5001, 5002, 5003])

    assert out == [5001, 5003]
    cur.execute.assert_called_once()
    sql_arg, params_arg = cur.execute.call_args.args
    assert "FROM studentschedulestudy" in sql_arg
    assert params_arg == ([5001, 5002, 5003],)


def test_prompt_target_course_valid(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "coen 243")
    assert mod.prompt_target_course() == ("COEN", "243")


def test_prompt_target_course_valid_with_comma(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "COEN,243")
    assert mod.prompt_target_course() == ("COEN", "243")


def test_prompt_target_course_empty_raises(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    with pytest.raises(ValueError):
        mod.prompt_target_course()


def test_prompt_target_course_bad_format_raises(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "COEN243")
    with pytest.raises(ValueError):
        mod.prompt_target_course()


def test_course_exists_true():
    cur = MagicMock()
    cur.fetchone.return_value = (1,)
    assert mod.course_exists(cur, "COEN", "243") is True
    cur.execute.assert_called_once()


def test_course_exists_false():
    cur = MagicMock()
    cur.fetchone.return_value = None
    assert mod.course_exists(cur, "COEN", "243") is False
    cur.execute.assert_called_once()


def test_get_waitlisted_students_and_course_from_user(monkeypatch):
    cur = MagicMock()

    monkeypatch.setattr(mod, "prompt_waitlisted_studyids", lambda: [5001, 5002, 5003])
    monkeypatch.setattr(mod, "fetch_existing_studyids", lambda _cur, ids: [5001, 5003])
    monkeypatch.setattr(mod, "prompt_target_course", lambda: ("COEN", "243"))
    monkeypatch.setattr(mod, "course_exists", lambda _cur, s, c: True)

    result = mod.get_waitlisted_students_and_course_from_user(cur)
    assert result == ([5001, 5003], ("COEN", "243"))


def test_get_waitlisted_students_and_course_from_user_no_found(monkeypatch):
    cur = MagicMock()

    monkeypatch.setattr(mod, "prompt_waitlisted_studyids", lambda: [5001])
    monkeypatch.setattr(mod, "fetch_existing_studyids", lambda _cur, ids: [])
    monkeypatch.setattr(mod, "prompt_target_course", lambda: ("COEN", "243"))
    monkeypatch.setattr(mod, "course_exists", lambda _cur, s, c: False)

    result = mod.get_waitlisted_students_and_course_from_user(cur)
    assert result == ([], ("COEN", "243"))
