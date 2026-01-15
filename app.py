from flask import Flask, render_template

app = Flask(__name__)

@app.get("/")
def dashboard():
    return render_template("admin-dashboard.html")

@app.get("/schedule")
def schedule():
    return render_template("schedule-display.html")

@app.get("/conflicts")
def conflicts():
    return render_template("conflicts-list.html")

@app.get("/solutions")
def solutions():
    return render_template("proposed-solutions.html")

app.run()
