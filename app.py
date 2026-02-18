import csv
import io
import os

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

ROUTE_TEMPLATES = {
    "/": "admin-dashboard.html",
    "/schedule": "schedule-display.html",
    "/conflicts": "conflicts-list.html",
    "/solutions": "proposed-solutions.html",
    "/import": "import-data.html",
}

# ---------------------------------------------------------------------------
# DB connection helper
# ---------------------------------------------------------------------------

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 9999)),
    "database": os.environ.get("DB_NAME", "uvo490_3"),
    "user": os.environ.get("DB_USER", "uvo490_3"),
    "password": os.environ.get("DB_PASSWORD", "coolbird18"),
}


def get_db_connection():
    """Return a psycopg2 connection using DB_CONFIG."""
    import psycopg2
    return psycopg2.connect(**DB_CONFIG)


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@app.get("/")
def dashboard():
    return render_template(ROUTE_TEMPLATES["/"])


@app.get("/schedule")
def schedule():
    return render_template(ROUTE_TEMPLATES["/schedule"])


@app.get("/conflicts")
def conflicts():
    return render_template(ROUTE_TEMPLATES["/conflicts"])


@app.get("/solutions")
def solutions():
    return render_template(ROUTE_TEMPLATES["/solutions"])


@app.get("/import")
def import_data():
    return render_template(ROUTE_TEMPLATES["/import"])


# ---------------------------------------------------------------------------
# Lab rooms CSV import
# ---------------------------------------------------------------------------

def _parse_lab_rooms_csv(file_stream):
    """Parse uploaded CSV and return list of row dicts.

    Expected columns: Course Code, Title, Room, Capacity, Cap_MAX,
    Responsible, Comments
    """
    text = file_stream.read().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)  # skip header
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


def _upsert_lab_room(cursor, row):
    """Upsert a single lab room into the labrooms table."""
    if row["room"] == "AITS":
        building, room = "H", "AITS"
        cap_max = 100
    else:
        parts = row["room"].split("-", 1)
        if len(parts) != 2:
            return False
        building, room = parts
        try:
            cap_max = int(row["capacity_max"])
        except (ValueError, TypeError):
            cap_max = 0

    try:
        capacity = int(row["capacity"])
    except (ValueError, TypeError):
        capacity = 0

    cursor.execute(
        "INSERT INTO labrooms (campus, building, room, capacity, capacitymax) "
        "VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (campus, building, room) DO UPDATE "
        "SET capacity = EXCLUDED.capacity, capacitymax = EXCLUDED.capacitymax",
        ("SGW", building, room, capacity, cap_max),
    )
    return True


def _upsert_course_lab(cursor, row):
    """Upsert a single course-lab assignment into the courselabs table."""
    parts = row["course_code"].split(" ", 1)
    if len(parts) != 2:
        return False
    subject, catalog = parts

    if row["room"] == "AITS":
        building, room = "H", "AITS"
    else:
        room_parts = row["room"].split("-", 1)
        if len(room_parts) != 2:
            return False
        building, room = room_parts

    cursor.execute(
        "INSERT INTO courselabs (labroomid, subject, catalog, comments) "
        "VALUES ("
        "  (SELECT labroomid FROM labrooms "
        "   WHERE campus = %s AND building = %s AND room = %s), "
        "  %s, %s, %s"
        ") "
        "ON CONFLICT (labroomid, subject, catalog) DO UPDATE "
        "SET comments = EXCLUDED.comments",
        ("SGW", building, room, subject, catalog, row["comments"]),
    )
    return True


@app.post("/api/import/labrooms")
def api_import_labrooms():
    """Accept a CSV upload and import lab rooms + course assignments."""
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded."}), 400

    file = request.files["file"]
    if not file.filename or not file.filename.endswith(".csv"):
        return jsonify({"status": "error", "message": "Please upload a .csv file."}), 400

    rows = _parse_lab_rooms_csv(file.stream)
    if not rows:
        return jsonify({"status": "error", "message": "CSV is empty or has invalid format."}), 400

    try:
        conn = get_db_connection()
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Could not connect to database: {e}",
        }), 500

    rooms_ok = 0
    assignments_ok = 0
    skipped = 0

    try:
        with conn.cursor() as cur:
            for row in rows:
                try:
                    if _upsert_lab_room(cur, row):
                        conn.commit()
                        rooms_ok += 1
                    else:
                        skipped += 1
                        conn.rollback()
                        continue

                    if _upsert_course_lab(cur, row):
                        conn.commit()
                        assignments_ok += 1
                    else:
                        skipped += 1
                        conn.rollback()
                except Exception:
                    conn.rollback()
                    skipped += 1
    finally:
        conn.close()

    return jsonify({
        "status": "success",
        "rows_processed": len(rows),
        "rooms_upserted": rooms_ok,
        "assignments_upserted": assignments_ok,
        "skipped": skipped,
    })
