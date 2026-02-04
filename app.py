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


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
