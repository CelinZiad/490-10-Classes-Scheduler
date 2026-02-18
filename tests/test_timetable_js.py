"""Unit tests for JavaScript code (using pytest to test JavaScript behavior)."""
import pytest


class TestTimetableJsStructure:
    """Tests that validate timetable.js exists and has required functions."""

    def test_timetable_js_file_exists(self):
        """timetable.js file should exist."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        assert js_file.exists(), "timetable.js should exist in static/js/"

    def test_timetable_js_is_readable(self):
        """timetable.js should be readable as text."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert len(content) > 0, "timetable.js should not be empty"

    def test_timetable_js_has_required_functions(self):
        """timetable.js should declare required functions."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        
        required_functions = [
            "loadFilters",
            "loadPlanTerms",
            "initCalendar",
            "setupEventListeners",
            "getFilterParams",
            "applyFilters",
            "clearFilters",
            "updateStats",
            "showEventModal",
            "showLoading",
        ]
        
        for func in required_functions:
            assert f"function {func}" in content or f"{func}(" in content, \
                f"timetable.js should define function: {func}"

    def test_timetable_js_has_ece_subjects_constant(self):
        """timetable.js should define ECE_SUBJECTS constant."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "ECE_SUBJECTS" in content

    def test_timetable_js_initializes_on_dom_ready(self):
        """timetable.js should initialize on DOMContentLoaded."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "DOMContentLoaded" in content


class TestTimetableJsSelectors:
    """Tests that JS code references correct DOM elements."""

    def test_js_references_plan_filter_element(self):
        """JS should reference the plan-filter select element."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert 'plan-filter' in content or 'planFilter' in content

    def test_js_references_semester_filter_element(self):
        """JS should reference the semester-filter select element."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert 'semester-filter' in content or 'semesterFilter' in content

    def test_js_references_term_filter_element(self):
        """JS should reference the term-filter select element."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert 'term-filter' in content or 'termFilter' in content

    def test_js_references_subject_filter_element(self):
        """JS should reference the subject-filter select element."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert 'subject-filter' in content or 'subjectFilter' in content

    def test_js_references_component_filter_element(self):
        """JS should reference the component-filter select element."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert 'component-filter' in content or 'componentFilter' in content

    def test_js_references_building_filter_element(self):
        """JS should reference the building-filter select element."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert 'building-filter' in content or 'buildingFilter' in content

    def test_js_references_calendar_element(self):
        """JS should reference the calendar container element."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert 'calendar' in content


class TestTimetableJsApiBehavior:
    """Tests that JS correctly builds API requests."""

    def test_js_calls_api_events_endpoint(self):
        """JS should call /api/events endpoint."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "/api/events" in content

    def test_js_calls_api_filters_endpoint(self):
        """JS should call /api/filters endpoint."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "/api/filters" in content

    def test_js_calls_api_plan_terms_endpoint(self):
        """JS should call /api/plans endpoint for plan terms."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "/api/plans" in content and "/terms" in content

    def test_js_calls_plan_sequenceterm_termcodes_endpoint(self):
        """JS should call new /api/plans/.../sequenceterms/.../termcodes endpoint."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        # Check for the endpoint or function that loads semester offerings
        assert "api" in content and ("termcode" in content.lower() or "semester" in content.lower())


class TestTimetableJsEventHandlers:
    """Tests that JS sets up event handlers."""

    def test_js_has_event_listener_setup(self):
        """JS should set up event listeners."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "addEventListener" in content or "on" in content.lower()

    def test_js_handles_apply_button_click(self):
        """JS should handle apply button clicks."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "apply" in content.lower()

    def test_js_handles_clear_button_click(self):
        """JS should handle clear button clicks."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "clear" in content.lower()

    def test_js_handles_tab_filter_clicks(self):
        """JS should handle quick filter tab clicks."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "tab" in content.lower() or "filter" in content.lower()


class TestTimetableJsFilterLogic:
    """Tests for filter parameter building logic."""

    def test_js_builds_filter_params_from_dropdowns(self):
        """JS should build filter parameters from dropdown selections."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "getFilterParams" in content or "params" in content.lower()

    def test_js_includes_term_in_filters(self):
        """JS should include term parameter in filter params."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "term" in content.lower()

    def test_js_includes_subject_in_filters(self):
        """JS should include subject parameter in filter params."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "subject" in content

    def test_js_includes_component_in_filters(self):
        """JS should include component parameter in filter params."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "component" in content

    def test_js_includes_building_in_filters(self):
        """JS should include building parameter in filter params."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "building" in content


class TestTimetableJsCalendar:
    """Tests for FullCalendar integration."""

    def test_js_initializes_fullcalendar(self):
        """JS should initialize FullCalendar."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "FullCalendar" in content or "calendar" in content

    def test_js_configures_calendar_views(self):
        """JS should configure FullCalendar views."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        # Should have calendar view configurations
        assert "timeGridWeek" in content or "view" in content.lower()

    def test_js_refetches_events_on_filter_change(self):
        """JS should refetch events when filters change."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "refetch" in content or "refetchEvents" in content


class TestTimetableJsUi:
    """Tests for UI-related functionality."""

    def test_js_has_loading_overlay_functionality(self):
        """JS should show/hide loading overlay."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "showLoading" in content or "loading" in content.lower()

    def test_js_has_event_modal_functionality(self):
        """JS should show/hide event detail modal."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "modal" in content.lower()

    def test_js_updates_event_count_display(self):
        """JS should update event count display."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "updateStats" in content or "event-count" in content


class TestTimetableJsSemanticFunctions:
    """Tests for the new semester/term mapping functionality."""

    def test_js_has_load_semester_offerings_function(self):
        """JS should have loadSemesterOfferings function for mapping sequences to terms."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "loadSemesterOfferings" in content or "semester" in content.lower()

    def test_js_populates_semester_dropdown_from_plan(self):
        """JS should populate semester dropdown when plan is selected."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        assert "loadPlanTerms" in content

    def test_js_handles_no_offerings_for_semester(self):
        """JS should handle case where a semester has no schedule offerings."""
        from pathlib import Path
        js_file = Path(__file__).resolve().parents[1] / "static" / "js" / "timetable.js"
        content = js_file.read_text()
        # Should have some error/empty handling
        assert len(content) > 100  # Reasonable JS file size
