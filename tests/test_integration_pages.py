import pytest
from pathlib import Path

pytestmark = pytest.mark.integration

TEMPLATES = [
    ("/", "admin-dashboard.html"),
    ("/schedule", "schedule-display.html"),
    ("/conflicts", "conflicts-list.html"),
    ("/solutions", "proposed-solutions.html"),
]

def _template_exists(template_name: str) -> bool:
    templates_dir = Path(__file__).resolve().parents[1] / "templates"
    return (templates_dir / template_name).exists()

@pytest.mark.parametrize("path,template_name", TEMPLATES)
def test_pages_return_200_if_template_exists(client, path, template_name):
    if not _template_exists(template_name):
        pytest.skip(f"Template not present yet: {template_name}")

    res = client.get(path)
    assert res.status_code == 200


def test_dashboard_contains_expected_text(client):
    res = client.get("/")
    assert res.status_code == 200

    html = res.get_data(as_text=True)
    assert "System Overview" in html
    assert "Scheduler Status" in html
    assert "Recent Activity" in html
