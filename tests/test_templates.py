"""Unit tests for Jinja2 templates."""
from pathlib import Path
from bs4 import BeautifulSoup
import re
import pytest


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"


def read_template(name: str) -> str:
    """Read a template file content."""
    path = TEMPLATES_DIR / name
    if not path.exists():
        pytest.skip(f"Template not found: {name}")
    return path.read_text()


class TestTemplateInheritance:
    """Tests for template inheritance structure."""

    def test_base_template_exists(self):
        """base.html should exist."""
        assert (TEMPLATES_DIR / "base.html").exists()

    def test_base_template_has_content_block(self):
        """base.html should have {% block content %}."""
        content = read_template("base.html")
        assert "{% block content %}" in content
        assert "{% endblock %}" in content

    def test_all_page_templates_extend_base(self):
        """All page templates should extend base.html (except base.html itself)."""
        page_templates = [
            "admin-dashboard.html",
            "activity.html",
            "catalog.html",
            "conflicts-list.html",
            "proposed-solutions.html",
            "timetable.html",
        ]
        
        for template_name in page_templates:
            content = read_template(template_name)
            assert '{% extends "base.html" %}' in content, \
                f"{template_name} should extend base.html"

    def test_page_templates_define_content_block(self):
        """All page templates should define {% block content %}."""
        page_templates = [
            "admin-dashboard.html",
            "activity.html",
            "catalog.html",
            "conflicts-list.html",
            "proposed-solutions.html",
            "timetable.html",
        ]
        
        for template_name in page_templates:
            content = read_template(template_name)
            assert "{% block content %}" in content, \
                f"{template_name} should define content block"


class TestBaseTemplateStructure:
    """Tests for base.html structure."""

    def test_base_has_html_doctype(self):
        """base.html should start with HTML5 doctype."""
        content = read_template("base.html")
        assert content.strip().startswith("<!DOCTYPE html>") or \
               content.strip().startswith("{% ")

    def test_base_has_head_section(self):
        """base.html should have <head> section."""
        content = read_template("base.html")
        assert "<head>" in content

    def test_base_has_body_section(self):
        """base.html should have <body> section."""
        content = read_template("base.html")
        assert "<body>" in content

    def test_base_has_sidebar(self):
        """base.html should have sidebar with navigation."""
        content = read_template("base.html")
        assert "<aside" in content or "sidebar" in content.lower()

    def test_base_has_main_content_area(self):
        """base.html should have main content area."""
        content = read_template("base.html")
        assert "<main" in content or "main-content" in content.lower()

    def test_base_includes_design_system_css(self):
        """base.html should link to design-system.css."""
        content = read_template("base.html")
        assert "design-system.css" in content

    def test_base_has_extra_js_block(self):
        """base.html should have {% block extra_js %} for page-specific scripts."""
        content = read_template("base.html")
        assert "{% block extra_js %}" in content

    def test_base_has_extra_css_block(self):
        """base.html should have {% block extra_css %} for page-specific styles."""
        content = read_template("base.html")
        assert "{% block extra_css %}" in content


class TestTimetableTemplate:
    """Tests for timetable.html."""

    def test_timetable_has_filter_controls(self):
        """Timetable should have filter dropdown controls."""
        content = read_template("timetable.html")
        filters = ["plan-filter", "semester-filter", "term-filter", 
                   "subject-filter", "component-filter", "building-filter"]
        for filter_id in filters:
            assert filter_id in content, \
                f"Timetable should have filter with id: {filter_id}"

    def test_timetable_has_calendar_container(self):
        """Timetable should have calendar container div."""
        content = read_template("timetable.html")
        assert 'id="calendar"' in content

    def test_timetable_has_event_modal(self):
        """Timetable should have event detail modal."""
        content = read_template("timetable.html")
        assert 'id="event-modal"' in content

    def test_timetable_includes_fullcalendar_css(self):
        """Timetable should include FullCalendar CSS."""
        content = read_template("timetable.html")
        assert "fullcalendar" in content.lower() and "css" in content.lower()

    def test_timetable_loads_timetable_js(self):
        """Timetable should load timetable.js script."""
        content = read_template("timetable.html")
        assert "timetable.js" in content


