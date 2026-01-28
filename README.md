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
    pytest -q
    pytest -q -m integration
    pytest -q -m unit
```
