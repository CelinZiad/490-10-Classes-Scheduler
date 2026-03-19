import os
import csv
import io
import json
from datetime import date, timedelta
from typing import Optional
from flask import Flask, render_template, jsonify, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
import json
import io
import csv as csv_mod
import traceback

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
    "/import": "import-data.html",
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

def _semester_label(raw: str, semester_labels: Optional[dict]) -> str:
    """Convert 'Semester 3' → 'Fall Year 2 (COEN)' using the labels map."""
    if not semester_labels or not raw.startswith("Semester "):
        return raw
    num = raw.replace("Semester ", "")
    return semester_labels.get(num, raw)


def conflict_detail(row: dict, semester_labels: dict = None) -> str:
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
        sem = _semester_label(comp1, semester_labels)
        return f"{sem}: missing {missing}"

    if ctype == "Sequence-No Valid Combination":
        sem = _semester_label(comp1, semester_labels)
        return f"{sem}: no valid tutorial/lab combination avoids conflicts"

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


def derive_solution(conflict_row: dict, semester_labels: dict = None) -> str:
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
        sem = _semester_label(comp1, semester_labels)
        return f"Add {missing} to the schedule (required in {sem})"

    if ctype == "Sequence-No Valid Combination":
        sem = _semester_label(comp1, semester_labels)
        return f"{sem}: Re-evaluate section combinations for sequence courses"

    return f"{course}: Review and resolve {ctype} conflict"


def logactivity(
    eventtype: str,
    title: str,
    actorname: Optional[str] = None,
    metadata: Optional[dict] = None,
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
    from pathlib import Path
    import sys

    PROJECT_ROOT = Path(__file__).resolve().parent
    ALGO_DIR = PROJECT_ROOT / "timetable-algo"
    GENETIC_DIR = ALGO_DIR / "genetic_algo"

    if str(GENETIC_DIR) not in sys.path:
        sys.path.insert(0, str(GENETIC_DIR))

    import config

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
        default_target_season=config.TARGET_SEASON,
        default_academic_year=config.ACADEMIC_YEAR,
    )


