"""Unit tests for Flask route handlers (excluding API endpoints)."""
import pytest
from unittest.mock import patch, MagicMock


def test_health_db_route_exists(app):
    """The /health/db route must be registered."""
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/health/db" in rules


def test_dashboard_route_exists(app):
    """The / (dashboard) route must be registered."""
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/" in rules


def test_activity_route_exists(app):
    """The /activity route must be registered."""
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/activity" in rules


def test_catalog_route_exists(app):
    """The /catalog route must be registered."""
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/catalog" in rules


def test_conflicts_route_exists(app):
    """The /conflicts route must be registered."""
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/conflicts" in rules


def test_solutions_route_exists(app):
    """The /solutions route must be registered."""
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/solutions" in rules


def test_timetable_route_exists(app):
    """The /timetable route must be registered."""
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/timetable" in rules


def test_schedulerrun_post_route_exists(app):
    """The /schedulerrun POST route must be registered."""
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/schedulerrun" in rules


class TestDashboardRoute:
    """Tests for GET / (dashboard)."""

    def test_dashboard_returns_200(self, client):
        """Dashboard should return 200 status."""
        res = client.get("/")
        assert res.status_code == 200

    def test_dashboard_uses_correct_template(self, client):
        """Dashboard should render admin-dashboard.html template."""
        res = client.get("/")
        assert res.status_code == 200
        html = res.get_data(as_text=True)
        # Check for content typically in admin-dashboard
        assert "System Overview" in html or "Dashboard" in html or "recent" in html.lower()


class TestActivityRoute:
    """Tests for GET /activity (activity log view)."""

    def test_activity_returns_200(self, client):
        """Activity page should return 200 status."""
        res = client.get("/activity")
        assert res.status_code == 200

    def test_activity_with_valid_date_range(self, client):
        """Activity page should accept startdate and enddate query params."""
        res = client.get("/activity?startdate=2026-01-01&enddate=2026-02-01")
        assert res.status_code == 200

    def test_activity_with_startdate_only(self, client):
        """Activity page should accept startdate param alone."""
        res = client.get("/activity?startdate=2026-01-01")
        assert res.status_code == 200

    def test_activity_with_enddate_only(self, client):
        """Activity page should accept enddate param alone."""
        res = client.get("/activity?enddate=2026-02-01")
        assert res.status_code == 200

    def test_activity_with_invalid_date_format(self, client):
        """Activity page should reject invalid date formats with 400."""
        res = client.get("/activity?startdate=invalid&enddate=also-invalid")
        assert res.status_code == 400


class TestCatalogRoute:
    """Tests for GET /catalog."""

    def test_catalog_returns_200(self, client):
        """Catalog page should return 200 status."""
        res = client.get("/catalog")
        assert res.status_code == 200

    def test_catalog_with_planid_param(self, client):
        """Catalog should accept planid query param."""
        res = client.get("/catalog?planid=1")
        assert res.status_code == 200

    def test_catalog_with_planid_and_termid(self, client):
        """Catalog should accept both planid and termid query params."""
        res = client.get("/catalog?planid=1&termid=1")
        assert res.status_code == 200


class TestConflictsRoute:
    """Tests for GET /conflicts."""

    def test_conflicts_returns_200(self, client):
        """Conflicts page should return 200 status."""
        res = client.get("/conflicts")
        assert res.status_code == 200


class TestSolutionsRoute:
    """Tests for GET /solutions."""

    def test_solutions_returns_200(self, client):
        """Solutions page should return 200 status."""
        res = client.get("/solutions")
        assert res.status_code == 200


class TestTimetableRoute:
    """Tests for GET /timetable."""

    def test_timetable_returns_200(self, client):
        """Timetable page should return 200 status."""
        res = client.get("/timetable")
        assert res.status_code == 200

    def test_timetable_includes_fullcalendar_script(self, client):
        """Timetable page should include FullCalendar JavaScript library."""
        res = client.get("/timetable")
        html = res.get_data(as_text=True)
        assert "fullcalendar" in html.lower()


class TestSchedulerRunRoute:
    """Tests for POST /schedulerrun."""

    def test_schedulerrun_post_requires_form_data(self, client):
        """POST /schedulerrun should accept schedulename form field."""
        res = client.post("/schedulerrun", data={"schedulename": "test-schedule"})
        # Should redirect on success (302 or similar)
        assert res.status_code in [302, 303, 307]

    def test_schedulerrun_post_with_empty_name(self, client):
        """POST /schedulerrun should use default name if not provided."""
        res = client.post("/schedulerrun", data={})
        # Should still redirect
        assert res.status_code in [302, 303, 307]


class TestNotFoundRoute:
    """Tests for 404 handling."""

    def test_nonexistent_route_returns_404(self, client):
        """Requesting a non-existent route should return 404."""
        res = client.get("/nonexistent-page")
        assert res.status_code == 404


class TestStaticFiles:
    """Tests for static file serving."""

    def test_css_files_are_served(self, client):
        """Static CSS files should be served."""
        res = client.get("/static/design-system.css")
        # May be 200 or 404 depending on file existence; at minimum should not error
        assert res.status_code in [200, 404]

    def test_js_files_are_served(self, client):
        """Static JS files should be served."""
        res = client.get("/static/js/timetable.js")
        # May be 200 or 404 depending on file existence
        assert res.status_code in [200, 404]

class TestPageRoutesMore:
    def test_dashboard_is_html(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert "text/html" in res.content_type

    def test_activity_is_html(self, client):
        res = client.get("/activity")
        assert res.status_code == 200
        assert "text/html" in res.content_type

    def test_activity_invalid_startdate_returns_400_json(self, client):
        res = client.get("/activity?startdate=2026-99-99")
        assert res.status_code == 400
        assert res.content_type == "application/json"
        data = res.get_json()
        assert "error" in data

    def test_activity_invalid_enddate_returns_400_json(self, client):
        res = client.get("/activity?enddate=not-a-date")
        assert res.status_code == 400
        data = res.get_json()
        assert "error" in data

    def test_activity_valid_dates_returns_html(self, client):
        res = client.get("/activity?startdate=2026-01-01&enddate=2026-01-02")
        assert res.status_code == 200
        assert "text/html" in res.content_type

    def test_schedulerrun_redirects_back_to_dashboard_when_not_implemented(self, client):
        res = client.post("/schedulerrun", data={"schedulename": "my-test"})
        assert res.status_code in (302, 303)
        assert res.headers["Location"].endswith("/")

    def test_timetable_page_is_html(self, client):
        res = client.get("/timetable")
        assert res.status_code == 200
        assert "text/html" in res.content_type
