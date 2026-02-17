import os
import json
from datetime import date
from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError

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


def logactivity(
    eventtype: str,
    title: str,
    actorname: str | None = None,
    metadata: dict | None = None,
):
    if metadata is None:
        metadata = {}

    db.session.execute(
        db.text(
            """
            insert into activitylog (actorname, eventtype, title, metadata)
            values (:actorname, :eventtype, :title, cast(:metadata as jsonb));
        """
        ),
        {
            "actorname": actorname,
            "eventtype": eventtype,
            "title": title,
            "metadata": json.dumps(metadata),
        },
    )
    db.session.commit()


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

    # only show 3 recent items on dashboard
    recentactivity = (
        db.session.execute(
            db.text(
                """
            select createdat, actorname, title
            from activitylog
            order by createdat desc
            limit 3;
        """
            )
        )
        .mappings()
        .all()
    )

    return render_template(
        ROUTE_TEMPLATES["/"],
        scheduler_status=scheduler_status,
        recentactivity=recentactivity,
    )


# Generate Schedule trigger (button on dashboard)
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
        db.text(
            """
            insert into schedulerun (name, status)
            values (:name, 'generated');
        """
        ),
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


# view all activity + filter by date
@app.get("/activity")
def activity():
    startdate = request.args.get("startdate")  # YYYY-MM-DD
    enddate = request.args.get("enddate")  # YYYY-MM-DD

    where = []
    params = {}

    # Validate date formats
    if startdate:
        try:
            date.fromisoformat(startdate)
        except ValueError:
            return jsonify({"error": "Invalid startdate format. Use YYYY-MM-DD"}), 400
        where.append("createdat >= CAST(:startdate AS date)")
        params["startdate"] = startdate

    if enddate:
        try:
            date.fromisoformat(enddate)
        except ValueError:
            return jsonify({"error": "Invalid enddate format. Use YYYY-MM-DD"}), 400
        where.append("createdat < (CAST(:enddate AS date) + interval '1 day')")
        params["enddate"] = enddate

    wheresql = ""
    if where:
        wheresql = "where " + " and ".join(where)

    logs = (
        db.session.execute(
            db.text(
                f"""
            select activityid, createdat, actorname, eventtype, title
            from activitylog
            {wheresql}
            order by createdat desc
            limit 300;
        """
            ),
            params,
        )
        .mappings()
        .all()
    )

    today = date.today().isoformat()

    return render_template(
        ROUTE_TEMPLATES["/activity"],
        logs=logs,
        startdate=startdate or "",
        enddate=enddate or "",
        today=today,
    )

@app.get("/catalog")
def catalog():
    plans = (
        db.session.execute(
            db.text(
                """
        select planid, planname, program, entryterm, option, durationyears, publishedon
        from sequenceplan
        order by publishedon desc, planid asc;
    """
            )
        )
        .mappings()
        .all()
    )

    selected_planid = request.args.get("planid", type=int)
    if selected_planid is None and plans:
        selected_planid = plans[0]["planid"]

    terms = []
    if selected_planid is not None:
        terms = (
            db.session.execute(
                db.text(
                    """
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
        """
                ),
                {"planid": selected_planid},
            )
            .mappings()
            .all()
        )

    selected_termid = request.args.get("termid", type=int)
    if selected_termid is None and terms:
        selected_termid = terms[0]["sequencetermid"]

    rows = []
    if selected_termid is not None:
        rows = (
            db.session.execute(
                db.text(
                    """
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
        """
                ),
                {"termid": selected_termid},
            )
            .mappings()
            .all()
        )

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
    "LEC": "#3B82F6",  # Blue
    "TUT": "#10B981",  # Green
    "LAB": "#F59E0B",  # Orange
    "SEM": "#8B5CF6",  # Purple
    "ONL": "#06B6D4",  # Cyan
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

    # PLAN / TERM SEQUENCE FILTER
    if planid or termid:
        query += """
          AND EXISTS (
              SELECT 1
              FROM sequencecourse sc
              JOIN sequenceterm st2
                ON st2.sequencetermid = sc.sequencetermid
              WHERE sc.subject = st.subject
                AND sc.catalog = st.catalog
        """

        if planid:
            query += " AND st2.planid = :planid"
            params["planid"] = planid

        if termid:
            query += " AND sc.sequencetermid = :termid"
            params["termid"] = termid

        query += ")"

    # DIRECT FILTERS
    if term:
        query += " AND st.termcode = :term"
        params["term"] = term

    if subject:
        subjects = [s.strip() for s in subject.split(",") if s.strip()]
        if len(subjects) == 1:
            query += " AND st.subject = :subject"
            params["subject"] = subjects[0]
        elif len(subjects) > 1:
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

    query += """
        ORDER BY st.subject, st.catalog, st.section,
                 st.componentcode, st.classnumber
        LIMIT 500
    """

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

        events.append(
            {
                "id": f"{row['subject']}-{row['catalog']}-{row['section']}-{row['componentcode']}-{row['classnumber']}",
                "title": f"{row['subject']} {row['catalog']}",
                "daysOfWeek": days_of_week,
                "startTime": str(row["classstarttime"]),
                "endTime": str(row["classendtime"]),
                "allDay": False,
                "color": COMPONENT_COLORS.get(row["componentcode"], DEFAULT_COLOR),
                "extendedProps": {
                    "subject": row["subject"],
                    "catalog": row["catalog"],
                    "section": row["section"],
                    "component": row["componentcode"],
                    "coursetitle": row["coursetitle"] or "",
                    "building": row["buildingcode"] or "TBA",
                    "room": row["room"] or "TBA",
                    "enrollment": row["currentenrollment"] or 0,
                    "capacity": row["enrollmentcapacity"] or 0,
                    "waitlist": row["currentwaitlisttotal"] or 0,
                    "waitlistCapacity": row["waitlistcapacity"] or 0,
                    "termcode": row["termcode"],
                },
            }
        )

    return jsonify(events)


