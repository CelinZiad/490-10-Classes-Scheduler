import os
import json
from datetime import date
from flask import Flask, render_template, jsonify, request, redirect, url_for, send_file
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

# Algorithm is implemented via algo_runner.py
algorithmimplemented = True


# --- Solution derivation from conflicts ---

def conflict_detail(row: dict) -> str:
    """Build a human-readable detail string from a conflict CSV row."""
    ctype = row.get("Conflict_Type", "")
    course = row.get("Course", "")
    comp1 = row.get("Component1", "")
    comp2 = row.get("Component2", "")
    day = row.get("Day", "")
    t1 = row.get("Time1", "")
    t2 = row.get("Time2", "")
    bldg = row.get("Building", "")
    room = row.get("Room", "")

    if ctype == "Sequence-Missing Course":
        # comp1 = "Semester 3", comp2 = "['COEN490']"
        missing = comp2.strip("[]' ").replace("'", "")
        return f"{comp1}: missing {missing}"

    if ctype == "Sequence-No Valid Combination":
        return f"{comp1}: no valid tutorial/lab combination avoids conflicts"

    if ctype in ("Lecture-Tutorial", "Lecture-Lab"):
        parts = [course]
        if t1 and t2:
            parts.append(f"{comp1 or 'Lecture'} {t1} vs {comp2 or ctype.split('-')[1]} {t2}")
        if day:
            parts.append(f"on day {day}")
        return " — ".join(parts)

    if ctype in ("Sequence-Tutorial Overlap", "Sequence-Lab Overlap",
                 "Sequence-Tutorial/Lab Overlap"):
        parts = [f"{comp1} vs {comp2}"]
        if t1 and t2:
            parts.append(f"{t1} vs {t2}")
        if day:
            parts.append(f"on day {day}")
        return " — ".join(parts)

    if ctype == "Room Conflict":
        loc = f"{bldg}-{room}" if bldg and room else "same room"
        parts = [f"{course} both assigned {loc}"]
        if t1 and t2:
            parts.append(f"{t1} vs {t2}")
        return " — ".join(parts)

    return f"{course}: {comp1} vs {comp2}" if comp1 else course