# Generate Schedule trigger (button on dashboard)
@app.post("/schedulerrun")
def postschedulerrun():
    schedulename = request.form.get("schedulename", "schedule-draft").strip() or "schedule-draft"

    try:
        season = int(request.form.get("season", 2))
    except (TypeError, ValueError):
        season = 2

    try:
        academic_year = int(request.form.get("academic_year", 2026))
    except (TypeError, ValueError):
        academic_year = 2026

    # always log that someone pressed the button
    logactivity(
        eventtype="schedulerrunrequested",
        title=f'Schedule run requested: "{schedulename}"',
        actorname="admin",
        metadata={
            "schedulename": schedulename,
            "season": season,
            "academic_year": academic_year,
        },
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

    result = run_algorithm(
        target_season=season,
        academic_year=academic_year,
    )

    # Log the schedule run
    run_status = "generated" if result["status"] == "success" else "failed"
    db.session.execute(
        db.text(
            """
            insert into schedulerun (name, status)
            values (:name, :status);
        """
        ),
        {"name": schedulename, "status": run_status},
    )
    db.session.commit()

    if result["status"] == "success":
        logactivity(
            eventtype="schedulegenerated",
            title=(
                f'Schedule "{schedulename}": fitness={result["best_fitness"]}, '
                f'generations={result["generations"]}, '
                f'duration={result.get("duration_seconds", 0):.1f}s'
            ),
            actorname="system",
            metadata={
                "schedulename": schedulename,
                "season": season,
                "academic_year": academic_year,
                "best_fitness": result["best_fitness"],
                "generations": result["generations"],
                "termination_reason": result.get("termination_reason", ""),
                "num_courses": result.get("num_courses", 0),
                "num_conflicts": result["num_conflicts"],
            },
        )
    else:
        logactivity(
            eventtype="schedulefailed",
            title=(
                f'Schedule "{schedulename}" failed: '
                f'{result.get("termination_reason", "unknown error")}'
            ),
            actorname="system",
            metadata={
                "schedulename": schedulename,
                "season": season,
                "academic_year": academic_year,
            },
        )

    semester_labels = result.get("semester_labels", {})

    if result["conflicts"]:
        try:
            db.session.execute(db.text(
                "ALTER TABLE solution ADD COLUMN IF NOT EXISTS "
                "conflictid bigint REFERENCES conflict(conflictid) ON DELETE SET NULL"
            ))
            db.session.commit()
        except Exception:
            db.session.rollback()

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
            detail = conflict_detail(row, semester_labels=semester_labels)

            conflict_data = json.dumps({
                "type": ctype,
                "course": row.get("Course", ""),
                "detail": detail,
            })

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

            desc = derive_solution(row, semester_labels=semester_labels)
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

@app.route("/delete-course", methods=["POST"])
def delete_course():
    data = request.get_json()

    subject = data.get("subject")
    catalog = data.get("catalog")
    termid = data.get("termid")

    if not subject or not catalog or not termid:
        return jsonify({"error": "Missing data"}), 400

    try:
        result = db.session.execute(
            db.text("""
                DELETE FROM sequencecourse
                WHERE subject = :subject
                AND catalog = :catalog
                AND sequencetermid = :termid
            """),
            {
                "subject": subject,
                "catalog": catalog,
                "termid": termid
            }
        )

        db.session.commit()

        return jsonify({
            "message": f"Deleted {result.rowcount} course from this term"
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

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


@app.get('/waitlist')
def waitlist():
    return render_template(ROUTE_TEMPLATES.get('/waitlist', 'waitlist.html'))


@app.get('/api/waitlist/filters')
def api_waitlist_filters():
    """Return distinct term / subject / component values for the waitlist filter bar."""
    source = request.args.get('source', 'scheduleterm')
    table = 'optimized_schedule' if source == 'optimized' else 'scheduleterm'

    def _label(ymd):
        if not ymd:
            return 'Unknown term'
        y, m = int(ymd[:4]), int(ymd[5:7])
        if 1 <= m <= 4:
            return f'Winter {y}'
        if 5 <= m <= 8:
            return f'Summer {y}'
        return f'Fall {y}'

    try:
        if source == 'optimized':
            from_clause = """optimized_schedule o
                JOIN sequencecourse c ON c.subject = o.subject AND c.catalog = o.catalog"""
            base_where = "WHERE o.classstarttime IS NOT NULL AND o.componentcode = 'LAB'"
            col_prefix = "o."
        else:
            from_clause = """scheduleterm st
                JOIN sequencecourse c ON c.subject = st.subject AND c.catalog = st.catalog"""
            base_where = """
                WHERE st.waitlistcapacity IS NOT NULL
                  AND st.waitlistcapacity > 0
                  AND st.currentwaitlisttotal >= st.waitlistcapacity
                  AND st.componentcode = 'LAB'
            """
            col_prefix = "st."

        terms_raw = db.session.execute(db.text(f"""
            SELECT {col_prefix}termcode AS termcode,
                   to_char(MIN({col_prefix}classstartdate)
                           FILTER (WHERE {col_prefix}classstartdate BETWEEN '2000-01-01' AND '2100-12-31'),
                           'YYYY-MM-DD') AS first_date
            FROM {from_clause}
            {base_where} AND {col_prefix}termcode IS NOT NULL
            GROUP BY {col_prefix}termcode ORDER BY {col_prefix}termcode DESC
        """)).mappings().all()

        # Deduplicate by semester label and keep only Fall 2025 – Winter 2026
        seen_labels = set()
        terms = []
        for r in terms_raw:
            label = _label(r['first_date'])
            if label in seen_labels:
                continue
            if label not in ('Fall 2025', 'Winter 2026'):
                continue
            seen_labels.add(label)
            terms.append({'code': r['termcode'], 'name': label})

        subjects = db.session.execute(db.text(f"""
            SELECT DISTINCT {col_prefix}subject AS subject FROM {from_clause}
            {base_where} AND {col_prefix}subject IS NOT NULL ORDER BY {col_prefix}subject
        """)).scalars().all()

        components = db.session.execute(db.text(f"""
            SELECT DISTINCT {col_prefix}componentcode AS componentcode FROM {from_clause}
            {base_where} AND {col_prefix}componentcode IS NOT NULL ORDER BY {col_prefix}componentcode
        """)).scalars().all()

        return jsonify({
            'terms': terms,
            'subjects': subjects,
            'components': components,
        })
    except Exception as e:
        app.logger.error('waitlist filters error: %s', e)
        return jsonify({'terms': [], 'subjects': [], 'components': []}), 500


@app.get('/api/waitlist/stats')
def api_waitlist_stats():
    source = request.args.get('source', 'scheduleterm')
    term = request.args.get('term', type=int)
    subject = request.args.get('subject')
    component = request.args.get('component')

    try:
        params = {}
        if source == 'optimized':
            query = """
                SELECT o.subject, o.catalog, o.section, o.componentcode,
                       MAX(o.currentwaitlisttotal) AS currentwaitlisttotal,
                       MAX(o.waitlistcapacity) AS waitlistcapacity,
                       MAX(o.enrollmentcapacity) AS enrollmentcapacity,
                       MAX(o.currentenrollment) AS currentenrollment
                FROM optimized_schedule o
                JOIN sequencecourse c ON c.subject = o.subject AND c.catalog = o.catalog
                WHERE o.classstarttime IS NOT NULL
                  AND o.componentcode = 'LAB'
            """
            if term:
                query += " AND o.termcode = :term"
                params['term'] = term
            if subject:
                query += " AND o.subject = :subject"
                params['subject'] = subject
            if component:
                query += " AND o.componentcode = :component"
                params['component'] = component
            query += """
                GROUP BY o.subject, o.catalog, o.section, o.componentcode
                ORDER BY o.subject, o.catalog, o.section
            """

            rows = db.session.execute(db.text(query), params).mappings().all()
            out = [{
                'subject': r['subject'],
                'catalog': r['catalog'],
                'section': r.get('section'),
                'component': r.get('componentcode'),
                'waitlist': r.get('currentwaitlisttotal') or 0,
                'waitlistCapacity': r.get('waitlistcapacity') or 0,
                'enrollmentCapacity': r.get('enrollmentcapacity') or 0,
                'currentEnrollment': r.get('currentenrollment') or 0,
            } for r in rows]
        else:
            query = """
                SELECT st.subject, st.catalog, st.section, st.componentcode,
                       MAX(st.currentwaitlisttotal) AS currentwaitlisttotal,
                       MAX(st.waitlistcapacity) AS waitlistcapacity,
                       MAX(st.enrollmentcapacity) AS enrollmentcapacity,
                       MAX(st.currentenrollment) AS currentenrollment
                FROM scheduleterm st
                JOIN sequencecourse c ON c.subject = st.subject AND c.catalog = st.catalog
                WHERE st.waitlistcapacity IS NOT NULL
                  AND st.waitlistcapacity > 0
                  AND st.currentwaitlisttotal >= st.waitlistcapacity
                  AND st.componentcode = 'LAB'
            """
            if term:
                query += " AND st.termcode = :term"
                params['term'] = term
            if subject:
                query += " AND st.subject = :subject"
                params['subject'] = subject
            if component:
                query += " AND st.componentcode = :component"
                params['component'] = component
            query += """
                GROUP BY st.subject, st.catalog, st.section, st.componentcode
                ORDER BY MAX(st.currentwaitlisttotal) DESC
            """

            rows = db.session.execute(db.text(query), params).mappings().all()
            out = [{
                'subject': r['subject'],
                'catalog': r['catalog'],
                'section': r.get('section'),
                'component': r.get('componentcode'),
                'waitlist': r.get('currentwaitlisttotal') or 0,
                'waitlistCapacity': r.get('waitlistcapacity') or 0,
                'enrollmentCapacity': r.get('enrollmentcapacity') or 0,
                'currentEnrollment': r.get('currentenrollment') or 0,
            } for r in rows]
        return jsonify(out)
    except Exception as e:
        app.logger.error('waitlist stats error: %s', e)
        return jsonify({'error': 'DB error loading waitlist stats'}), 500


@app.get('/api/waitlist/students')
def api_waitlist_students():
    subject = request.args.get('subject')
    catalog = request.args.get('catalog')
    if not subject or not catalog:
        return jsonify({'error': 'subject and catalog required'}), 400

    try:
        rows = db.session.execute(
            db.text(
                """
                SELECT DISTINCT sss.studyid, sss.studyname
                FROM studentschedulestudy sss
                JOIN studentschedule ss ON ss.studyid = sss.studyid
                JOIN studentscheduleclass ssc ON ssc.studentscheduleid = ss.studentscheduleid
                JOIN "section" sec ON sec.term = ssc.term AND sec.classnumber = ssc.classnumber AND sec."section" = ssc."section"
                WHERE sec.subject = :subject AND sec.catalog = :catalog
                ORDER BY sss.studyname NULLS LAST, sss.studyid
                LIMIT 500
                """,
            ),
            {'subject': subject, 'catalog': catalog},
        ).mappings().all()

        # Fallback: if no students found for this specific course, return all known students
        if not rows:
            rows = db.session.execute(
                db.text(
                    """
                    SELECT DISTINCT studyid, studyname
                    FROM studentschedulestudy
                    ORDER BY studyname NULLS LAST, studyid
                    LIMIT 500
                    """
                )
            ).mappings().all()

        out = [{'studyid': r['studyid'], 'studyname': r['studyname']} for r in rows]
        return jsonify(out)
    except Exception as e:
        app.logger.error('waitlist students error: %s', e)
        return jsonify({'error': 'DB error loading students'}), 500


@app.post('/api/waitlist/run')
def api_waitlist_run():
    data = request.get_json(silent=True) or {}
    students = data.get('students') or []
    subject = (data.get('subject') or '').strip().upper()
    catalog = (data.get('catalog') or '').strip()

    app.logger.info('POST /api/waitlist/run: subject=%s, catalog=%s, students=%s', subject, catalog, students)

    if not subject or not catalog or not students:
        return jsonify({'error': 'subject, catalog and students are required'}), 400

    try:
        # Import algorithm pieces dynamically
        from waitlist_algorithm.database_connection.db import get_conn
        from waitlist_algorithm.algorithm.students_busy import load_students_busy_from_db, get_two_week_anchor_monday
        from waitlist_algorithm.algorithm.room_busy import load_room_busy_for_course
        from waitlist_algorithm.algorithm.lab_generator import propose_waitlist_slots
        from waitlist_algorithm.algorithm.database_results import save_lab_results_to_db

        conn = get_conn()
        cur = conn.cursor()

        students_busy = load_students_busy_from_db(cur, students)
        week1 = get_two_week_anchor_monday(cur, students)
        room_busy = load_room_busy_for_course(cur, subject, catalog, week1)

        lab_start_time = [  # minutes from midnight
            8*60 + 45,
            11*60 + 45,
            14*60 + 45,
            17*60 + 45,
        ]

        results = propose_waitlist_slots(
            waitlisted_students=students,
            students_busy=students_busy,
            room_busy=room_busy,
            lab_start_times=lab_start_time,
        )

        # persist results
        save_lab_results_to_db(cur, subject, catalog, 180, results)
        conn.commit()

        # Format results for JSON — human-readable
        DAY_NAMES = {
            1: 'Monday (Week 1)', 2: 'Tuesday (Week 1)', 3: 'Wednesday (Week 1)',
            4: 'Thursday (Week 1)', 5: 'Friday (Week 1)', 6: 'Saturday (Week 1)', 7: 'Sunday (Week 1)',
            8: 'Monday (Week 2)', 9: 'Tuesday (Week 2)', 10: 'Wednesday (Week 2)',
            11: 'Thursday (Week 2)', 12: 'Friday (Week 2)', 13: 'Saturday (Week 2)', 14: 'Sunday (Week 2)',
        }

        def _fmt_time(mins):
            return f"{mins // 60:02d}:{mins % 60:02d}"

        out = []
        for (day, start), ids in sorted(results.items()):
            out.append({
                'day': DAY_NAMES.get(day, f'Day {day}'),
                'time': f"{_fmt_time(start)} – {_fmt_time(start + 180)}",
                'students': ids,
            })
        return jsonify({'status': 'success', 'results': out})

    except Exception as e:
        app.logger.error('waitlist run failed: %s', traceback.format_exc())
        return jsonify({'error': 'Algorithm execution failed'}), 500


@app.get('/api/waitlist/download')
def api_waitlist_download():
    subject = request.args.get('subject')
    catalog = request.args.get('catalog')
    source = request.args.get('source', 'scheduleterm')
    if not subject or not catalog:
        return jsonify({'error': 'subject and catalog required'}), 400

    source_label = 'optimized' if source == 'optimized' else 'original'

    try:
        rows = db.session.execute(
            db.text(
                """
                SELECT subject, catalog, classstarttime, classendtime, mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays, studyids
                FROM lab_slot_result
                WHERE subject = :subject AND catalog = :catalog
                ORDER BY classstarttime
                """
            ),
            {'subject': subject, 'catalog': catalog},
        ).mappings().all()

        if not rows:
            return jsonify({'error': 'No results found'}), 404

        buf = io.StringIO()
        w = csv_mod.writer(buf)
        w.writerow(['subject','catalog','start','end','mondays','tuesdays','wednesdays','thursdays','fridays','saturdays','sundays','studentids'])
        for r in rows:
            raw_ids = r['studyids'] or []
            if isinstance(raw_ids, (list, tuple)):
                student_str = ', '.join(str(sid) for sid in raw_ids)
            else:
                student_str = str(raw_ids)
            w.writerow([
                r['subject'], r['catalog'], str(r['classstarttime']), str(r['classendtime']),
                r['mondays'], r['tuesdays'], r['wednesdays'], r['thursdays'], r['fridays'], r['saturdays'], r['sundays'],
                student_str
            ])
        resp = app.response_class(buf.getvalue(), mimetype='text/csv')
        resp.headers['Content-Disposition'] = f'attachment; filename={source_label}-waitlist-{subject}-{catalog}.csv'
        return resp
    except Exception as e:
        app.logger.error('waitlist download error: %s', e)
        return jsonify({'error': 'Error generating CSV'}), 500


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
                            st.componentcode,
                            st.classstarttime, st.classendtime,
                            st.mondays, st.tuesdays, st.wednesdays,
                            st.thursdays, st.fridays, st.saturdays,
                            st.sundays,
                            st.classstartdate, st.classenddate)
            st.subject, st.catalog, st.section, st.componentcode,
            st.classnumber,
            COALESCE(NULLIF(st.buildingcode, ''), lr.building) AS buildingcode,
            COALESCE(NULLIF(st.room, ''), lr.room) AS room,
            st.classstarttime, st.classendtime,
            st.mondays, st.tuesdays, st.wednesdays, st.thursdays,
            st.fridays, st.saturdays, st.sundays,
            st.termcode, st.currentenrollment, st.enrollmentcapacity,
            st.currentwaitlisttotal, st.waitlistcapacity,
            st.meetingpatternnumber,
            st.classstartdate, st.classenddate,
            c.title AS coursetitle
        FROM {source_table} st
        LEFT JOIN catalog c
          ON c.subject = st.subject
         AND c.catalog = st.catalog
         AND c.career  = 'UGRD'
        LEFT JOIN courselabs cl
          ON cl.subject = st.subject
         AND cl.catalog = st.catalog
        LEFT JOIN labrooms lr
          ON lr.labroomid = cl.labroomid
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

    # TERM CODE FILTER
    # When a semester (termid) is selected, auto-detect the correct termcode
    # from the season so we only show the latest year's schedule data.
    # We find the MAX termcode that has data for the courses in the selected
    # sequence term AND matches the season's month range.
    if termid and source != "optimized":
        season = db.session.execute(
            db.text("SELECT season FROM sequenceterm WHERE sequencetermid = :tid"),
            {"tid": termid},
        ).scalar()

        if season in ("fall", "winter", "summer"):
            month_ranges = {"fall": (9, 12), "winter": (1, 4), "summer": (5, 8)}
            m1, m2 = month_ranges[season]
            latest_term = db.session.execute(
                db.text("""
                    SELECT MAX(sch.termcode)
                    FROM scheduleterm sch
                    JOIN sequencecourse sc
                      ON sc.subject = sch.subject AND sc.catalog = sch.catalog
                    WHERE sc.sequencetermid = :tid
                      AND EXTRACT(MONTH FROM sch.classstartdate) BETWEEN :m1 AND :m2
                      AND sch.classstartdate > '2000-01-01'
                """),
                {"tid": termid, "m1": m1, "m2": m2},
            ).scalar()

            if latest_term:
                query += " AND st.termcode = :auto_term"
                params["auto_term"] = latest_term
    elif term and source != "optimized":
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
                 st.componentcode,
                 st.classstarttime, st.classendtime,
                 st.mondays, st.tuesdays, st.wednesdays,
                 st.thursdays, st.fridays, st.saturdays,
                 st.sundays,
                 st.classstartdate, st.classenddate
        LIMIT 10000
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

        # FullCalendar startRecur/endRecur bound recurring events to a date range.
        # endRecur is exclusive, so add one day past classenddate.
        start_recur = None
        end_recur = None
        if row["classstartdate"]:
            start_recur = str(row["classstartdate"])
        if row["classenddate"]:
            end_recur = str(row["classenddate"] + timedelta(days=1))

        events.append(
            {
                "id": f"{row['subject']}-{row['catalog']}-{row['section']}-{row['componentcode']}-{row['classnumber']}-{row['meetingpatternnumber']}",
                "title": f"{row['subject']} {row['catalog']}",
                "daysOfWeek": days_of_week,
                "startTime": str(row["classstarttime"]),
                "endTime": str(row["classendtime"]),
                "startRecur": start_recur,
                "endRecur": end_recur,
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

@app.get("/api/list-optimized")
def api_list_optimized():
    subject = request.args.get("subject")
    component = request.args.get("component")
    building = request.args.get("building")

    query = """
        SELECT DISTINCT ON (
            st.subject, st.catalog, st.section,
            st.componentcode, st.classnumber
        )
            st.id,
            st.subject,
            st.catalog,
            st.section,
            st.componentcode,
            st.classnumber,
            st.buildingcode,
            st.room,
            st.classstarttime,
            st.classendtime,
            st.mondays,
            st.tuesdays,
            st.wednesdays,
            st.thursdays,
            st.fridays,
            st.saturdays,
            st.sundays,
            st.currentenrollment,
            st.enrollmentcapacity,
            st.currentwaitlisttotal,
            st.waitlistcapacity,
            c.title AS coursetitle
        FROM optimized_schedule st
        LEFT JOIN catalog c
          ON c.subject = st.subject
         AND c.catalog = st.catalog
         AND c.career = 'UGRD'
       
    
    """

    params = {}

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

    # GROUP BY DAY
    grouped = {
        "Monday": [],
        "Tuesday": [],
        "Wednesday": [],
        "Thursday": [],
        "Friday": [],
        "Saturday": [],
        "Sunday": []
    }

    def create_entry(row, day_name):
        return {
            "id": row["id"],
            "subject": row["subject"],
            "catalog": row["catalog"],
            "section": row["section"],
            "component": row["componentcode"],
            "coursetitle": row["coursetitle"] or "",
            "day": day_name,
            "startTime": str(row["classstarttime"]),
            "endTime": str(row["classendtime"]),
            "building": row["buildingcode"] or "TBA",
            "room": row["room"] or "TBA",
            "enrollment": row["currentenrollment"] or 0,
            "capacity": row["enrollmentcapacity"] or 0,
            "waitlist": row["currentwaitlisttotal"] or 0,
            "waitlistCapacity": row["waitlistcapacity"] or 0,
        }

    for row in rows:
        if row["mondays"]:
            grouped["Monday"].append(create_entry(row, "Monday"))
        if row["tuesdays"]:
            grouped["Tuesday"].append(create_entry(row, "Tuesday"))
        if row["wednesdays"]:
            grouped["Wednesday"].append(create_entry(row, "Wednesday"))
        if row["thursdays"]:
            grouped["Thursday"].append(create_entry(row, "Thursday"))
        if row["fridays"]:
            grouped["Friday"].append(create_entry(row, "Friday"))
        if row["saturdays"]:
            grouped["Saturday"].append(create_entry(row, "Saturday"))
        if row["sundays"]:
            grouped["Sunday"].append(create_entry(row, "Sunday"))

    return jsonify(grouped)

@app.route("/api/update-class/<int:class_id>", methods=["PUT"])
def update_class(class_id):
    data = request.json

    # Ensure time format is HH:MM:SS
    def fix_time(t):
        if t and len(t) == 5:
            return t + ":00"
        return t

    query = """
        UPDATE optimized_schedule
        SET
            subject = :subject,
            catalog = :catalog,
            section = :section,
            componentcode = :component,
            classstarttime = :startTime,
            classendtime = :endTime,
            buildingcode = :building,
            room = :room,
            currentenrollment = :enrollment,
            enrollmentcapacity = :capacity,
            currentwaitlisttotal = :waitlist,
            waitlistcapacity = :waitlistCapacity,
            mondays = :monday,
            tuesdays = :tuesday,
            wednesdays = :wednesday,
            thursdays = :thursday,
            fridays = :friday
        WHERE id = :id
    """

    # Reset all days
    params = {
        "id": class_id,
        "subject": data["subject"],
        "catalog": data["catalog"],
        "section": data["section"],
        "component": data["component"],
        "startTime": fix_time(data["startTime"]),
        "endTime": fix_time(data["endTime"]),
        "building": data["building"],
        "room": data["room"],
        "enrollment": data["enrollment"],
        "capacity": data["capacity"],
        "waitlist": data["waitlist"],
        "waitlistCapacity": data["waitlistCapacity"],
        "monday": False,
        "tuesday": False,
        "wednesday": False,
        "thursday": False,
        "friday": False,
    }

    # Map selected day
    if "day" in data:
        if data["day"] == "Monday":
            params["monday"] = True
        elif data["day"] == "Tuesday":
            params["tuesday"] = True
        elif data["day"] == "Wednesday":
            params["wednesday"] = True
        elif data["day"] == "Thursday":
            params["thursday"] = True
        elif data["day"] == "Friday":
            params["friday"] = True

    result = db.session.execute(db.text(query), params)
    db.session.commit()

    print("Rows updated:", result.rowcount)  # DEBUG

    return jsonify({"status": "success"})

@app.route("/api/delete-class/<int:class_id>", methods=["DELETE"])
def delete_class(class_id):
    db.session.execute(
        db.text("DELETE FROM optimized_schedule WHERE id = :id"),
        {"id": class_id}
    )
    db.session.commit()

    return jsonify({"status": "deleted"})

@app.route("/api/create-class", methods=["POST"])
def create_class():
    data = request.json

    day_map = {
        "Monday": "mondays",
        "Tuesday": "tuesdays",
        "Wednesday": "wednesdays",
        "Thursday": "thursdays",
        "Friday": "fridays"
    }

    query = """
        INSERT INTO optimized_schedule (
            subject, catalog, section, componentcode,
            classstarttime, classendtime,
            buildingcode, room,
            currentenrollment, enrollmentcapacity,
            currentwaitlisttotal, waitlistcapacity,
            mondays, tuesdays, wednesdays, thursdays, fridays
        )
        VALUES (
            :subject, :catalog, :section, :component,
            :startTime, :endTime,
            :building, :room,
            :enrollment, :capacity,
            :waitlist, :waitlistCapacity,
            :monday, :tuesday, :wednesday, :thursday, :friday
        )
    """

    params = {
        "subject": data["subject"],
        "catalog": data["catalog"],
        "section": data["section"],
        "component": data["component"],
        "startTime": data["startTime"],
        "endTime": data["endTime"],
        "building": data["building"],
        "room": data["room"],
        "enrollment": data["enrollment"],
        "capacity": data["capacity"],
        "waitlist": data["waitlist"],
        "waitlistCapacity": data["waitlistCapacity"],
        "monday": False,
        "tuesday": False,
        "wednesday": False,
        "thursday": False,
        "friday": False,
    }

    if data["day"] in day_map:
        params[day_map[data["day"]]] = True

    db.session.execute(db.text(query), params)
    db.session.commit()

    return jsonify({"status": "created"})

@app.get("/api/optimized-date-range")
def api_optimized_date_range():
    """Return the actual date range of the optimized schedule.

    Used by the frontend to navigate the calendar to the correct dates,
    since the optimized schedule's termcode may not align with the plan
    name's academic year (e.g. plan "25-26" but data in 2026-27).

    Concordia termcode offsets relative to plan name year:
      2250-2260 → +10,  2260-2270 → 0,
      2270-2280 → -10,  2280-2290 → -10
    Rather than relying on these offsets, we query the actual dates.
    """
    planid = request.args.get("planid", type=int)
    termid = request.args.get("termid", type=int)

    query = """
        SELECT MIN(os.classstartdate) AS min_date,
               MAX(os.classenddate)   AS max_date
        FROM optimized_schedule os
        WHERE os.classstartdate IS NOT NULL
    """
    params = {}

    if planid or termid:
        query += """
          AND EXISTS (
              SELECT 1
              FROM sequencecourse sc
              JOIN sequenceterm st ON st.sequencetermid = sc.sequencetermid
              WHERE sc.subject = os.subject
                AND sc.catalog = os.catalog
        """
        if planid:
            query += " AND st.planid = :planid"
            params["planid"] = planid
        if termid:
            query += " AND sc.sequencetermid = :termid"
            params["termid"] = termid
        query += ")"

    row = db.session.execute(db.text(query), params).mappings().first()

    if row and row["min_date"]:
        return jsonify({
            "startDate": str(row["min_date"]),
            "endDate": str(row["max_date"]) if row["max_date"] else None,
        })
    return jsonify({"startDate": None, "endDate": None})


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

    def label_from_ymd(ymd: Optional[str]) -> str:
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

    # Apply term filter to other dropdowns.
    # When a semester is selected, auto-detect the correct termcode from season.
    term_where = ""
    if termid:
        season = db.session.execute(
            db.text("SELECT season FROM sequenceterm WHERE sequencetermid = :tid"),
            {"tid": termid},
        ).scalar()

        if season in ("fall", "winter", "summer"):
            month_ranges = {"fall": (9, 12), "winter": (1, 4), "summer": (5, 8)}
            m1, m2 = month_ranges[season]
            latest_term = db.session.execute(
                db.text("""
                    SELECT MAX(sch.termcode)
                    FROM scheduleterm sch
                    JOIN sequencecourse sc
                      ON sc.subject = sch.subject AND sc.catalog = sch.catalog
                    WHERE sc.sequencetermid = :tid
                      AND EXTRACT(MONTH FROM sch.classstartdate) BETWEEN :m1 AND :m2
                      AND sch.classstartdate > '2000-01-01'
                """),
                {"tid": termid, "m1": m1, "m2": m2},
            ).scalar()
            if latest_term:
                term_where = " AND sch.termcode = :term"
                params["term"] = latest_term
    elif term:
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


# ---------------------------------------------------------------------------
# Import Data page + Lab Rooms CSV import
# ---------------------------------------------------------------------------

@app.get("/import")
def import_data():
    return render_template(ROUTE_TEMPLATES["/import"])


def _parse_lab_rooms_csv(file_stream):
    """Parse uploaded CSV and return list of row dicts."""
    text = file_stream.read().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if header is None:
        return []
    rows = []
    for line in reader:
        if len(line) < 7:
            continue
        rows.append({
            "course_code": line[0].strip(),
            "title": line[1].strip(),
            "room": line[2].strip(),
            "capacity": line[3].strip(),
            "capacity_max": line[4].strip(),
            "responsible": line[5].strip(),
            "comments": line[6].strip(),
        })
    return rows


@app.post("/api/import/labrooms")
def api_import_labrooms():
    f = request.files.get("file")
    if not f or not f.filename.endswith(".csv"):
        return jsonify({"status": "error", "message": "Please upload a .csv file."}), 400

    rows = _parse_lab_rooms_csv(f.stream)
    if not rows:
        return jsonify({"status": "error", "message": "CSV is empty or has no valid rows."}), 400

    rooms_upserted = 0
    assignments_upserted = 0
    skipped = 0

    try:
        for row in rows:
            room_str = row["room"]
            course_code = row["course_code"]

            # Parse room: "H-859" → building=H, room=859; "AITS" → building=AITS, room=AITS
            if "-" in room_str:
                parts = room_str.split("-", 1)
                building = parts[0]
                room_num = parts[1]
            else:
                building = room_str
                room_num = room_str

            # Parse capacity
            try:
                cap = int(row["capacity"])
            except (ValueError, TypeError):
                cap = 0
            try:
                cap_max = int(row["capacity_max"])
            except (ValueError, TypeError):
                cap_max = cap

            # Ensure building exists (FK requirement)
            db.session.execute(
                db.text("""
                    INSERT INTO building (campus, building)
                    VALUES ('SGW', :building)
                    ON CONFLICT (campus, building) DO NOTHING;
                """),
                {"building": building},
            )

            # Upsert lab room
            result = db.session.execute(
                db.text("""
                    INSERT INTO labrooms (campus, building, room, capacity, capacitymax)
                    VALUES ('SGW', :building, :room, :capacity, :capacitymax)
                    ON CONFLICT (campus, building, room)
                    DO UPDATE SET capacity = EXCLUDED.capacity,
                                  capacitymax = EXCLUDED.capacitymax
                    RETURNING labroomid;
                """),
                {
                    "building": building,
                    "room": room_num,
                    "capacity": cap,
                    "capacitymax": cap_max,
                },
            )
            lab_row = result.mappings().first()
            if lab_row:
                rooms_upserted += 1
                labroomid = lab_row["labroomid"]
            else:
                skipped += 1
                continue

            # Parse course code: "COEN 314" → subject=COEN, catalog=314
            code_parts = course_code.split()
            if len(code_parts) >= 2:
                subject = code_parts[0]
                catalog = code_parts[1]
            else:
                subject = course_code
                catalog = ""

            # Ensure catalog entry exists (FK requirement)
            db.session.execute(
                db.text("""
                    INSERT INTO catalog (id, subject, catalog, title)
                    VALUES (
                        (SELECT COALESCE(MAX(id), 0) + 1 FROM catalog),
                        :subject, :catalog, :title
                    )
                    ON CONFLICT (subject, catalog) DO NOTHING;
                """),
                {"subject": subject, "catalog": catalog, "title": row["title"]},
            )

            # Upsert course-lab assignment
            db.session.execute(
                db.text("""
                    INSERT INTO courselabs (labroomid, subject, catalog, comments)
                    VALUES (:labroomid, :subject, :catalog, :comments)
                    ON CONFLICT (labroomid, catalog, subject)
                    DO UPDATE SET comments = EXCLUDED.comments;
                """),
                {
                    "labroomid": labroomid,
                    "subject": subject,
                    "catalog": catalog,
                    "comments": row["comments"],
                },
            )
            assignments_upserted += 1

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error("Lab room import failed: %s", e)
        return jsonify({"status": "error", "message": "A database error occurred while importing lab rooms."}), 500

    return jsonify({
        "status": "success",
        "rows_processed": len(rows),
        "rooms_upserted": rooms_upserted,
        "assignments_upserted": assignments_upserted,
        "skipped": skipped,
    })

def _parse_catalog_csv(file_stream):
    """Parse uploaded CSV and return list of row dicts."""
    text = file_stream.read().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if header is None:
        return "No header found", []
    rows = []
    for row in reader:
        if len(row) != 6:
            return "Expected 6 columns per row", []
        rows.append({
            "subject": row[0].strip(),
            "catalog": row[1].strip(),
            "title": row[2].strip(),
            "career": row[3].strip(),
            "classunit": row[4].strip(),
            "prerequisites": row[5].strip()
        })
    return "success", rows

@app.post("/api/import/catalog")
def import_catalog():
    f = request.files.get("file")
    if not f or not f.filename.endswith(".csv"):
        return jsonify({"status": "error", "message": "Please upload a .csv file."}), 400

    message, rows = _parse_catalog_csv(f.stream)
    if message != "success":
        return jsonify({"status": "error", "message": message}), 400

    courses_added = 0
    courses_updated = 0
    skipped = 0

    try:
        for row in rows:
            subject = row["subject"]
            catalog = row["catalog"]
            title = row["title"]
            career = row["career"]
            classunit = row["classunit"]
            prerequisites = row["prerequisites"]

            result = db.session.execute(
                db.text(f"""SELECT id FROM catalog WHERE subject = :subject AND catalog = :catalog;"""), 
                        {"subject": subject, "catalog": catalog}).mappings().first()
            
            if result:
                result = db.session.execute(
                    db.text(f"""
                    UPDATE catalog SET title = :title, career = :career, classunit = :classunit, prerequisites = :prerequisites
                    WHERE subject = :subject AND catalog = :catalog;
                    """),
                    {
                        "title": title,
                        "career": career,
                        "classunit": classunit,
                        "prerequisites": prerequisites,
                        "subject": subject,
                        "catalog": catalog
                    }
                )
                courses_updated += 1
            else:
                db.session.execute(
                    db.text(f"""
                        INSERT INTO catalog (id, subject, catalog, title, career, classunit, prerequisites)
                        VALUES (
                            (SELECT COALESCE(MAX(id), 0) + 1 FROM catalog),
                            :subject, :catalog, :title, :career, :classunit, :prerequisites
                        );
                    """),
                    {
                        "subject": subject,
                        "catalog": catalog,
                        "title": title,
                        "career": career,
                        "classunit": classunit,
                        "prerequisites": prerequisites,
                    },
                )
                courses_added += 1
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error("Catalog import failed: %s", e)
        return jsonify({"status": "error", "message": "A database error occurred while importing catalog courses."}), 500
    
    return jsonify({
        "status": "success",
        "rows_processed": len(rows),
        "courses_added": courses_added,
        "courses_updated": courses_updated,
        "skipped": skipped
    })

def _get_course_days(class_day_string):
    if len(class_day_string) != 7:
        return None
    days = []
    for index, char in enumerate(class_day_string):
        if char == '-':
            days.append(False)
        else:
            days.append(True)
    return days

def _parse_schedules_csv(file_stream):
    """Parse uploaded CSV and return list of row dicts."""
    text = file_stream.read().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if header is None:
        return "No header found", []
    rows = []
    i = 1
    for row in reader:
        if len(row) != 19:
            return f"Expected 19 columns per row, row {i} invalid", []
        days = _get_course_days(row[12].strip())
        if days is None:
            return f"Invalid class day string in row {i}", []
        
        section = ""
        if (row[6].strip() != ""):
            section = row[6].strip()
        else:
            section = row[7].strip()

        # 1st, 3rd, 4th digit of year + (1 (summer), 2(fall), 3(fall/winter), 4(winter), 5(spring, CCCE), 6(winter, CCCE))
        if (row[2].strip() == "Winter"):
            year = int(row[0].strip()) - 1
            year_str = str(year)
            session = '13W'
            termcode = year_str[0] + year_str[2] + year_str[3] + '4'
        elif (row[2].strip() == "Summer"):
            if (row[6].strip() == 'COEN390' or row[6].strip() == 'ELEC390'):
                year = int(row[0].strip())
                year_str = str(year)
                session = '13W'
                termcode = year_str[0] + year_str[2] + year_str[3] + '1'
            else:
                year = int(row[0].strip())
                year_str = str(year)
                if (int(row[16].strip().split('-')[1]) <= 6):
                    session = '6H1'
                else:
                    session = '6H2'
                termcode = year_str[0] + year_str[2] + year_str[3] + '1'
        else: # Fall
            year = int(row[0].strip())
            year_str = str(year)
            session = '13W'
            termcode = year_str[0] + year_str[2] + year_str[3] + '2'

        career = 'UGRD' if row[15].strip() == 'U' else 'GRAD'

        department = ""
        faculty = ""
        facultydescription = ""
        if (row[3].strip() == "ECE"):
            department = 'ELECCOEN'
            faculty = 'ENCS'
            facultydescription = 'Gina Cody School of Engineering & Computer Science'

        rows.append({
            "subject": row[5].strip()[:4],
            "catalog": row[5].strip()[4:],
            "section": section,
            "componentcode": row[11].strip().split("-")[0],
            "termcode": termcode,
            "classnumber": '',
            "session": session,
            "buildingcode": '',
            "room": '',
            "instructionmodecode": '',
            "locationcode": '',
            "currentwaitlisttotal": '',
            "waitlistcapacity": '',
            "enrollmentcapacity": row[9].strip(),
            "currentenrollment": '',
            "departmentcode": department,
            "facultycode": faculty,
            "classstarttime": row[13].strip(),
            "classendtime": row[14].strip(),
            "classstartdate": row[17].strip(),
            "classenddate": row[18].strip(),
            "mondays": days[0],
            "tuesdays": days[1],
            "wednesdays": days[2],
            "thursdays": days[3],
            "fridays": days[4],
            "saturdays": days[5],
            "sundays": days[6],
            "facultydescription": facultydescription,
            "career": career,
            "meetingpatternnumber": '1',
            "cid": ''
        })
        i += 1
    return "success", rows

@app.post("/api/import/schedules")
def import_schedules():
    f = request.files.get("file")
    if not f or not f.filename.endswith(".csv"):
        return jsonify({"status": "error", "message": "Please upload a .csv file."}), 400

    message, rows = _parse_schedules_csv(f.stream)
    if message != "success":
        return jsonify({"status": "error", "message": message}), 400

    schedules_upserted = 0
    sections_added = 0
    skipped = 0

    try:
        for row in rows:
            # Complete schedule data
            result = db.session.execute(
                db.text(f"""
                        SELECT classnumber FROM section WHERE 
                        subject = :subject AND catalog = :catalog AND 
                        section = :section AND term = :term              
                """),
                {
                    "subject": row["subject"],
                    "catalog": row["catalog"],
                    "section": row["section"],
                    "term": row["termcode"]
                }
            ).mappings().first()
            if result:
                row["classnumber"] = result["classnumber"]
            else:
                result = db.session.execute(
                    db.text(f"""
                            INSERT INTO section (term, session, subject, catalog, component, classnumber, classenrollcapacity, section)
                            VALUES (:term, :session, :subject, :catalog, :componentcode, 
                            (SELECT COALESCE(MAX(classnumber), 0) + 1 FROM section), :enrollmentcapacity, :section)
                            RETURNING classnumber;
                    """),
                    {
                        "term": row["termcode"],
                        "session": row["session"],
                        "subject": row["subject"],
                        "catalog": row["catalog"],
                        "componentcode": row["componentcode"],
                        "enrollmentcapacity": row["enrollmentcapacity"],
                        "section": row["section"]
                    }
                ).mappings().first()
                row["classnumber"] = result["classnumber"]
                sections_added += 1
            
            # Upsert schedule
            db.session.execute(
                db.text(f"""
                    INSERT INTO scheduleterm (subject, "catalog", "section", componentcode, termcode,
                    classnumber, "session", enrollmentcapacity, departmentcode, facultycode,
                    classstarttime, classendtime, classstartdate, classenddate,
                    mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays,
                    facultydescription, career, meetingpatternnumber)
                    VALUES (:subject, :catalog, :section, :componentcode, :termcode,
                    :classnumber, :session, :enrollmentcapacity, :departmentcode, :facultycode,
                    :classstarttime, :classendtime, :classstartdate, :classenddate,
                    :mondays, :tuesdays, :wednesdays, :thursdays, :fridays, :saturdays, :sundays,
                    :facultydescription, :career, '1')
                    ON CONFLICT (subject, "catalog", section, termcode, classnumber, meetingpatternnumber)
                    DO UPDATE SET componentcode = EXCLUDED.componentcode, session = EXCLUDED.session, enrollmentcapacity = EXCLUDED.enrollmentcapacity, departmentcode = EXCLUDED.departmentcode, facultycode = EXCLUDED.facultycode,
                    classstarttime = EXCLUDED.classstarttime, classendtime = EXCLUDED.classendtime, classstartdate = EXCLUDED.classstartdate, classenddate = EXCLUDED.classenddate,
                    mondays = EXCLUDED.mondays, tuesdays = EXCLUDED.tuesdays, wednesdays = EXCLUDED.wednesdays, thursdays = EXCLUDED.thursdays, fridays = EXCLUDED.fridays, saturdays = EXCLUDED.saturdays, sundays = EXCLUDED.sundays,
                    facultydescription = EXCLUDED.facultydescription, career = EXCLUDED.career;
                """),
                {
                    "subject": row["subject"],
                    "catalog": row["catalog"],
                    "section": row["section"],
                    "componentcode": row["componentcode"],
                    "termcode": row["termcode"],
                    "classnumber": row["classnumber"],
                    "session": row["session"],
                    "enrollmentcapacity": row["enrollmentcapacity"],
                    "departmentcode": row["departmentcode"],
                    "facultycode": row["facultycode"],
                    "classstarttime": row["classstarttime"],
                    "classendtime": row["classendtime"],
                    "classstartdate": row["classstartdate"],
                    "classenddate": row["classenddate"],
                    "mondays": row["mondays"],
                    "tuesdays": row["tuesdays"],
                    "wednesdays": row["wednesdays"],
                    "thursdays": row["thursdays"],
                    "fridays": row["fridays"],
                    "saturdays": row["saturdays"],
                    "sundays": row["sundays"],
                    "facultydescription": row["facultydescription"],
                    "career": row["career"]
                }
            )
            schedules_upserted += 1
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error("Schedule import failed: %s", e)
        return jsonify({"status": "error", "message": "A database error occurred while importing schedules."}), 500

    return jsonify({
        "status": "success",
        "rows_processed": len(rows),
        "schedules_upserted": schedules_upserted,
        "sections_added": sections_added,
        "skipped": skipped
    })

def _parse_sequence_plan_csv(file_stream):
    """Parse uploaded CSV and return list of row dicts."""
    text = file_stream.read().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if header is None:
        return "No header found", [], [], []
    elif header[0].strip() != "Name":
        return "Expected 'Name' in first column of header", [], [], []

    plan = {}
    terms = []
    courses = []
    i = 1
    mode = 0 # 0 = expect plan header, 1 = sequence terms, 2 = sequence courses
    for row in reader:
        if len(row) < 5:
            return f"Expected 5 columns per row, row {i} invalid", [], [], []
        if (row[1].strip() == "YearNumber"):
            mode = 1 # SequenceTerm
            continue
        elif (row[1].strip() == "Subject"):
            mode = 2 # SequenceCourse
            continue
        if mode == 0:
            plan["planname"] = row[0].strip()
            plan["program"] = row[1].strip()
            plan["entryterm"] = row[2].strip()
            plan["option"] = row[3].strip()
            plan["durationyears"] = row[4].strip()
        elif mode == 1:
            terms.append({
                "termnumber": row[0].strip(),
                "yearnumber": row[1].strip(),
                "season": row[2].strip(),
                "workterm": row[3].strip(),
                "notes": row[4].strip()
            })
        elif mode == 2:
            courses.append({
                "termnumber": row[0].strip(),
                "subject": row[1].strip(),
                "catalog": row[2].strip(),
                "label": row[4].strip()
            })
        
        i += 1
    
    return "success", plan, terms, courses

@app.post("/api/import/sequenceplans")
def import_sequence_plans():
    f = request.files.get("file")
    if not f or not f.filename.endswith(".csv"):
        return jsonify({"status": "error", "message": "Please upload a .csv file."}), 400

    message, plan, terms, courses = _parse_sequence_plan_csv(f.stream)
    if message != "success":
        return jsonify({"status": "error", "message": message}), 400
    
    try:
        # Check if plan name already exists
        result = db.session.execute(
            db.text("""
                SELECT planid FROM sequenceplan WHERE planname = :planname;
            """),
            {"planname": plan["planname"]}
        ).mappings().first()
        if result:
            return jsonify({"status": "error", "message": "A sequence plan with this name already exists."}), 400

        # Insert sequence plan and get generated planid
        result = db.session.execute(
            db.text("""
                INSERT INTO sequenceplan (planname, program, entryterm, option, durationyears)
                VALUES (:planname, :program, :entryterm, :option, :durationyears)
                RETURNING planid;
            """),
            {
                "planname": plan["planname"],
                "program": plan["program"],
                "entryterm": plan["entryterm"],
                "option": plan["option"],
                "durationyears": plan["durationyears"]
            }
        ).mappings().first()
        if not result:
            db.session.rollback()
            return jsonify({"status": "error", "message": "Failed to create sequence plan."}), 500
        
        planid = result["planid"]

        for term in terms:
            result = db.session.execute(
                db.text("""
                    INSERT INTO sequenceterm (planid, yearnumber, season, workterm, notes)
                    VALUES (:planid, :yearnumber, :season, :workterm, :notes)
                    returning sequencetermid;
                """),
                {
                    "planid": planid,
                    "yearnumber": term["yearnumber"],
                    "season": term["season"],
                    "workterm": term["workterm"],
                    "notes": term["notes"]
                }
            ).mappings().first()
            if not result:
                db.session.rollback()
                return jsonify({"status": "error", "message": "Failed to create sequence term."}), 500
            
            term["sequencetermid"] = result["sequencetermid"]
        
        for course in courses:
            # Find matching sequencetermid based on termnumber
            for term in terms:
                if term["termnumber"] == course["termnumber"]:
                    course["sequencetermid"] = term["sequencetermid"]
                    break
            
            if "sequencetermid" not in course:
                db.session.rollback()
                return jsonify({"status": "error", "message": f"No matching sequence term for course {course['subject']} {course['catalog']}."}), 400
            
            db.session.execute(
                db.text("""
                    INSERT INTO sequencecourse (sequencetermid, subject, catalog, label)
                    VALUES (:sequencetermid, :subject, :catalog, :label)
                """),
                {
                    "sequencetermid": course["sequencetermid"],
                    "subject": course["subject"],
                    "catalog": course["catalog"],
                    "label": course["label"]
                }
            )

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        app.logger.error("Sequence plan import failed: %s", e)
        return jsonify({"status": "error", "message": "A database error occurred while importing sequence plan."}), 500
    
    return jsonify({
        "status": "success",
        "planid": planid,
        "sequenceterms_added": len(terms),
        "sequencecourses_added": len(courses)
    })

def _parse_student_schedules_csv(file_stream):
    """Parse uploaded CSV and return list of row dicts."""
    text = file_stream.read().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if header is None:
        return "No header found", [], [], []
    elif header[0].strip() != "StudyName":
        return "Expected 'StudyName' in first column of header", [], [], []
    
    study = {}
    schedules = []
    classes = []
    i = 1
    mode = 0 # 0 = expect study header, 1 = schedules, 2 = classes
    for row in reader:
        if (len(row) != 5):
            return f"Expected 5 columns per row, row {i} invalid", [], [], []
        if (row[1].strip() == "Notes"):
            mode = 1 # Schedules
            continue
        elif (row[1].strip() == "Subject"):
            mode = 2 # Classes
            continue

        if mode == 0:
            study["studyname"] = row[0].strip()
            study["owner"] = row[1].strip()
        elif mode == 1:
            schedules.append({
                "schedulename": row[0].strip(),
                "notes": row[1].strip()
            })
        elif mode == 2:
            classes.append({
                "schedulename": row[0].strip(),
                "subject": row[1].strip(),
                "catalog": row[2].strip(),
                "section": row[3].strip(),
                "termnumber": row[4].strip()
            })
        i += 1
    
    return "success", study, schedules, classes


@app.post("/api/import/student")
def import_student_schedules():
    f = request.files.get("file")
    if not f or not f.filename.endswith(".csv"):
        return jsonify({"status": "error", "message": "Please upload a .csv file."}), 400

    message, study, schedules, classes = _parse_student_schedules_csv(f.stream)
    if message != "success":
        return jsonify({"status": "error", "message": message}), 400
    
    created_or_updated = "Created"
    studyid = None
    schedules_added = 0
    classes_added = 0

    try:
        # Create or reset study records
        result = db.session.execute(
            db.text("""
                    SELECT studyid from studentschedulestudy
                    WHERE studyname = :studyname AND owner = :owner;
            """),
            {
                "studyname": study["studyname"],
                "owner": study["owner"]
            }
        ).mappings().first()

        if result:
            studyid = result["studyid"]
            created_or_updated = "Updated"
            db.session.execute(
                db.text("""
                    DELETE FROM studentschedule
                    WHERE studyid = :studyid;
                """),
                {"studyid": studyid}
            )
        else:
            result = db.session.execute(
                db.text("""
                    INSERT INTO studentschedulestudy (studyname, owner)
                    VALUES (:studyname, :owner)
                    RETURNING studyid;
                """),
                {
                    "studyname": study["studyname"],
                    "owner": study["owner"]
                }
            ).mappings().first()

            if not result:
                db.session.rollback()
                return jsonify({"status": "error", "message": "Failed to create student schedule study."}), 500
            
            studyid = result["studyid"]

        for schedule in schedules:
            result = db.session.execute(
                db.text("""
                    INSERT INTO studentschedule (studyid, schedulename, notes)
                    VALUES (:studyid, :schedulename, :notes)
                    RETURNING studentscheduleid;
                """),
                {
                    "studyid": studyid,
                    "schedulename": schedule["schedulename"],
                    "notes": schedule["notes"]
                }
            ).mappings().first()

            if not result:
                db.session.rollback()
                return jsonify({"status": "error", "message": "Failed to create student schedule."}), 500
            
            schedule["studentscheduleid"] = result["studentscheduleid"]
            schedules_added += 1

        for course in classes:
            # Find matching studentscheduleid based on schedulename
            for schedule in schedules:
                if schedule["schedulename"] == course["schedulename"]:
                    course["studentscheduleid"] = schedule["studentscheduleid"]
                    break
            
            if "studentscheduleid" not in course:
                db.session.rollback()
                return jsonify({"status": "error", "message": f"No matching student schedule for course {course['subject']} {course['catalog']}."}), 400
            
            result = db.session.execute(
                db.text("""
                    SELECT classnumber, cid FROM scheduleterm
                    WHERE subject = :subject AND catalog = :catalog 
                    AND section = :section AND termcode = :termcode
                    ORDER BY meetingpatternnumber ASC LIMIT 1;
                """),
                {
                    "subject": course["subject"],
                    "catalog": course["catalog"],
                    "section": course["section"],
                    "termcode": course["termnumber"]
                }
            ).mappings().first()

            if not result:
                db.session.rollback()
                return jsonify({"status": "error", "message": f"No matching course found for {course['subject']} {course['catalog']} {course['section']} in term {course['termnumber']}."}), 400

            classnumber = result["classnumber"]
            cid = result["cid"]

            db.session.execute(
                db.text("""
                    INSERT INTO studentscheduleclass (studentscheduleid, classnumber, term, section, cid)
                    VALUES (:studentscheduleid, :classnumber, :termcode, :section, :cid);
                """),
                {
                    "studentscheduleid": course["studentscheduleid"],
                    "classnumber": classnumber,
                    "termcode": course["termnumber"],
                    "section": course["section"],
                    "cid": cid
                }
            )

            classes_added += 1

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        app.logger.error("Student schedule import failed: %s", e)
        return jsonify({"status": "error", "message": "A database error occurred while importing student schedule."}), 500
    
    return jsonify({
        "status": "success",
        "studyid": studyid,
        "created_or_updated": created_or_updated,
        "schedules_added": schedules_added,
        "classes_added": classes_added
    })

def _parse_buildings_csv(file_stream):
    """Parse uploaded CSV and return list of row dicts."""
    text = file_stream.read().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if header is None:
        return "No header found", []
    elif header[0].strip() != "Campus":
        return "Expected 'Campus' in first column of header", []
    
    rows = []
    i = 1
    for line in reader:
        if len(line) != 6:
            return f"Expected 6 columns per row, row {i} invalid", []
        
        if (line[0].strip() != "SGW" and line[0].strip() != "LOY"):
            return f"Only SGW and LOY campus are supported, row {i} invalid", []

        rows.append({
            "campus": line[0].strip(),
            "building": line[1].strip(),
            "buildingname": line[2].strip(),
            "address": line[3].strip(),
            "latitude": line[4].strip(),
            "longitude": line[5].strip()
        })

    return "success", rows

@app.post("/api/import/buildings")
def import_buildings():
    f = request.files.get("file")
    if not f or not f.filename.endswith(".csv"):
        return jsonify({"status": "error", "message": "Please upload a .csv file."}), 400

    message, buildings = _parse_buildings_csv(f.stream)
    if message != "success":
        return jsonify({"status": "error", "message": message}), 400
    
    buildings_upserted = 0
    try:
        for building in buildings:
            db.session.execute(
                db.text("""
                    INSERT INTO building (campus, building, buildingname, address, latitude, longitude)
                    VALUES (:campus, :building, :buildingname, :address, :latitude, :longitude)
                    ON CONFLICT (campus, building) DO UPDATE SET
                        buildingname = EXCLUDED.buildingname,
                        address = EXCLUDED.address,
                        latitude = EXCLUDED.latitude,
                        longitude = EXCLUDED.longitude;
                """),
                {
                    "campus": building["campus"],
                    "building": building["building"],
                    "buildingname": building["buildingname"],
                    "address": building["address"],
                    "latitude": building["latitude"],
                    "longitude": building["longitude"]
                }
            )
            buildings_upserted += 1

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        app.logger.error("Buildings import failed: %s", e)
        return jsonify({"status": "error", "message": "A database error occurred while importing buildings."}), 500
    
    return jsonify({
        "status": "success",
        "buildings_upserted": buildings_upserted
    })

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