@app.get("/api/filters")
def api_filters():
    """
    Return available filter options.
    - Term labels derived from scheduleterm dates (safe: uses text + filters out ancient dates)
    - subjects/components/buildings scoped to the same sequence->schedule join
    - optional: planid + termid scoping if passed
    """
    term = request.args.get("term", type=int)        # scheduleterm.termcode
    planid = request.args.get("planid", type=int)    # sequenceplan.planid (optional)
    termid = request.args.get("termid", type=int)    # sequencetermid (optional)

    ece_subjects = ("COEN", "ELEC", "COMP", "SOEN", "ENCS", "ENGR")

    def label_from_ymd(ymd: str | None) -> str:
        if not ymd:
            return "Unknown term"
        # ymd like "2025-01-13"
        y = int(ymd[0:4])
        m = int(ymd[5:7])
        if 1 <= m <= 4:
            return f"Winter {y}"
        if 5 <= m <= 8:
            return f"Summer {y}"
        return f"Fall {y}"

    # Base course set (sequence tables) — reused everywhere
    params = {"ece_subjects": tuple(ece_subjects)}

    base_courses_cte = """
        WITH base_courses AS (
            SELECT DISTINCT sc.subject, sc.catalog
            FROM sequencecourse sc
            JOIN sequenceterm st
              ON st.sequencetermid = sc.sequencetermid
            WHERE sc.subject IN :ece_subjects
    """

    if planid:
        base_courses_cte += " AND st.planid = :planid"
        params["planid"] = planid

    if termid:
        base_courses_cte += " AND sc.sequencetermid = :termid"
        params["termid"] = termid

    base_courses_cte += ")"

    # TERMS: safe min date (as TEXT) and ignore ancient/garbage dates
    terms_rows = db.session.execute(
        db.text(
            base_courses_cte
            + """
            SELECT
              sch.termcode,
              to_char(
                MIN(sch.classstartdate) FILTER (
                  WHERE sch.classstartdate BETWEEN DATE '2000-01-01' AND DATE '2100-12-31'
                ),
                'YYYY-MM-DD'
              ) AS first_date_ymd
            FROM scheduleterm sch
            JOIN base_courses bc
              ON bc.subject = sch.subject
             AND bc.catalog = sch.catalog
            GROUP BY sch.termcode
            ORDER BY sch.termcode DESC;
            """
        ),
        params,
    ).mappings().all()

    term_options = [
        {"code": r["termcode"], "name": label_from_ymd(r["first_date_ymd"])}
        for r in terms_rows
        if r["termcode"] is not None
    ]

    # Apply selected term filter to other dropdowns
    term_where = ""
    if term:
        term_where = " AND sch.termcode = :term"
        params["term"] = term

    subjects = db.session.execute(
        db.text(
            base_courses_cte
            + f"""
            SELECT DISTINCT sch.subject
            FROM scheduleterm sch
            JOIN base_courses bc
              ON bc.subject = sch.subject
             AND bc.catalog = sch.catalog
            WHERE sch.subject IS NOT NULL
              {term_where}
            ORDER BY sch.subject;
            """
        ),
        params,
    ).scalars().all()

    components = db.session.execute(
        db.text(
            base_courses_cte
            + f"""
            SELECT DISTINCT sch.componentcode
            FROM scheduleterm sch
            JOIN base_courses bc
              ON bc.subject = sch.subject
             AND bc.catalog = sch.catalog
            WHERE sch.componentcode IS NOT NULL
              {term_where}
            ORDER BY sch.componentcode;
            """
        ),
        params,
    ).scalars().all()

    buildings = db.session.execute(
        db.text(
            base_courses_cte
            + f"""
            SELECT DISTINCT sch.buildingcode
            FROM scheduleterm sch
            JOIN base_courses bc
              ON bc.subject = sch.subject
             AND bc.catalog = sch.catalog
            WHERE sch.buildingcode IS NOT NULL
              AND sch.buildingcode != ''
              {term_where}
            ORDER BY sch.buildingcode;
            """
        ),
        params,
    ).scalars().all()

    plans = db.session.execute(
        db.text("""
            SELECT planid, planname, program, entryterm, option
            FROM sequenceplan
            ORDER BY planname;
        """)
    ).mappings().all()

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
    rows = (
        db.session.execute(
            db.text(
                """
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
    """
            ),
            {"planid": planid},
        )
        .mappings()
        .all()
    )

    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