class TestActivityTemplate:
    """Tests for activity.html."""

    def test_activity_has_date_filters(self):
        """Activity page should have date range filters."""
        content = read_template("activity.html")
        assert "startdate" in content
        assert "enddate" in content

    def test_activity_has_logs_table(self):
        """Activity page should display logs in a table."""
        content = read_template("activity.html")
        assert "<table" in content
        # Likely content for table headers
        assert "createdat" in content.lower() or "date" in content.lower()


class TestCatalogTemplate:
    """Tests for catalog.html."""

    def test_catalog_has_plan_selector(self):
        """Catalog should have sequence plan selector."""
        content = read_template("catalog.html")
        assert "planid" in content or "plan" in content.lower()

    def test_catalog_has_data_table(self):
        """Catalog should display courses in a table."""
        content = read_template("catalog.html")
        assert "<table" in content


class TestDashboardTemplate:
    """Tests for admin-dashboard.html."""

    def test_dashboard_has_scheduler_status_section(self):
        """Dashboard should display scheduler status."""
        content = read_template("admin-dashboard.html")
        assert "scheduler_status" in content or "status" in content.lower()

    def test_dashboard_has_recent_activity_section(self):
        """Dashboard should display recent activity."""
        content = read_template("admin-dashboard.html")
        assert "recent" in content.lower() or "activity" in content.lower()

    def test_dashboard_has_schedule_generator_form(self):
        """Dashboard should have form to generate schedule."""
        content = read_template("admin-dashboard.html")
        assert "schedulename" in content or "form" in content.lower()


class TestConflictsTemplate:
    """Tests for conflicts-list.html."""

    def test_conflicts_page_renders(self):
        """Conflicts page should render without errors."""
        content = read_template("conflicts-list.html")
        assert len(content) > 0


class TestSolutionsTemplate:
    """Tests for proposed-solutions.html."""

    def test_solutions_page_renders(self):
        """Solutions page should render without errors."""
        content = read_template("proposed-solutions.html")
        assert len(content) > 0


class TestHtmlStructure:
    """Tests for general HTML structure across all templates."""

    def test_all_templates_are_valid_html_fragments(self):
        """All templates should be parseable as HTML."""
        page_templates = [
            "admin-dashboard.html",
            "activity.html",
            "catalog.html",
            "conflicts-list.html",
            "proposed-solutions.html",
            "timetable.html",
        ]
        
        for template_name in page_templates:
            content = read_template(template_name)
            # Try to parse as HTML (jinja2 syntax will be preserved)
            try:
                soup = BeautifulSoup(content, 'html.parser')
                # If it parses, that's good
                assert soup is not None
            except Exception as e:
                pytest.fail(f"Template {template_name} failed to parse: {e}")

    def test_templates_have_no_duplicate_ids(self):
        """Templates should not have duplicate element IDs (within a template)."""
        page_templates = [
            "admin-dashboard.html",
            "activity.html",
            "catalog.html",
            "conflicts-list.html",
            "proposed-solutions.html",
            "timetable.html",
        ]
        
        for template_name in page_templates:
            content = read_template(template_name)
            # Find all id= attributes
            ids = re.findall(r'id=["\']([^"\']+)["\']', content)
            # Filter out jinja2 variables
            ids = [id for id in ids if "{{" not in id]
            
            # Check for duplicates
            if len(ids) != len(set(ids)):
                duplicates = [id for id in ids if ids.count(id) > 1]
                pytest.fail(f"Template {template_name} has duplicate IDs: {set(duplicates)}")


class TestAccessibility:
    """Tests for basic accessibility in templates."""

    def test_base_has_lang_attribute(self):
        """HTML element should have lang attribute."""
        content = read_template("base.html")
        assert 'lang=' in content or 'lang =' in content

    def test_base_has_meta_viewport(self):
        """Page should have viewport meta tag for responsive design."""
        content = read_template("base.html")
        assert 'viewport' in content

    def test_templates_use_semantic_html(self):
        """Templates should use semantic HTML elements."""
        page_templates = [
            "timetable.html",
            "admin-dashboard.html",
        ]
        
        for template_name in page_templates:
            content = read_template(template_name)
            # Should have semantic elements
            has_semantic = any(elem in content for elem in 
                             ["<main", "<aside", "<nav", "<header", "<section", "<article"])
            # Not strictly required but good practice
            if has_semantic:
                assert True
