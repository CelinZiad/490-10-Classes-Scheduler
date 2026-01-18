from pathlib import Path


def test_routes_are_registered(app):
    rules = {r.rule for r in app.url_map.iter_rules()}

    assert "/" in rules
    assert "/schedule" in rules
    assert "/conflicts" in rules
    assert "/solutions" in rules


def test_templates_exist():
    templates_dir = Path(__file__).resolve().parents[1] / "templates"

    expected = [
        "admin-dashboard.html",
        "schedule-display.html",
        "conflicts-list.html",
        "proposed-solutions.html",
    ]

    missing = [name for name in expected if not (templates_dir / name).exists()]
    assert not missing, f"Missing templates in /templates: {missing}"
