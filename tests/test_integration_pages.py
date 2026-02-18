from pathlib import Path

import pytest

from app import ROUTE_TEMPLATES

pytestmark = pytest.mark.integration

TEMPLATES = list(ROUTE_TEMPLATES.items())


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


def test_import_page_returns_200(client):
    res = client.get("/import")
    assert res.status_code == 200


def test_import_page_contains_expected_content(client):
    res = client.get("/import")
    html = res.get_data(as_text=True)
    assert "Import Data" in html
    assert "Lab Rooms" in html
    assert "Course Schedules" in html
    assert "Coming Soon" in html
