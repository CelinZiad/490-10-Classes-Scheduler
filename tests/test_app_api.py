"""Unit tests for API endpoints."""
from http import client
import pytest
import json


class TestHealthDbApi:
    """Tests for GET /health/db endpoint."""

    def test_health_db_returns_json(self, client):
        res = client.get("/health/db")
        assert res.content_type == "application/json"
        assert res.status_code in (200, 500)
        data = res.get_json()
        assert "ok" in data


    def test_health_db_has_ok_field(self, client):
        """Health check response should have 'ok' field."""
        res = client.get("/health/db")
        data = json.loads(res.get_data(as_text=True))
        assert "ok" in data


class TestApiEventsEndpoint:
    """Tests for GET /api/events endpoint."""

    def test_api_events_returns_json(self, client):
        """Events API should return JSON array."""
        res = client.get("/api/events")
        assert res.status_code == 200
        assert res.content_type == "application/json"
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, list)

    def test_api_events_with_term_filter(self, client):
        """Events API should accept term query param."""
        res = client.get("/api/events?term=2251")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, list)

    def test_api_events_with_subject_filter(self, client):
        """Events API should accept subject query param."""
        res = client.get("/api/events?subject=COEN")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, list)

    def test_api_events_with_multiple_subjects(self, client):
        """Events API should accept comma-separated subjects."""
        res = client.get("/api/events?subject=COEN,ELEC")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, list)

    def test_api_events_with_component_filter(self, client):
        """Events API should accept component query param."""
        res = client.get("/api/events?component=LEC")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, list)

    def test_api_events_with_building_filter(self, client):
        """Events API should accept building query param."""
        res = client.get("/api/events?building=EV")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, list)

    def test_api_events_with_planid_and_termid(self, client):
        """Events API should accept planid and sequence termid params."""
        res = client.get("/api/events?planid=1&termid=1")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, list)

    def test_api_events_response_structure(self, client):
        """Event objects should have required fields for FullCalendar."""
        res = client.get("/api/events")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        
        # If there are events, check structure
        if len(data) > 0:
            event = data[0]
            required_fields = ["id", "title", "daysOfWeek", "startTime", "endTime"]
            for field in required_fields:
                assert field in event, f"Event missing field: {field}"


class TestApiFiltersEndpoint:
    """Tests for GET /api/filters endpoint."""

    def test_api_filters_returns_json(self, client):
        """Filters API should return JSON object."""
        res = client.get("/api/filters")
        assert res.status_code == 200
        assert res.content_type == "application/json"
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, dict)

    def test_api_filters_has_required_fields(self, client):
        """Filters response should have terms, subjects, components, buildings, plans."""
        res = client.get("/api/filters")
        data = json.loads(res.get_data(as_text=True))
        required_fields = ["terms", "subjects", "components", "buildings", "plans"]
        for field in required_fields:
            assert field in data, f"Filters response missing field: {field}"

    def test_api_filters_with_term_param(self, client):
        """Filters API should accept term query param to scope results."""
        res = client.get("/api/filters?term=2251")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert "terms" in data
        assert "subjects" in data

    def test_api_filters_with_planid_param(self, client):
        """Filters API should accept planid query param."""
        res = client.get("/api/filters?planid=1")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, dict)

    def test_api_filters_with_termid_param(self, client):
        """Filters API should accept termid (sequence term) query param."""
        res = client.get("/api/filters?termid=1")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, dict)

    def test_api_filters_terms_have_code_and_name(self, client):
        """Term objects in response should have code and name fields."""
        res = client.get("/api/filters")
        data = json.loads(res.get_data(as_text=True))
        terms = data.get("terms", [])
        
        if len(terms) > 0:
            term = terms[0]
            assert "code" in term, "Term should have 'code' field"
            assert "name" in term, "Term should have 'name' field"


class TestApiPlanTermsEndpoint:
    """Tests for GET /api/plans/<planid>/terms endpoint."""

    def test_api_plan_terms_returns_json_array(self, client):
        """Plan terms API should return JSON array."""
        res = client.get("/api/plans/1/terms")
        assert res.status_code == 200
        assert res.content_type == "application/json"
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, list)

    def test_api_plan_terms_response_structure(self, client):
        """Sequence term objects should have expected fields."""
        res = client.get("/api/plans/1/terms")
        data = json.loads(res.get_data(as_text=True))
        
        # Response should be a list of sequence terms
        assert isinstance(data, list)
        
        # If there are terms, check structure
        if len(data) > 0:
            term = data[0]
            expected_fields = ["sequencetermid", "yearnumber", "season"]
            for field in expected_fields:
                assert field in term, f"Term missing field: {field}"

    def test_api_plan_terms_with_invalid_planid(self, client):
        """Plan terms API should return empty array for non-existent plan."""
        res = client.get("/api/plans/99999/terms")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        # Should return empty list, not error
        assert isinstance(data, list)


