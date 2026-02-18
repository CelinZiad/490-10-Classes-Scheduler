from pathlib import Path

from app import ROUTE_TEMPLATES


EXPECTED_GET_ROUTES = {
    "/",
    "/activity",
    "/catalog",
    "/conflicts",
    "/solutions",
    "/timetable",
    "/import",
    "/api/events",
    "/api/filters",
    "/api/plans/<int:planid>/terms",
    "/api/export-csv",
    "/api/import/labrooms",
}

EXPECTED_POST_ROUTES = {
    "/schedulerrun",
    "/api/import/labrooms",
}


def test_routes_are_registered(app):
    rules = {r.rule for r in app.url_map.iter_rules()}

    missing_get = EXPECTED_GET_ROUTES - rules
    missing_post = EXPECTED_POST_ROUTES - rules

    assert not missing_get, f"Missing GET routes: {sorted(missing_get)}"
    assert not missing_post, f"Missing POST routes: {sorted(missing_post)}"


def test_schedulerrun_is_post(app):
    """Ensure /schedulerrun is registered as POST (not only GET)."""
    rule = next((r for r in app.url_map.iter_rules() if r.rule == "/schedulerrun"), None)
    assert rule is not None, "Route /schedulerrun is not registered"
    assert "POST" in rule.methods, f"/schedulerrun should allow POST, got {rule.methods}"


def test_templates_exist():
    """
    Only check templates for routes that are implemented as pages right now.
    (Don't require schedule-display.html unless /schedule route exists.)
    """
    templates_dir = Path(__file__).resolve().parents[1] / "templates"

    implemented_page_routes = [
        "/",
        "/activity",
        "/catalog",
        "/conflicts",
        "/solutions",
        "/timetable",
        "/import",
    ]

    required_templates = {ROUTE_TEMPLATES[r] for r in implemented_page_routes}
    required_templates.add("base.html")

    missing = [name for name in sorted(required_templates) if not (templates_dir / name).exists()]
    assert not missing, f"Missing templates in /templates: {missing}"


def test_import_route_registered(app):
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/import" in rules
    assert "/api/import/labrooms" in rules
