import os
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

ROUTE_TEMPLATES = {
    "/": "admin-dashboard.html",
    "/schedule": "schedule-display.html",
    "/catalog": "catalog.html",
    "/conflicts": "conflicts-list.html",
    "/solutions": "proposed-solutions.html",
    "/timetable": "timetable.html",
}

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


@app.get("/health/db")
def health_db():
    ok = db.session.execute(db.text("SELECT 1")).scalar() == 1
    return jsonify(ok=ok)


@app.get("/")
def dashboard():
    # ✅ Provide scheduler status to the template
    scheduler_status = {
        "state": "NOT_IMPLEMENTED",
        "message": "No scheduling algorithm is currently implemented.",
    }

    # ✅ Honest activity (until you generate schedules for real)
    recent_activity = [
        "Sequence plans available (COEN/ELEC, COOP/C-EDGE)",
        "Term structure loaded (Fall/Winter/Summer + work terms)",
        "Catalog data available (course titles + prerequisites)",
    ]

    return render_template(
        ROUTE_TEMPLATES["/"],
        scheduler_status=scheduler_status,
        recent_activity=recent_activity,
    )


@app.get("/schedule")
def schedule():
    plans = db.session.execute(db.text("""
        SELECT planid, planname, program, entryterm, option, durationyears, publishedon
        FROM sequenceplan
        ORDER BY publishedon DESC, planid ASC;
    """)).mappings().all()

    selected_planid = request.args.get("planid", type=int)
    if selected_planid is None and plans:
        selected_planid = plans[0]["planid"]

    terms = []
    if selected_planid is not None:
        terms = db.session.execute(db.text("""
            SELECT sequencetermid, yearnumber, season, workterm, notes
            FROM sequenceterm
            WHERE planid = :planid
            ORDER BY yearnumber ASC,
                     CASE season
                        WHEN 'fall' THEN 1
                        WHEN 'winter' THEN 2
                        WHEN 'summer' THEN 3
                        ELSE 4
                     END ASC;
        """), {"planid": selected_planid}).mappings().all()

    selected_termid = request.args.get("termid", type=int)
    if selected_termid is None and terms:
        selected_termid = terms[0]["sequencetermid"]

    courses = []
    if selected_termid is not None:
        courses = db.session.execute(db.text("""
            SELECT subject, catalog, label, iselective
            FROM sequencecourse
            WHERE sequencetermid = :termid
            ORDER BY subject ASC, catalog ASC;
        """), {"termid": selected_termid}).mappings().all()

    return render_template(
        ROUTE_TEMPLATES["/schedule"],
        plans=plans,
        terms=terms,
        courses=courses,
        selected_planid=selected_planid,
        selected_termid=selected_termid,
    )


# ✅ NEW ENDPOINT: combines sequencecourse + catalog
@app.get("/catalog")
def catalog():
    plans = db.session.execute(db.text("""
        SELECT planid, planname, program, entryterm, option, durationyears, publishedon
        FROM sequenceplan
        ORDER BY publishedon DESC, planid ASC;
    """)).mappings().all()

    selected_planid = request.args.get("planid", type=int)
    if selected_planid is None and plans:
        selected_planid = plans[0]["planid"]

    terms = []
    if selected_planid is not None:
        terms = db.session.execute(db.text("""
            SELECT sequencetermid, yearnumber, season, workterm, notes
            FROM sequenceterm
            WHERE planid = :planid
            ORDER BY yearnumber ASC,
                     CASE season
                        WHEN 'fall' THEN 1
                        WHEN 'winter' THEN 2
                        WHEN 'summer' THEN 3
                        ELSE 4
                     END ASC;
        """), {"planid": selected_planid}).mappings().all()

    selected_termid = request.args.get("termid", type=int)
    if selected_termid is None and terms:
        selected_termid = terms[0]["sequencetermid"]

    rows = []
    if selected_termid is not None:
        rows = db.session.execute(db.text("""
            SELECT
                sc.subject,
                sc.catalog,
                sc.label,
                sc.iselective,
                c.title,
                c.classunit,
                c.prerequisites
            FROM sequencecourse sc
            LEFT JOIN catalog c
              ON c.subject = sc.subject
             AND c.catalog = sc.catalog
             AND c.career = 'UGRD'
            WHERE sc.sequencetermid = :termid
            ORDER BY sc.subject ASC, sc.catalog ASC;
        """), {"termid": selected_termid}).mappings().all()

    return render_template(
        ROUTE_TEMPLATES["/catalog"],
        plans=plans,
        terms=terms,
        rows=rows,
        selected_planid=selected_planid,
        selected_termid=selected_termid,
    )


@app.get("/conflicts")
def conflicts():
    return render_template(ROUTE_TEMPLATES["/conflicts"])


@app.get("/solutions")
def solutions():
    return render_template(ROUTE_TEMPLATES["/solutions"])


@app.get("/timetable")
def timetable():
    return render_template(ROUTE_TEMPLATES["/timetable"])


# Color mapping for component types
COMPONENT_COLORS = {
    "LEC": "#3B82F6",   # Blue
    "TUT": "#10B981",   # Green
    "LAB": "#F59E0B",   # Orange
    "SEM": "#8B5CF6",   # Purple
    "ONL": "#06B6D4",   # Cyan
}
DEFAULT_COLOR = "#6B7280"  # Gray