def derive_solution(conflict_row: dict) -> str:
    """Derive a specific solution description from a conflict CSV row."""
    ctype = conflict_row.get("Conflict_Type", "")
    course = conflict_row.get("Course", "")
    comp1 = conflict_row.get("Component1", "")
    comp2 = conflict_row.get("Component2", "")

    if ctype == "Lecture-Tutorial":
        return f"{course}: Reschedule tutorial to a non-conflicting time slot"

    if ctype == "Lecture-Lab":
        return f"{course}: Reschedule lab to a non-conflicting time slot"

    if ctype == "Room Conflict":
        bldg = conflict_row.get("Building", "")
        room = conflict_row.get("Room", "")
        loc = f" (currently {bldg}-{room})" if bldg and room else ""
        return f"{course}: Assign an alternative lab room{loc}"

    if ctype == "Sequence-Tutorial Overlap":
        return f"{course}: Adjust tutorial sections to avoid overlap between {comp1} and {comp2}"

    if ctype == "Sequence-Lab Overlap":
        return f"{course}: Adjust lab sections to avoid overlap between {comp1} and {comp2}"

    if ctype == "Sequence-Tutorial/Lab Overlap":
        return f"{course}: Adjust tutorial/lab sections to avoid overlap between {comp1} and {comp2}"

    if ctype == "Sequence-Missing Course":
        missing = comp2.strip("[]' ").replace("'", "")
        return f"Add {missing} to the schedule (required in {comp1})"

    if ctype == "Sequence-No Valid Combination":
        return f"{comp1}: Re-evaluate section combinations for sequence courses"

    return f"{course}: Review and resolve {ctype} conflict"


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

    # Run the genetic algorithm
    from algo_runner import run_algorithm

    result = run_algorithm()

    # Log the schedule run
    db.session.execute(
        db.text(
            """
            insert into schedulerun (name, status)
            values (:name, :status);
        """
        ),
        {"name": schedulename, "status": "generated" if result["status"] == "success" else "failed"},
    )
    db.session.commit()

    logactivity(
        eventtype="schedulegenerated",
        title=(
            f'Schedule "{schedulename}": fitness={result["best_fitness"]}, '
            f'generations={result["generations"]}, '
            f'duration={result.get("duration_seconds", 0)}s'
        ),
        actorname="system",
        metadata={
            "schedulename": schedulename,
            "best_fitness": result["best_fitness"],
            "generations": result["generations"],
            "termination_reason": result.get("termination_reason", ""),
            "num_courses": result.get("num_courses", 0),
            "num_conflicts": result["num_conflicts"],
        },
    )

    # Insert conflicts and linked solutions into DB
    if result["conflicts"]:
        # Ensure solution table has conflictid column (one-time migration)
        try:
            db.session.execute(db.text(
                "ALTER TABLE solution ADD COLUMN IF NOT EXISTS "
                "conflictid bigint REFERENCES conflict(conflictid) ON DELETE SET NULL"
            ))
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Clear previous active conflicts and proposed solutions
        db.session.execute(
            db.text("delete from solution where status = 'proposed';")
        )
        db.session.execute(
            db.text("delete from conflict where status = 'active';")
        )
        db.session.commit()

        solutions_added = 0
        for row in result["conflicts"]:
            ctype = row.get("Conflict_Type", "Unknown")
            detail = conflict_detail(row)

            # Store conflict data as JSON for rich frontend display
            conflict_data = json.dumps({
                "type": ctype,
                "course": row.get("Course", ""),
                "detail": detail,
            })

            # Insert conflict and get its ID back
            conflict_row = db.session.execute(
                db.text(
                    """
                    insert into conflict (status, description)
                    values ('active', :description)
                    returning conflictid;
                """
                ),
                {"description": conflict_data},
            ).mappings().first()

            conflict_id = conflict_row["conflictid"] if conflict_row else None

            # Insert linked solution
            desc = derive_solution(row)
            db.session.execute(
                db.text(
                    """
                    insert into solution (status, description, conflictid)
                    values ('proposed', :description, :conflictid);
                """
                ),
                {"description": f"[{ctype}] {desc}", "conflictid": conflict_id},
            )
            solutions_added += 1

        db.session.commit()

        logactivity(
            eventtype="conflictsdetected",
            title=f"Detected {result['num_conflicts']} conflicts",
            actorname="system",
            metadata={"count": result["num_conflicts"]},
        )

        if solutions_added:
            logactivity(
                eventtype="solutionsproposed",
                title=f"Proposed {solutions_added} solutions",
                actorname="system",
                metadata={"count": solutions_added},
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
    rows = (
        db.session.execute(
            db.text(
                """
            select conflictid, status, description, createdat
            from conflict
            where status = 'active'
            order by createdat desc;
        """
            )
        )
        .mappings()
        .all()
    )

    # Parse JSON description into display fields
    parsed = []
    for r in rows:
        try:
            data = json.loads(r["description"])
        except (json.JSONDecodeError, TypeError):
            data = {"type": "Unknown", "course": "", "detail": r["description"]}
        parsed.append({
            "conflictid": r["conflictid"],
            "type": data.get("type", "Unknown"),
            "course": data.get("course", ""),
            "detail": data.get("detail", ""),
            "status": r["status"],
            "createdat": r["createdat"],
        })

    return render_template(ROUTE_TEMPLATES["/conflicts"], conflicts=parsed)


@app.get("/solutions")
def solutions():
    conflict_id = request.args.get("conflictid", type=int)

    if conflict_id:
        rows = (
            db.session.execute(
                db.text(
                    """
                select s.solutionid, s.status, s.description, s.createdat,
                       s.conflictid, c.description as conflict_desc
                from solution s
                left join conflict c on c.conflictid = s.conflictid
                where s.conflictid = :cid
                order by s.createdat desc;
            """
                ),
                {"cid": conflict_id},
            )
            .mappings()
            .all()
        )
    else:
        rows = (
            db.session.execute(
                db.text(
                    """
                select s.solutionid, s.status, s.description, s.createdat,
                       s.conflictid, c.description as conflict_desc
                from solution s
                left join conflict c on c.conflictid = s.conflictid
                order by s.createdat desc;
            """
                )
            )
            .mappings()
            .all()
        )

    return render_template(
        ROUTE_TEMPLATES["/solutions"],
        solutions=rows,
        filtered_conflict=conflict_id,
    )


@app.get("/api/export-csv")
def api_export_csv():
    """Download schedule as CSV with format and source options.

    Query params:
        source: "optimized" (generated) or "original" (scheduleterm)  [default: optimized]
        format: "detailed" (all columns) or "condensed" (key columns) [default: detailed]
    """
    import csv as csv_mod
    import io

    source = request.args.get("source", "optimized")
    fmt = request.args.get("format", "detailed")

    # Get latest schedule name for filename prefix
    try:
        row = db.session.execute(
            db.text("SELECT name FROM schedulerun ORDER BY generatedat DESC LIMIT 1")
        ).mappings().first()
        schedule_name = row["name"] if row else "schedule"
    except Exception:
        schedule_name = "schedule"

    # Column definitions
    all_cols = [
        "subject", "catalog", "section", "componentcode", "termcode",
        "classnumber", "session", "buildingcode", "room",
        "instructionmodecode", "locationcode",
        "currentwaitlisttotal", "waitlistcapacity",
        "enrollmentcapacity", "currentenrollment",
        "departmentcode", "facultycode",
        "classstarttime", "classendtime", "classstartdate", "classenddate",
        "mondays", "tuesdays", "wednesdays", "thursdays", "fridays",
        "saturdays", "sundays", "facultydescription", "career",
        "meetingpatternnumber",
    ]
    condensed_cols = [
        "subject", "catalog", "section", "componentcode",
        "buildingcode", "room", "classstarttime", "classendtime",
        "mondays", "tuesdays", "wednesdays", "thursdays", "fridays",
    ]

    table = "optimized_schedule" if source == "optimized" else "scheduleterm"
    cols = condensed_cols if fmt == "condensed" else all_cols
    col_sql = ", ".join(cols)

    where = (
        "WHERE classstarttime IS NOT NULL AND classstarttime != '00:00:00'"
    )
    if source == "original":
        where += " AND departmentcode = 'ELECCOEN'"

    try:
        rows = db.session.execute(
            db.text(
                f"SELECT {col_sql} FROM {table} {where} "
                "ORDER BY subject, catalog, section, componentcode"
            )
        ).mappings().all()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"error": f"No {source} schedule found. Generate a schedule first."}), 404

    if not rows:
        return jsonify({"error": f"No {source} schedule data found."}), 404

    buf = io.StringIO()
    writer = csv_mod.DictWriter(buf, fieldnames=cols)
    writer.writeheader()
    for r in rows:
        writer.writerow(dict(r))

    label = "detailed" if fmt == "detailed" else "condensed"
    filename = f"{schedule_name}-{label}.csv"
    resp = app.response_class(buf.getvalue(), mimetype="text/csv")
    resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return resp


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
    source = request.args.get("source", "scheduleterm")  # "scheduleterm" or "optimized"

    # Choose source table
    source_table = "optimized_schedule" if source == "optimized" else "scheduleterm"

    query = f"""
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
        FROM {source_table} st
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

    try:
        rows = db.session.execute(db.text(query), params).mappings().all()
    except SQLAlchemyError:
        db.session.rollback()
        if source == "optimized":
            return jsonify({"error": "No optimized schedule found. Generate a schedule first."}), 404
        return jsonify({"error": "Database error loading events."}), 500

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
