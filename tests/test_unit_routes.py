from pathlib import Path

from app import ROUTE_TEMPLATES

def test_routes_are_registered(app):
    rules = {r.rule for r in app.url_map.iter_rules()}

    assert set(ROUTE_TEMPLATES).issubset(rules)


def test_templates_exist():
    templates_dir = Path(__file__).resolve().parents[1] / "templates"

    expected = [
        "admin-dashboard.html",
        "schedule-display.html",
        "conflicts-list.html",
        "proposed-solutions.html",
        "catalog.html",
        "timetable.html",
        "base.html",
    ]

    missing = [name for name in ROUTE_TEMPLATES.values() if not (templates_dir / name).exists()]
    assert not missing, f"Missing templates in /templates: {missing}"


def test_timetable_route_exists(app):
    """The /timetable route must be registered."""
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/timetable" in rules


def test_api_events_route_exists(app):
    """The /api/events route must be registered."""
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/api/events" in rules


def test_api_filters_route_exists(app):
    """The /api/filters route must be registered."""
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/api/filters" in rules


def test_api_plan_terms_route_exists(app):
    """The /api/plans/<id>/terms route must be registered."""
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/api/plans/<int:planid>/terms" in rules
