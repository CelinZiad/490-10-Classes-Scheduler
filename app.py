import os
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

ROUTE_TEMPLATES = {
    "/": "admin-dashboard.html",
    "/schedule": "schedule-display.html",
    "/catalog": "catalog.html",  # ✅ NEW
    "/conflicts": "conflicts-list.html",
    "/solutions": "proposed-solutions.html",
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


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
