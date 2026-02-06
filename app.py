import os
import json
from datetime import date
from flask import Flask, render_template, jsonify, request, redirect, url_for
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
    "/activity": "activity.html",
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

# flip to True when your real algorithm exists
algorithmimplemented = False


def logactivity(eventtype: str, title: str, actorname: str | None = None, metadata: dict | None = None):
    if metadata is None:
        metadata = {}

    db.session.execute(
        db.text("""
            insert into activitylog (actorname, eventtype, title, metadata)
            values (:actorname, :eventtype, :title, cast(:metadata as jsonb));
        """),
        {
            "actorname": actorname,
            "eventtype": eventtype,
            "title": title,
            "metadata": json.dumps(metadata),
        },
    )
    db.session.commit()


@app.get("/health/db")
def health_db():
    ok = db.session.execute(db.text("select 1")).scalar() == 1
    return jsonify(ok=ok)


@app.get("/")
def dashboard():
    # scheduler status
    if not algorithmimplemented:
        scheduler_status = {
            "state": "NOT_IMPLEMENTED",
            "message": "No scheduling algorithm is currently implemented.",
        }
    else:
        scheduler_status = {
            "state": "READY",
            "message": "Scheduling algorithm is available.",
        }

    # ✅ only show 3 recent items on dashboard
    recentactivity = db.session.execute(
        db.text("""
            select createdat, actorname, title
            from activitylog
            order by createdat desc
            limit 3;
        """)
    ).mappings().all()

    return render_template(
        ROUTE_TEMPLATES["/"],
        scheduler_status=scheduler_status,
        recentactivity=recentactivity,
    )


# ✅ Generate Schedule trigger (button on dashboard)
@app.post("/schedulerrun")
def postschedulerrun():
    schedulename = request.form.get("schedulename", "schedule-draft")

    # always log that someone pressed the button
    logactivity(
        eventtype="schedulerrunrequested",
        title=f'Schedule run requested: "{schedulename}"',
        actorname="admin",
        metadata={"schedulename": schedulename},
    )

    # no algo -> log blocked, do not create schedulerun row
    if not algorithmimplemented:
        logactivity(
            eventtype="schedulerrunblocked",
            title="Scheduler run blocked: no algorithm implemented.",
            actorname="system",
            metadata={},
        )
        return redirect(url_for("dashboard"))

    # algo exists -> create a schedulerun row
    db.session.execute(
        db.text("""
            insert into schedulerun (name, status)
            values (:name, 'generated');
        """),
        {"name": schedulename},
    )
    db.session.commit()

    logactivity(
        eventtype="schedulegenerated",
        title=f'Schedule "{schedulename}" generated',
        actorname="system",
        metadata={"schedulename": schedulename},
    )

    return redirect(url_for("dashboard"))


# ✅ NEW: view all activity + filter by date
@app.get("/activity")
def activity():
    startdate = request.args.get("startdate")  # YYYY-MM-DD
    enddate = request.args.get("enddate")      # YYYY-MM-DD

    where = []
    params = {}

    if startdate:
        where.append("createdat >= :startdate::date")
        params["startdate"] = startdate

    if enddate:
        where.append("createdat < (:enddate::date + interval '1 day')")
        params["enddate"] = enddate

    wheresql = ""
    if where:
        wheresql = "where " + " and ".join(where)

    logs = db.session.execute(
        db.text(f"""
            select activityid, createdat, actorname, eventtype, title
            from activitylog
            {wheresql}
            order by createdat desc
            limit 300;
        """),
        params,
    ).mappings().all()

    today = date.today().isoformat()

    return render_template(
        ROUTE_TEMPLATES["/activity"],
        logs=logs,
        startdate=startdate or "",
        enddate=enddate or "",
        today=today,
    )


@app.get("/schedule")
def schedule():
    plans = db.session.execute(db.text("""
        select planid, planname, program, entryterm, option, durationyears, publishedon
        from sequenceplan
        order by publishedon desc, planid asc;
    """)).mappings().all()

    selected_planid = request.args.get("planid", type=int)
    if selected_planid is None and plans:
        selected_planid = plans[0]["planid"]

    terms = []
    if selected_planid is not None:
        terms = db.session.execute(db.text("""
            select sequencetermid, yearnumber, season, workterm, notes
            from sequenceterm
            where planid = :planid
            order by yearnumber asc,
                     case season
                        when 'fall' then 1
                        when 'winter' then 2
                        when 'summer' then 3
                        else 4
                     end asc;
        """), {"planid": selected_planid}).mappings().all()

    selected_termid = request.args.get("termid", type=int)
    if selected_termid is None and terms:
        selected_termid = terms[0]["sequencetermid"]

    courses = []
    if selected_termid is not None:
        courses = db.session.execute(db.text("""
            select subject, catalog, label, iselective
            from sequencecourse
            where sequencetermid = :termid
            order by subject asc, catalog asc;
        """), {"termid": selected_termid}).mappings().all()

    return render_template(
        ROUTE_TEMPLATES["/schedule"],
        plans=plans,
        terms=terms,
        courses=courses,
        selected_planid=selected_planid,
        selected_termid=selected_termid,
    )


