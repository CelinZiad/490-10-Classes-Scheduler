# 490-10-Classes-Scheduler
Capstone Project Repo, Team 10

### Setup Instructions
1. Clone the repository to your local machine.
2. Create a virtual environment and activate it.
3. Install the required dependencies using `pip install -r requirements.txt`.
4. Set up the database by running the provided migration scripts.
5. Run the application using 
```powershell
$env:FLASK_APP = "app.py"
$env:FLASK_ENV = "development"
flask run
```

6. Run tests using `pytest` to ensure everything is working correctly.
```powershell
    # Run all tests
    pytest -q
    
    # Run only integration tests (requires database)
    pytest -q -m integration
    
    # Run specific test file
    pytest tests/test_app_routes.py -v
    
    # Run with coverage report
    pytest --cov=app --cov-report=html
```

### Test Suite Overview
The project includes comprehensive test coverage:

**Backend Tests:**
- `test_app_routes.py` - Tests for route handlers, page rendering, and HTTP status codes
- `test_app_api.py` - Tests for API endpoints (/api/events, /api/filters, /api/plans/...)

**Template Tests:**
- `test_templates.py` - Tests for Jinja2 template inheritance, structure, and HTML validity

**Frontend Tests:**
- `test_timetable_js.py` - Tests for JavaScript code structure and API integration

**Existing Tests:**
- `test_unit_routes.py` - Tests for route registration and template existence
- `test_integration_pages.py` - Integration tests that verify pages render (requires database)

To run tests with coverage:
```powershell
pytest --cov=app --cov-report=term-missing
```