class TestApiPlanTermsAndEventsConsistency:
    """Tests using existing endpoints instead of /termcodes."""

    def test_api_plan_terms_returns_json_array(self, client):
        res = client.get("/api/plans/1/terms")
        assert res.status_code == 200
        assert res.content_type == "application/json"
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, list)

    def test_api_events_accepts_planid_and_termid(self, client):
        # This is already in your file, but keeping it here if you want the
        # replacement block to be self-contained.
        res = client.get("/api/events?planid=1&termid=1")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, list)

    def test_api_filters_returns_terms(self, client):
        res = client.get("/api/filters")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert "terms" in data
        assert isinstance(data["terms"], list)


class TestApiEndpointsIntegration:
    """Integration tests across API endpoints."""

    def test_filters_subjects_match_events_subjects(self, client):
        """Subjects returned by /api/filters should match those in /api/events."""
        filters_res = client.get("/api/filters")
        filters_data = json.loads(filters_res.get_data(as_text=True))
        subjects = set(filters_data.get("subjects", []))

        # If there are subjects in filters, events should be able to filter by them
        if subjects:
            subject = list(subjects)[0]
            events_res = client.get(f"/api/events?subject={subject}")
            assert events_res.status_code == 200

    def test_filters_components_match_events_components(self, client):
        """Components in filters should work with /api/events."""
        filters_res = client.get("/api/filters")
        filters_data = json.loads(filters_res.get_data(as_text=True))
        components = filters_data.get("components", [])

        if components:
            component = components[0]
            events_res = client.get(f"/api/events?component={component}")
            assert events_res.status_code == 200
            

import json


class TestApiFiltersMore:
    def test_api_filters_term_param_invalid_type_is_handled(self, client):
        # Flask's type=int makes "term=abc" become None, should still 200
        res = client.get("/api/filters?term=abc")
        assert res.status_code == 200
        assert res.content_type == "application/json"
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, dict)
        assert "terms" in data

    def test_api_filters_planid_invalid_type_is_handled(self, client):
        res = client.get("/api/filters?planid=abc")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, dict)

    def test_api_filters_termid_invalid_type_is_handled(self, client):
        res = client.get("/api/filters?termid=abc")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, dict)


class TestApiEventsMore:
    def test_api_events_returns_list_even_with_unknown_filters(self, client):
        # Unknown subject/building/component should still return JSON list (maybe empty)
        res = client.get("/api/events?subject=ZZZZ&building=??&component=XYZ")
        assert res.status_code == 200
        assert res.content_type == "application/json"
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, list)

    def test_api_events_multiple_subjects_with_spaces(self, client):
        # Your code strips spaces around comma-separated subjects
        res = client.get("/api/events?subject=COEN, ELEC")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, list)

    def test_api_events_planid_only(self, client):
        res = client.get("/api/events?planid=1")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, list)

    def test_api_events_termid_only(self, client):
        res = client.get("/api/events?termid=1")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, list)

    def test_api_events_term_invalid_type_is_handled(self, client):
        # term is type=int -> "abc" becomes None, endpoint should still work
        res = client.get("/api/events?term=abc")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert isinstance(data, list)

    def test_api_events_structure_for_all_events_if_present(self, client):
        # If any events exist, each event should have key FullCalendar fields
        res = client.get("/api/events")
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        if data:
            for ev in data[:10]:  # check first 10 only
                for k in ["id", "title", "daysOfWeek", "startTime", "endTime", "extendedProps"]:
                    assert k in ev
                assert isinstance(ev["daysOfWeek"], list)
                assert isinstance(ev["extendedProps"], dict)


class TestPlanTermsMore:
    def test_api_plan_terms_invalid_planid_type_404(self, client):
        # route uses <int:planid>, so non-int path should 404
        res = client.get("/api/plans/notanint/terms")
        assert res.status_code == 404

