"""Tests for the lab rooms CSV import API."""

import io
from unittest.mock import patch, MagicMock

import pytest

from app import _parse_lab_rooms_csv


# ---------------------------------------------------------------------------
# CSV parsing tests (no DB required)
# ---------------------------------------------------------------------------

def test_parse_empty_csv():
    stream = io.BytesIO(b"")
    assert _parse_lab_rooms_csv(stream) == []


def test_parse_header_only():
    stream = io.BytesIO(b"Course Code,Title,Room,Capacity,Cap_MAX,Responsible,Comments\n")
    assert _parse_lab_rooms_csv(stream) == []


def test_parse_valid_csv():
    csv_data = (
        b"Course Code,Title,Room,Capacity,Cap_MAX,Responsible,Comments\n"
        b"COEN 314,Digital Electronics 1,H-861,14,16,Shiyu,\n"
    )
    rows = _parse_lab_rooms_csv(io.BytesIO(csv_data))
    assert len(rows) == 1
    assert rows[0]["course_code"] == "COEN 314"
    assert rows[0]["room"] == "H-861"
    assert rows[0]["capacity"] == "14"


def test_parse_aits_room():
    csv_data = (
        b"Course Code,Title,Room,Capacity,Cap_MAX,Responsible,Comments\n"
        b"COEN 346,OPERATING SYSTEMS,AITS,16,AITS,Bipin,\n"
    )
    rows = _parse_lab_rooms_csv(io.BytesIO(csv_data))
    assert len(rows) == 1
    assert rows[0]["room"] == "AITS"
    assert rows[0]["capacity_max"] == "AITS"


def test_parse_multiple_rows():
    csv_data = (
        b"Course Code,Title,Room,Capacity,Cap_MAX,Responsible,Comments\n"
        b"COEN 212,DIGITAL SYSTEMS DESIGN,H-807,16,18,Ted,notes\n"
        b"COEN 311,COMP ORGANIZATION,H-813,14,16,Ted,\n"
        b"COEN 311,COMP ORGANIZATION,AITS,14,AITS,Ted,any AITS lab\n"
    )
    rows = _parse_lab_rooms_csv(io.BytesIO(csv_data))
    assert len(rows) == 3


def test_parse_skips_short_rows():
    csv_data = (
        b"Course Code,Title,Room,Capacity,Cap_MAX,Responsible,Comments\n"
        b"COEN 314,Digital Electronics\n"
        b"COEN 212,DIGITAL SYSTEMS,H-807,16,18,Ted,notes\n"
    )
    rows = _parse_lab_rooms_csv(io.BytesIO(csv_data))
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# API endpoint tests (DB mocked via SQLAlchemy)
# ---------------------------------------------------------------------------

def test_import_no_file(client):
    res = client.post("/api/import/labrooms")
    assert res.status_code == 400
    data = res.get_json()
    assert data["status"] == "error"


def test_import_non_csv_file(client):
    data = {"file": (io.BytesIO(b"hello"), "data.txt")}
    res = client.post("/api/import/labrooms", data=data, content_type="multipart/form-data")
    assert res.status_code == 400


def test_import_empty_csv(client):
    data = {"file": (io.BytesIO(b""), "empty.csv")}
    res = client.post("/api/import/labrooms", data=data, content_type="multipart/form-data")
    assert res.status_code == 400


@patch("app.db.session")
def test_import_db_error(mock_session, client):
    mock_session.execute.side_effect = Exception("Connection refused")
    csv_data = (
        b"Course Code,Title,Room,Capacity,Cap_MAX,Responsible,Comments\n"
        b"COEN 314,Digital Electronics 1,H-861,14,16,Shiyu,\n"
    )
    data = {"file": (io.BytesIO(csv_data), "rooms.csv")}
    res = client.post("/api/import/labrooms", data=data, content_type="multipart/form-data")
    assert res.status_code == 500
    assert "database" in res.get_json()["message"].lower()


@patch("app.db.session")
def test_import_success(mock_session, client):
    # Mock the execute call to return a row with labroomid
    mock_result = MagicMock()
    mock_mapping = MagicMock()
    mock_mapping.__getitem__ = lambda self, key: 1  # labroomid = 1
    mock_result.mappings.return_value.first.return_value = mock_mapping
    mock_session.execute.return_value = mock_result

    csv_data = (
        b"Course Code,Title,Room,Capacity,Cap_MAX,Responsible,Comments\n"
        b"COEN 314,Digital Electronics 1,H-861,14,16,Shiyu,\n"
        b"COEN 346,OPERATING SYSTEMS,AITS,16,AITS,Bipin,\n"
    )
    data = {"file": (io.BytesIO(csv_data), "rooms.csv")}
    res = client.post("/api/import/labrooms", data=data, content_type="multipart/form-data")
    assert res.status_code == 200

    body = res.get_json()
    assert body["status"] == "success"
    assert body["rows_processed"] == 2
    assert body["rooms_upserted"] == 2
    assert body["assignments_upserted"] == 2
