import csv
import io
import json
import sys
import types
from datetime import date

import pytest

import app as app_module
from app import (
    app as flask_app,
    db,
    _semester_label,
    conflict_detail,
    derive_solution,
    _get_course_days,
    _parse_lab_rooms_csv,
    _parse_catalog_csv,
    _parse_schedules_csv,
    _parse_sequence_plan_csv,
    _parse_student_schedules_csv,
    _parse_buildings_csv,
)


class FakeResult:
    def __init__(self, rows=None, scalar_value=None, rowcount=0):
        self._rows = rows or []
        self._scalar_value = scalar_value
        self.rowcount = rowcount

    def mappings(self):
        return self

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def one(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._scalar_value


class FakeSession:
    def __init__(self, responses=None):
        self.responses = responses or []
        self.executed = []

    def execute(self, statement, params=None):
        sql = str(statement).lower() if statement is not None else ""
        self.executed.append((sql, params))
        for pattern, response in self.responses:
            if pattern in sql:
                return response(sql, params) if callable(response) else response
        return FakeResult(rows=[])

    def commit(self):
        return None

    def rollback(self):
        return None

    def remove(self):
        return None


def install_fake_db(monkeypatch, responses=None):
    fake = FakeSession(responses=responses)
    monkeypatch.setattr(db, "session", fake, raising=False)
    monkeypatch.setattr(db, "_session", fake, raising=False)
    return fake


def make_csv_file(text: str, filename: str = "test.csv"):
    return {
        "file": (io.BytesIO(text.encode("utf-8")), filename),
    }


def test_semester_label_with_and_without_map():
    assert _semester_label("Semester 3", {"3": "Fall Year 2 (COEN)"}) == "Fall Year 2 (COEN)"
    assert _semester_label("Semester 4", {"3": "Fall Year 2 (COEN)"}) == "Semester 4"
    assert _semester_label("Not a semester", {"3": "Fall Year 2 (COEN)"}) == "Not a semester"


def test_conflict_detail_variants():
    assert (
        conflict_detail({
            "Conflict_Type": "Lecture-Tutorial",
            "Course": "COEN101",
            "Component1": "Lecture",
            "Component2": "Tutorial",
            "Time1": "08:00",
            "Time2": "09:00",
            "Day": "Monday",
        })
        == "COEN101 — Lecture 08:00 vs Tutorial 09:00 — on day Monday"
    )

    assert (
        conflict_detail({
            "Conflict_Type": "Room Conflict",
            "Course": "COEN101",
            "Building": "H",
            "Room": "859",
            "Time1": "08:00",
            "Time2": "09:00",
        })
        == "COEN101 both assigned H-859 — 08:00 vs 09:00"
    )

    assert (
        conflict_detail({
            "Conflict_Type": "Sequence-Missing Course",
            "Component1": "Semester 3",
            "Component2": "['COEN490']",
        }, semester_labels={"3": "Fall Year 2 (COEN)"})
        == "Fall Year 2 (COEN): missing COEN490"
    )


@pytest.mark.parametrize(
    "row, expected",
    [
        (
            {"Conflict_Type": "Lecture-Lab", "Course": "COEN101"},
            "COEN101: Reschedule lab to a non-conflicting time slot",
        ),
        (
            {
                "Conflict_Type": "Room Conflict",
                "Course": "COEN101",
                "Building": "H",
                "Room": "859",
            },
            "COEN101: Assign an alternative lab room (currently H-859)",
        ),
        (
            {
                "Conflict_Type": "Sequence-Tutorial/Lab Overlap",
                "Course": "COEN101",
                "Component1": "TUT1",
                "Component2": "LAB2",
            },
            "COEN101: Adjust tutorial/lab sections to avoid overlap between TUT1 and LAB2",
        ),
        (
            {
                "Conflict_Type": "Sequence-No Valid Combination",
                "Component1": "Semester 3",
            },
            "Fall Year 2 (COEN): Re-evaluate section combinations for sequence courses",
        ),
    ],
)
def test_derive_solution_variants(row, expected):
    assert derive_solution(row, semester_labels={"3": "Fall Year 2 (COEN)"}) == expected


def test_get_course_days_valid_and_invalid():
    assert _get_course_days("MTWTF--") == [True, True, True, True, True, False, False]
    assert _get_course_days("MTWTF") is None


def test_parse_lab_rooms_csv_invalid_rows():
    bad_csv = "course,title,room\n1,2,3"
    assert _parse_lab_rooms_csv(io.BytesIO(bad_csv.encode("utf-8"))) == []


def test_parse_lab_rooms_csv_valid_rows():
    body = "course_code,title,room,capacity,capacity_max,responsible,comments\nCOEN 101,Intro,H-859,40,45,admin,good\n"
    rows = _parse_lab_rooms_csv(io.BytesIO(body.encode("utf-8")))
    assert rows == [
        {
            "course_code": "COEN 101",
            "title": "Intro",
            "room": "H-859",
            "capacity": "40",
            "capacity_max": "45",
            "responsible": "admin",
            "comments": "good",
        }
    ]


def test_parse_catalog_csv_error_and_success():
    bad_csv = "subject,catalog,title,career,classunit\nCOEN,101,Intro,UGRD,3"
    msg, rows = _parse_catalog_csv(io.BytesIO(bad_csv.encode("utf-8")))
    assert msg.startswith("Expected 6 columns")
    assert rows == []

    good_csv = "subject,catalog,title,career,classunit,prerequisites\nCOEN,101,Intro,UGRD,3,None\n"
    msg, rows = _parse_catalog_csv(io.BytesIO(good_csv.encode("utf-8")))
    assert msg == "success"
    assert rows[0]["subject"] == "COEN"


def test_parse_sequence_plan_csv_invalid_and_success():
    bad_csv = "Name,Program,EntryTerm,Option,DurationYears\nTOO_SHORT\n"
    msg, plan, terms, courses = _parse_sequence_plan_csv(io.BytesIO(bad_csv.encode("utf-8")))
    assert msg.startswith("Expected 5 columns")

    good_csv = (
        "Name,Program,EntryTerm,Option,DurationYears\n"
        "MyPlan,Engineering,2025,Fall,4\n"
        ",YearNumber,Season,WorkTerm,Notes\n"
        "1,1,fall,0,notes\n"
        ",Subject,Catalog,Unused,Label\n"
        "1,COEN,101,,Course A\n"
    )
    msg, plan, terms, courses = _parse_sequence_plan_csv(io.BytesIO(good_csv.encode("utf-8")))
    assert msg == "success"
    assert plan["planname"] == "MyPlan"
    assert terms[0]["season"] == "fall"
    assert courses[0]["label"] == "Course A"


def test_parse_student_schedules_csv_invalid_and_success():
    bad_csv = "StudyName,Owner,Unused,Unused,Unused\nTOO_SHORT\n"
    msg, study, schedules, classes = _parse_student_schedules_csv(io.BytesIO(bad_csv.encode("utf-8")))
    assert msg.startswith("Expected 5 columns")

    good_csv = (
        "StudyName,Owner,Unused,Unused,Unused\n"
        "MyStudy,owner,_,_,_\n"
        ",Notes,_,_,_\n"
        "Schedule A,notes,_,_,_\n"
        ",Subject,Catalog,Section,TermNumber\n"
        "Schedule A,COEN,101,001,2251\n"
    )
    msg, study, schedules, classes = _parse_student_schedules_csv(io.BytesIO(good_csv.encode("utf-8")))
    assert msg == "success"
    assert study["studyname"] == "MyStudy"
    assert schedules[0]["schedulename"] == "Schedule A"
    assert classes[0]["catalog"] == "101"


def test_parse_buildings_csv_invalid_and_success():
    bad_csv = "Campus,Building,BuildingName,Address,Latitude,Longitude\nTOO_SHORT\n"
    msg, rows = _parse_buildings_csv(io.BytesIO(bad_csv.encode("utf-8")))
    assert msg.startswith("Expected 6 columns")

    bad_campus = "Campus,Building,Name,Address,Lat,Long\nXYZ,EV,Ev,Addr,1,2\n"
    msg, rows = _parse_buildings_csv(io.BytesIO(bad_campus.encode("utf-8")))
    assert msg.startswith("Only SGW and LOY")

    good_csv = "Campus,Building,BuildingName,Address,Latitude,Longitude\nSGW,EV,Engineering,123 St,45.0,-73.0\n"
    msg, rows = _parse_buildings_csv(io.BytesIO(good_csv.encode("utf-8")))
    assert msg == "success"
    assert rows[0]["campus"] == "SGW"


def test_dashboard_route_returns_200(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.content_type


def test_schedulerrun_invalid_numbers_with_algo_blocked(client, monkeypatch):
    monkeypatch.setattr(app_module, "algorithmimplemented", False)
    res = client.post(
        "/schedulerrun",
        data={"season": "bad", "academic_year": "bad", "schedulename": "demo"},
    )
    assert res.status_code == 302
    assert "/" in res.location


def test_create_course_missing_fields(client):
    res = client.post("/create-course", json={})
    assert res.status_code == 400
    assert "termid" in res.get_json()["error"]


def test_create_course_term_not_found(client, monkeypatch):
    install_fake_db(monkeypatch, responses=[
        ("from sequenceterm", FakeResult(rows=[])),
    ])
    res = client.post(
        "/create-course",
        json={"termid": 1, "subject": "COEN", "catalog": "101"},
    )
    assert res.status_code == 404
    assert "Sequence term" in res.get_json()["error"]


def test_create_course_new_course_missing_title(client, monkeypatch):
    install_fake_db(monkeypatch, responses=[
        ("from sequenceterm", FakeResult(rows=[{"sequencetermid": 1}])),
        ("from catalog", FakeResult(rows=[])),
        ("select 1 from sequencecourse", FakeResult(rows=[])),
        ("insert into sequencecourse", FakeResult(rows=[])),
    ])
    res = client.post(
        "/create-course",
        json={
            "termid": 1,
            "subject": "COEN",
            "catalog": "101",
            "create_new": True,
        },
    )
    assert res.status_code == 400
    assert "Title is required" in res.get_json()["error"]


def test_create_course_new_course_success(client, monkeypatch):
    install_fake_db(monkeypatch, responses=[
        ("from sequenceterm", FakeResult(rows=[{"sequencetermid": 1}])),
        ("from catalog", FakeResult(rows=[])),
        ("select 1 from sequencecourse", FakeResult(rows=[])),
        ("insert into catalog", FakeResult(rows=[])),
        ("insert into sequencecourse", FakeResult(rows=[])),
    ])
    res = client.post(
        "/create-course",
        json={
            "termid": 1,
            "subject": "COEN",
            "catalog": "101",
            "create_new": True,
            "title": "Intro to Software",
            "classunit": 3,
            "prerequisites": "",
        },
    )
    assert res.status_code == 201
    assert "Added COEN 101" in res.get_json()["message"]


def test_update_course_missing_fields(client):
    res = client.post("/update-course", json={})
    assert res.status_code == 400


def test_update_course_not_found(client, monkeypatch):
    install_fake_db(monkeypatch, responses=[
        ("select 1 from sequencecourse", FakeResult(rows=[])),
    ])
    res = client.post(
        "/update-course",
        json={
            "old_subject": "COEN",
            "old_catalog": "101",
            "old_termid": 1,
            "new_subject": "COEN",
            "new_catalog": "101",
        },
    )
    assert res.status_code == 404
    assert "Original course not found" in res.get_json()["error"]


def test_update_course_success_same_course(client, monkeypatch):
    install_fake_db(monkeypatch, responses=[
        ("select 1 from sequencecourse", FakeResult(rows=[{"1": 1}])),
        ("delete from sequencecourse", FakeResult(rows=[])),
        ("insert into sequencecourse", FakeResult(rows=[])),
    ])
    res = client.post(
        "/update-course",
        json={
            "old_subject": "COEN",
            "old_catalog": "101",
            "old_termid": 1,
            "new_subject": "COEN",
            "new_catalog": "101",
        },
    )
    assert res.status_code == 200
    assert "Updated COEN 101" in res.get_json()["message"]


def test_api_search_catalog_short_query(client):
    res = client.get("/api/search-catalog?q=a")
    assert res.status_code == 200
    assert res.get_json() == []


def test_api_export_csv_no_rows(client, monkeypatch):
    install_fake_db(monkeypatch, responses=[
        ("select name from schedulerun", FakeResult(rows=[{"name": "schedule"}])),
        ("from optimized_schedule", FakeResult(rows=[])),
    ])
    res = client.get("/api/export-csv")
    assert res.status_code == 404
    assert "No optimized schedule data" in res.get_json()["error"]


def test_api_export_csv_success(client, monkeypatch):
    row = {
        "subject": "COEN",
        "catalog": "101",
        "section": "001",
        "componentcode": "LEC",
        "termcode": "2251",
        "classnumber": "1234",
        "session": "13W",
        "buildingcode": "H",
        "room": "859",
        "instructionmodecode": "INP",
        "locationcode": "TBD",
        "currentwaitlisttotal": 0,
        "waitlistcapacity": 5,
        "enrollmentcapacity": 40,
        "currentenrollment": 30,
        "departmentcode": "ELECCOEN",
        "facultycode": "ENCS",
        "classstarttime": "08:00:00",
        "classendtime": "09:00:00",
        "classstartdate": "2025-01-01",
        "classenddate": "2025-04-01",
        "mondays": True,
        "tuesdays": False,
        "wednesdays": False,
        "thursdays": False,
        "fridays": False,
        "saturdays": False,
        "sundays": False,
        "facultydescription": "",
        "career": "UGRD",
        "meetingpatternnumber": 1,
    }
    install_fake_db(monkeypatch, responses=[
        ("select name from schedulerun", FakeResult(rows=[{"name": "schedule"}])),
        ("from optimized_schedule", FakeResult(rows=[row])),
    ])
    res = client.get("/api/export-csv?format=detailed")
    assert res.status_code == 200
    assert res.content_type == "text/csv; charset=utf-8"
    assert "schedule-detailed.csv" in res.headers["Content-Disposition"]
    assert "subject,catalog,section,componentcode" in res.get_data(as_text=True)


def test_api_waitlist_students_missing_params(client):
    res = client.get("/api/waitlist/students")
    assert res.status_code == 400
    assert "required" in res.get_json()["error"]


def test_api_waitlist_students_fallback(client, monkeypatch):
    install_fake_db(monkeypatch, responses=[
        ("from studentschedulestudy sss", FakeResult(rows=[])),
        ("from studentschedulestudy", FakeResult(rows=[{"studyid": 5, "studyname": "Test"}])),
    ])
    res = client.get("/api/waitlist/students?subject=COEN&catalog=101")
    assert res.status_code == 200
    assert res.get_json() == [{"studyid": 5, "studyname": "Test"}]


def test_api_waitlist_download_missing_params(client):
    res = client.get("/api/waitlist/download")
    assert res.status_code == 400
    assert "subject and catalog" in res.get_json()["error"]


def test_api_waitlist_download_no_results(client, monkeypatch):
    install_fake_db(monkeypatch, responses=[
        ("from lab_slot_result", FakeResult(rows=[])),
    ])
    res = client.get("/api/waitlist/download?subject=COEN&catalog=101")
    assert res.status_code == 404
    assert "No results found" in res.get_json()["error"]


def test_api_optimized_date_range_returns_none(client, monkeypatch):
    install_fake_db(monkeypatch, responses=[
        ("select min(os.classstartdate) as min_date", FakeResult(rows=[{"min_date": None, "max_date": None}])),
    ])
    res = client.get("/api/optimized-date-range")
    assert res.status_code == 200
    assert res.get_json() == {"startDate": None, "endDate": None}


def test_api_optimized_date_range_with_dates(client, monkeypatch):
    install_fake_db(monkeypatch, responses=[
        ("select min(os.classstartdate) as min_date", FakeResult(rows=[{"min_date": "2025-01-01", "max_date": "2025-04-01"}])),
    ])
    res = client.get("/api/optimized-date-range")
    assert res.status_code == 200
    assert res.get_json()["startDate"] == "2025-01-01"


def test_api_plans_terms_returns_empty_for_missing_plan(client, monkeypatch):
    install_fake_db(monkeypatch, responses=[
        ("from sequenceterm", FakeResult(rows=[])),
    ])
    res = client.get("/api/plans/999/terms")
    assert res.status_code == 200
    assert res.get_json() == []


def test_api_plans_terms_returns_rows(client, monkeypatch):
    install_fake_db(monkeypatch, responses=[
        ("from sequenceterm", FakeResult(rows=[{"sequencetermid": 10, "yearnumber": 1, "season": "fall", "workterm": "0", "notes": ""}])),
    ])
    res = client.get("/api/plans/1/terms")
    assert res.status_code == 200
    data = res.get_json()
    assert data[0]["sequencetermid"] == 10


def test_api_events_termid_autodetect(monkeypatch, client):
    def event_response(sql, params):
        if "select season from sequenceterm" in sql:
            return FakeResult(scalar_value="fall")
        if "select max(sch.termcode)" in sql:
            return FakeResult(scalar_value=2251)
        return FakeResult(rows=[{
            "subject": "COEN",
            "catalog": "101",
            "section": "001",
            "componentcode": "LEC",
            "classnumber": 1,
            "buildingcode": "H",
            "room": "859",
            "classstarttime": "08:00:00",
            "classendtime": "09:00:00",
            "mondays": True,
            "tuesdays": False,
            "wednesdays": False,
            "thursdays": False,
            "fridays": False,
            "saturdays": False,
            "sundays": False,
            "termcode": 2251,
            "currentenrollment": 30,
            "enrollmentcapacity": 40,
            "currentwaitlisttotal": 0,
            "waitlistcapacity": 0,
            "meetingpatternnumber": 1,
            "classstartdate": date(2025, 1, 1),
            "classenddate": date(2025, 4, 1),
            "coursetitle": "Introduction",
        }])

    install_fake_db(monkeypatch, responses=[
        ("select season from sequenceterm", event_response),
        ("select max(sch.termcode)", event_response),
        ("select distinct on (st.subject, st.catalog", event_response),
    ])
    res = client.get("/api/events?termid=1")
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_api_list_optimized_grouping(monkeypatch, client):
    install_fake_db(monkeypatch, responses=[
        ("from optimized_schedule st", FakeResult(rows=[{
            "id": 1,
            "subject": "COEN",
            "catalog": "101",
            "section": "001",
            "componentcode": "LAB",
            "classnumber": 1,
            "buildingcode": "H",
            "room": "859",
            "classstarttime": "10:00:00",
            "classendtime": "12:00:00",
            "mondays": True,
            "tuesdays": False,
            "wednesdays": False,
            "thursdays": False,
            "fridays": False,
            "saturdays": False,
            "sundays": False,
            "currentenrollment": 20,
            "enrollmentcapacity": 30,
            "currentwaitlisttotal": 5,
            "waitlistcapacity": 8,
            "coursetitle": "Laboratory",
        }]) ),
    ])
    res = client.get("/api/list-optimized")
    assert res.status_code == 200
    data = res.get_json()
    assert data["Monday"] and data["Monday"][0]["subject"] == "COEN"


def test_api_update_class_and_create_class(monkeypatch, client):
    install_fake_db(monkeypatch, responses=[
        ("update optimized_schedule", FakeResult(rows=[], rowcount=1)),
        ("insert into optimized_schedule", FakeResult(rows=[])),
    ])

    update_res = client.put(
        "/api/update-class/1",
        json={
            "subject": "COEN",
            "catalog": "101",
            "section": "001",
            "component": "LAB",
            "startTime": "08:00",
            "endTime": "09:00",
            "building": "H",
            "room": "859",
            "enrollment": 20,
            "capacity": 30,
            "waitlist": 2,
            "waitlistCapacity": 5,
            "day": "Monday",
        },
    )
    assert update_res.status_code == 200
    assert update_res.get_json()["status"] == "success"

    create_res = client.post(
        "/api/create-class",
        json={
            "subject": "COEN",
            "catalog": "101",
            "section": "002",
            "component": "LAB",
            "startTime": "08:00",
            "endTime": "09:00",
            "building": "H",
            "room": "859",
            "enrollment": 10,
            "capacity": 20,
            "waitlist": 0,
            "waitlistCapacity": 5,
            "day": "Tuesday",
        },
    )
    assert create_res.status_code == 201
    assert create_res.get_json()["status"] == "created"


def test_api_waitlist_run_invalid_payload(client):
    res = client.post("/api/waitlist/run", json={})
    assert res.status_code == 400
    assert "required" in res.get_json()["error"]


def test_api_waitlist_run_success(monkeypatch, client):
    fake_conn = types.SimpleNamespace()
    fake_cur = types.SimpleNamespace()

    def get_conn():
        return types.SimpleNamespace(cursor=lambda: fake_cur, commit=lambda: None)

    def load_students_busy_from_db(cur, students):
        return {}

    def get_two_week_anchor_monday(cur, students):
        return 1

    def load_room_busy_for_course(cur, subject, catalog, week1):
        return {}

    def propose_waitlist_slots(waitlisted_students, students_busy, room_busy, lab_start_times):
        return {
            (1, 525): ["s1", "s2"],
            (2, 525): ["s1"],
        }

    def save_lab_results_to_db(cur, subject, catalog, duration, results):
        pass

    wla_pkg = types.ModuleType("waitlist_algorithm")
    db_pkg = types.ModuleType("waitlist_algorithm.database_connection")
    db_mod = types.ModuleType("waitlist_algorithm.database_connection.db")
    students_busy_pkg = types.ModuleType("waitlist_algorithm.algorithm.students_busy")
    room_busy_pkg = types.ModuleType("waitlist_algorithm.algorithm.room_busy")
    lab_generator_pkg = types.ModuleType("waitlist_algorithm.algorithm.lab_generator")
    database_results_pkg = types.ModuleType("waitlist_algorithm.algorithm.database_results")

    db_mod.get_conn = get_conn
    students_busy_pkg.load_students_busy_from_db = load_students_busy_from_db
    students_busy_pkg.get_two_week_anchor_monday = get_two_week_anchor_monday
    room_busy_pkg.load_room_busy_for_course = load_room_busy_for_course
    lab_generator_pkg.propose_waitlist_slots = propose_waitlist_slots
    database_results_pkg.save_lab_results_to_db = save_lab_results_to_db

    monkeypatch.setitem(sys.modules, "waitlist_algorithm", wla_pkg)
    monkeypatch.setitem(sys.modules, "waitlist_algorithm.database_connection", db_pkg)
    monkeypatch.setitem(sys.modules, "waitlist_algorithm.database_connection.db", db_mod)
    monkeypatch.setitem(sys.modules, "waitlist_algorithm.algorithm.students_busy", students_busy_pkg)
    monkeypatch.setitem(sys.modules, "waitlist_algorithm.algorithm.room_busy", room_busy_pkg)
    monkeypatch.setitem(sys.modules, "waitlist_algorithm.algorithm.lab_generator", lab_generator_pkg)
    monkeypatch.setitem(sys.modules, "waitlist_algorithm.algorithm.database_results", database_results_pkg)

    res = client.post(
        "/api/waitlist/run",
        json={"subject": "COEN", "catalog": "101", "students": ["s1", "s2"]},
    )
    assert res.status_code == 200
    assert res.get_json()["status"] == "success"
    assert len(res.get_json()["results"]) >= 1


def test_api_filters_termid_and_planid(client, monkeypatch):
    def response_for(sql, params):
        if "from scheduleterm sch" in sql and "min(sch.classstartdate)" in sql:
            return FakeResult(rows=[{"termcode": 2251, "first_date_ymd": "2025-09-01"}])
        if "select distinct sch.subject" in sql:
            return FakeResult(rows=["COEN"])
        if "select distinct sch.componentcode" in sql:
            return FakeResult(rows=["LAB"])
        if "select distinct sch.buildingcode" in sql:
            return FakeResult(rows=["H"])
        if "from sequenceplan" in sql:
            return FakeResult(rows=[{"planid": 1, "planname": "Plan A", "program": "ENG", "entryterm": "2251", "option": "A"}])
        return FakeResult(rows=[])

    install_fake_db(monkeypatch, responses=[("select distinct sch.subject", response_for),
                                            ("select distinct sch.componentcode", response_for),
                                            ("select distinct sch.buildingcode", response_for),
                                            ("from sequenceplan", response_for),
                                            ("min(sch.classstartdate)", response_for),
                                            ("from sequenceterm", FakeResult(scalar_value="fall")),
                                            ("select max(sch.termcode)", FakeResult(scalar_value=2251)),
                                           ])
    res = client.get("/api/filters?termid=1&planid=1")
    assert res.status_code == 200
    data = res.get_json()
    assert data["terms"][0]["name"] == "Fall 2025"
    assert data["subjects"] == ["COEN"]
    assert data["components"] == ["LAB"]
    assert data["buildings"] == ["H"]
    assert isinstance(data["plans"], list)