@app.get("/api/events")
def api_events():
    """Return schedule events in FullCalendar format"""
    # Query params for filtering
    term = request.args.get("term", type=int)
    subject = request.args.get("subject")
    component = request.args.get("component")
    building = request.args.get("building")
    room = request.args.get("room")

    # Build dynamic query with filters
    query = """
        SELECT
            subject, catalog, section, componentcode, classnumber,
            buildingcode, room, classstarttime, classendtime,
            mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays,
            termcode, currentenrollment, enrollmentcapacity,
            currentwaitlisttotal, waitlistcapacity
        FROM scheduleterm
        WHERE classstarttime IS NOT NULL
          AND classendtime IS NOT NULL
    """
    params = {}

    if term:
        query += " AND termcode = :term"
        params["term"] = term

    if subject:
        # Support comma-separated subjects for ECE filter
        subjects = [s.strip() for s in subject.split(",")]
        if len(subjects) == 1:
            query += " AND subject = :subject"
            params["subject"] = subjects[0]
        else:
            query += " AND subject = ANY(:subjects)"
            params["subjects"] = subjects

    if component:
        query += " AND componentcode = :component"
        params["component"] = component

    if building:
        query += " AND buildingcode = :building"
        params["building"] = building

    if room:
        query += " AND room = :room"
        params["room"] = room

    query += " ORDER BY subject, catalog, section LIMIT 500"

    rows = db.session.execute(db.text(query), params).mappings().all()

    # Convert to FullCalendar event format
    events = []
    for row in rows:
        # Build days of week array (0=Sunday, 1=Monday, etc.)
        days_of_week = []
        if row["sundays"]:
            days_of_week.append(0)
        if row["mondays"]:
            days_of_week.append(1)
        if row["tuesdays"]:
            days_of_week.append(2)
        if row["wednesdays"]:
            days_of_week.append(3)
        if row["thursdays"]:
            days_of_week.append(4)
        if row["fridays"]:
            days_of_week.append(5)
        if row["saturdays"]:
            days_of_week.append(6)

        if not days_of_week:
            continue  # Skip if no days set

        # Format times as HH:MM:SS
        start_time = str(row["classstarttime"])
        end_time = str(row["classendtime"])

        # Get color based on component type
        color = COMPONENT_COLORS.get(row["componentcode"], DEFAULT_COLOR)

        event = {
            "id": f"{row['subject']}-{row['catalog']}-{row['section']}-{row['componentcode']}-{row['classnumber']}",
            "title": f"{row['subject']} {row['catalog']} {row['componentcode']}",
            "daysOfWeek": days_of_week,
            "startTime": start_time,
            "endTime": end_time,
            "color": color,
            "extendedProps": {
                "subject": row["subject"],
                "catalog": row["catalog"],
                "section": row["section"],
                "component": row["componentcode"],
                "building": row["buildingcode"] or "TBA",
                "room": row["room"] or "TBA",
                "enrollment": row["currentenrollment"] or 0,
                "capacity": row["enrollmentcapacity"] or 0,
                "waitlist": row["currentwaitlisttotal"] or 0,
                "waitlistCapacity": row["waitlistcapacity"] or 0,
                "termcode": row["termcode"],
            }
        }
        events.append(event)

    return jsonify(events)


@app.get("/api/filters")
def api_filters():
    """Return available filter options"""
    # Get distinct terms
    terms = db.session.execute(db.text("""
        SELECT DISTINCT termcode
        FROM scheduleterm
        WHERE termcode IS NOT NULL
        ORDER BY termcode DESC
    """)).scalars().all()

    # Format terms with readable names
    term_options = []
    for code in terms:
        # Parse term code: first digit is year offset from 2000, last digit is semester
        # 2251 = 2025 Winter, 2254 = 2025 Summer, 2257 = 2025 Fall
        year = 2000 + int(str(code)[:3]) // 10
        semester_code = int(str(code)[-1])
        semester_names = {1: "Winter", 4: "Summer", 7: "Fall"}
        semester = semester_names.get(semester_code, f"Term {semester_code}")
        term_options.append({"code": code, "name": f"{semester} {year}"})

    # Get distinct subjects
    subjects = db.session.execute(db.text("""
        SELECT DISTINCT subject
        FROM scheduleterm
        WHERE subject IS NOT NULL
        ORDER BY subject
    """)).scalars().all()

    # Get distinct component types
    components = db.session.execute(db.text("""
        SELECT DISTINCT componentcode
        FROM scheduleterm
        WHERE componentcode IS NOT NULL
        ORDER BY componentcode
    """)).scalars().all()

    # Get distinct buildings
    buildings = db.session.execute(db.text("""
        SELECT DISTINCT buildingcode
        FROM scheduleterm
        WHERE buildingcode IS NOT NULL AND buildingcode != ''
        ORDER BY buildingcode
    """)).scalars().all()

    return jsonify({
        "terms": term_options,
        "subjects": subjects,
        "components": components,
        "buildings": buildings,
    })


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
