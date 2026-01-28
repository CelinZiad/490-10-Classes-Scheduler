from flask import Flask, render_template

app = Flask(__name__)

ROUTE_TEMPLATES = {
    "/": "admin-dashboard.html",
    "/schedule": "schedule-display.html",
    "/conflicts": "conflicts-list.html",
    "/solutions": "proposed-solutions.html",
}


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