@app.get("/catalog")
def catalog():
    plans = db.session.execute(db.text("""
        select planid, planname, program, entryterm, option, durationyears, publishedon
        from sequenceplan
        order by publishedon desc, planid asc;
    """)).mappings().all()

    selected_planid = request.args.get("planid", type=int)
    if selected_planid is None and plans:
        selected_planid = plans[0]["planid"]

    terms = []
    if selected_planid is not None:
        terms = db.session.execute(db.text("""
            select sequencetermid, yearnumber, season, workterm, notes
            from sequenceterm
            where planid = :planid
            order by yearnumber asc,
                     case season
                        when 'fall' then 1
                        when 'winter' then 2
                        when 'summer' then 3
                        else 4
                     end asc;
        """), {"planid": selected_planid}).mappings().all()

    selected_termid = request.args.get("termid", type=int)
    if selected_termid is None and terms:
        selected_termid = terms[0]["sequencetermid"]

    rows = []
    if selected_termid is not None:
        rows = db.session.execute(db.text("""
            select
                sc.subject,
                sc.catalog,
                sc.label,
                sc.iselective,
                c.title,
                c.classunit,
                c.prerequisites
            from sequencecourse sc
            left join catalog c
              on c.subject = sc.subject
             and c.catalog = sc.catalog
             and c.career = 'UGRD'
            where sc.sequencetermid = :termid
            order by sc.subject asc, sc.catalog asc;
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


# ---------------------------------------------------------------------------
# Timetable page + API (TASK-8.1: Add Schedule Page)
# ---------------------------------------------------------------------------

COMPONENT_COLORS = {
    "LEC": "#3B82F6",   # Blue
    "TUT": "#10B981",   # Green
    "LAB": "#F59E0B",   # Orange
    "SEM": "#8B5CF6",   # Purple
    "ONL": "#06B6D4",   # Cyan
}
DEFAULT_COLOR = "#6B7280"  # Gray


@app.get("/timetable")
def timetable():
    return render_template(ROUTE_TEMPLATES["/timetable"])


@app.get("/api/events")
def api_events():
    """Return schedule events in FullCalendar format.

    Supports filtering by sequence plan/term (sequenceplan -> sequenceterm
    -> sequencecourse) as well as direct filters on scheduleterm columns.
    """
    planid = request.args.get("planid", type=int)
    termid = request.args.get("termid", type=int)
    term = request.args.get("term", type=int)
    subject = request.args.get("subject")
    component = request.args.get("component")
    building = request.args.get("building")

    query = """
        SELECT DISTINCT ON (st.subject, st.catalog, st.section,
                            st.componentcode, st.classnumber)
            st.subject, st.catalog, st.section, st.componentcode,
            st.classnumber, st.buildingcode, st.room,
            st.classstarttime, st.classendtime,
            st.mondays, st.tuesdays, st.wednesdays, st.thursdays,
            st.fridays, st.saturdays, st.sundays,
            st.termcode, st.currentenrollment, st.enrollmentcapacity,
            st.currentwaitlisttotal, st.waitlistcapacity,
            c.title AS coursetitle
        FROM scheduleterm st
        LEFT JOIN catalog c
          ON c.subject = st.subject
         AND c.catalog = st.catalog
         AND c.career  = 'UGRD'
        WHERE st.classstarttime IS NOT NULL
          AND st.classendtime   IS NOT NULL
          AND st.classstarttime != '00:00:00'
    """
    params = {}

    # Sequence filter: restrict to courses listed in a sequence term
    if termid:
        query += """
          AND EXISTS (
              SELECT 1 FROM sequencecourse sc
              WHERE sc.sequencetermid = :termid
                AND sc.subject  = st.subject
                AND sc.catalog  = st.catalog
          )
        """
        params["termid"] = termid

    if term:
        query += " AND st.termcode = :term"
        params["term"] = term

    if subject:
        subjects = [s.strip() for s in subject.split(",")]
        if len(subjects) == 1:
            query += " AND st.subject = :subject"
            params["subject"] = subjects[0]
        else:
            placeholders = ", ".join(f":subj_{i}" for i in range(len(subjects)))
            query += f" AND st.subject IN ({placeholders})"
            for i, s in enumerate(subjects):
                params[f"subj_{i}"] = s

    if component:
        query += " AND st.componentcode = :component"
        params["component"] = component

    if building:
        query += " AND st.buildingcode = :building"
        params["building"] = building

    query += " ORDER BY st.subject, st.catalog, st.section, st.componentcode, st.classnumber LIMIT 500"

    rows = db.session.execute(db.text(query), params).mappings().all()

    events = []
    for row in rows:
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
            continue

        start_time = str(row["classstarttime"])
        end_time = str(row["classendtime"])
        color = COMPONENT_COLORS.get(row["componentcode"], DEFAULT_COLOR)
        title = row["coursetitle"] or ""

        events.append({
            "id": (
                f"{row['subject']}-{row['catalog']}-{row['section']}"
                f"-{row['componentcode']}-{row['classnumber']}"
            ),
            "title": f"{row['subject']} {row['catalog']}",
            "daysOfWeek": days_of_week,
            "startTime": start_time,
            "endTime": end_time,
            "allDay": False,
            "color": color,
            "extendedProps": {
                "subject": row["subject"],
                "catalog": row["catalog"],
                "section": row["section"],
                "component": row["componentcode"],
                "coursetitle": title,
                "building": row["buildingcode"] or "TBA",
                "room": row["room"] or "TBA",
                "enrollment": row["currentenrollment"] or 0,
                "capacity": row["enrollmentcapacity"] or 0,
                "waitlist": row["currentwaitlisttotal"] or 0,
                "waitlistCapacity": row["waitlistcapacity"] or 0,
                "termcode": row["termcode"],
            },
        })

    return jsonify(events)


@app.get("/api/filters")
def api_filters():
    """Return available filter options, scoped to the selected term."""
    term = request.args.get("term", type=int)

    terms = db.session.execute(db.text("""
        SELECT DISTINCT termcode
        FROM scheduleterm
        WHERE termcode IS NOT NULL
          AND subject IN ('COEN','ELEC','COMP','SOEN')
        ORDER BY termcode DESC
    """)).scalars().all()

    term_options = []
    for code in terms:
        prefix = code // 10
        base_year = 2000 + (prefix - 200)
        last_digit = code % 10
        semester_map = {
            1: ("Fall", -1),
            2: ("Winter", 0),
            3: ("Winter/Spring", 0),
            4: ("Summer", 0),
            5: ("Summer", 0),
            6: ("Fall", 0),
        }
        name, year_offset = semester_map.get(last_digit, (f"Term {last_digit}", 0))
        year = base_year + year_offset
        term_options.append({"code": code, "name": f"{name} {year}"})

    # Scope to ECE subjects + selected term
    ece_filter = " AND subject IN ('COEN','ELEC','COMP','SOEN','ENCS','ENGR')"
    term_where = ""
    term_params = {}
    if term:
        term_where = " AND termcode = :term"
        term_params["term"] = term

    subjects = db.session.execute(db.text(f"""
        SELECT DISTINCT subject FROM scheduleterm
        WHERE subject IS NOT NULL{ece_filter}{term_where} ORDER BY subject
    """), term_params).scalars().all()

    components = db.session.execute(db.text(f"""
        SELECT DISTINCT componentcode FROM scheduleterm
        WHERE componentcode IS NOT NULL{ece_filter}{term_where} ORDER BY componentcode
    """), term_params).scalars().all()

    buildings = db.session.execute(db.text(f"""
        SELECT DISTINCT buildingcode FROM scheduleterm
        WHERE buildingcode IS NOT NULL AND buildingcode != ''{ece_filter}{term_where}
        ORDER BY buildingcode
    """), term_params).scalars().all()

    plans = db.session.execute(db.text("""
        SELECT planid, planname, program, entryterm, option
        FROM sequenceplan
        ORDER BY planname
    """)).mappings().all()

    return jsonify({
        "terms": term_options,
        "subjects": subjects,
        "components": components,
        "buildings": buildings,
        "plans": [dict(p) for p in plans],
    })


@app.get("/api/plans/<int:planid>/terms")
def api_plan_terms(planid):
    """Return the sequence terms for a given plan."""
    rows = db.session.execute(db.text("""
        SELECT sequencetermid, yearnumber, season, workterm, notes
        FROM sequenceterm
        WHERE planid = :planid
        ORDER BY yearnumber ASC,
                 CASE season
                    WHEN 'fall'   THEN 1
                    WHEN 'winter' THEN 2
                    WHEN 'summer' THEN 3
                    ELSE 4
                 END ASC
    """), {"planid": planid}).mappings().all()

    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
