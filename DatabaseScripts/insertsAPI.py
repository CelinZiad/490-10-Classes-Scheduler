import requests
import psycopg2
import json

# -------------------------------
# CONFIGURATION
# -------------------------------

# Concordia Open Data
API_URL = "https://opendata.concordia.ca/API/v1"

# PostgreSQL Configuration (REMOTE)
DB_HOST = "db-teach"
DB_PORT = 5432
DB_NAME = "uvo490_3"
DB_USER = "uvo490_3"
DB_PASSWORD = "coolbird18"

def yn_to_bool(value):
    return 'TRUE' if value.upper() == 'Y' else 'FALSE'

def career_to_code(value):
    value = value.strip()
    value = value.lower()
    mapping = {
        "undergraduate": "UGRD",
        "graduate": "GRAD",
        "continuing education": "CCCE",
        "professional development": "PDEV"
    }
    return mapping.get(value, value)

def sanitize_meeting_patten_number(value):
    if value is None or value == "":
        return "1"
    return value

# Building Table
BUILDING_TABLE = "building"
BUILDING_SCHEMA = "campus, building, buildingname, address, latitude, longitude"
def building_filter():
    return "/facilities/buildinglist/"
def building_api_to_db(data):
    return f"'{data['Campus']}','{data['Building']}','{data['Building_Name']}','{data['Address']}','{data['Latitude']}','{data['Longitude']}'"

# Section Table
SECTION_TABLE = "section"
SECTION_SCHEMA = 'term, "session", overallenrollcapacity, overallenrollments, overallwaitlistcapacity, overallwaitlisttotal, subject, "catalog", component, classnumber, classenrollcapacity, classenrollments, classwaitlistcapacity, classwaitlisttotal, "section"'
def section_filter(subject="*", catalog="*"):
    return f"/course/section/filter/{subject}/{catalog}"
def section_api_to_db(data):
    # There is a typo in the API for overallWaitlisTotal, it is intended.
    return f"{data['term']},'{data['session']}',{data['overallEnrollCapacity']},{data['overallEnrollments']},{data['overallWaitlistCapacity']},{data['overallWaitlisTotal']},'{data['subject']}','{data['catalog']}','{data['components']}',{data['classNumber']},{data['classEnrollCapacity']},{data['classEnrollments']},{data['classWaitlistCapacity']},{data['classWaitlistTotal']},'{data['section']}'"

# Catalog Table
CATALOG_TABLE = "catalog"
CATALOG_SCHEMA = "id, title, subject, \"catalog\", career, classunit, prerequisites"
def catalog_filter(subject="*", catalog="*", career="*"):
    return f"/course/catalog/filter/{subject}/{catalog}/{career}"
def catalog_api_to_db(data):
    return f"'{data['ID']}','{data['title']}','{data['subject']}','{data['catalog']}','{data['career']}',{data['classUnit']},'{data['prerequisites']}'"

# FacultyDept Table
FACULTYDEPT_TABLE = "facultydept"
FACULTYDEPT_SCHEMA = "facultycode, facultydescription, departmentcode, departmentdescription"
def facultydept_filter(facultyCode="*", departmentCode="*"):
    return f"/course/faculty/filter/{facultyCode}/{departmentCode}"
def facultydept_api_to_db(data):
    # The deparmentCode and deparmentDescription have a typo in the API, it is intended.
    return f"'{data['facultyCode']}','{data['facultyDescription']}','{data['deparmentCode']}','{data['deparmentDescription']}'"

# ScheduleTerm Table
SCHEDULETERM_TABLE = "scheduleterm"
SCHEDULETERM_SCHEMA = 'subject, "catalog", "section", componentcode, termcode, classnumber, "session", buildingcode, room, instructionmodecode, locationcode, currentwaitlisttotal, waitlistcapacity, enrollmentcapacity, currentenrollment, departmentcode, facultycode, classstarttime, classendtime, classstartdate, classenddate, mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays, facultydescription, career, meetingpatternnumber'
def scheduleTerm_filter(subject="*", termcode="*"):
    return f"/course/scheduleTerm/filter/{subject}/{termcode}"
def scheduleTerm_api_to_db(data):
    # There are some typos in the API like currentWaitlistTotal, it is intended.
    return f"'{data['subject']}','{data['catalog']}','{data['section']}','{data['componentCode']}',{data['termCode']},{data['classNumber']},'{data['session']}','{data['buildingCode']}','{data['room']}','{data['instructionModeCode']}','{data['locationCode']}',{data['currentWaitlistTotal']},{data['waitlistCapacity']},{data['enrollmentCapacity']},{data['currentEnrollment']},'{data['departmentCode']}','{data['facultyCode']}',TO_TIMESTAMP('{data['classStartTime']}','HH24.MI.SS'),TO_TIMESTAMP('{data['classEndTime']}','HH24.MI.SS'),TO_DATE('{data['classStartDate']}','DD-MM-YYYY'),TO_DATE('{data['classEndDate']}','DD-MM-YYYY'),{yn_to_bool(data['modays'])},{yn_to_bool(data['tuesdays'])},{yn_to_bool(data['wednesdays'])},{yn_to_bool(data['thursdays'])},{yn_to_bool(data['fridays'])},{yn_to_bool(data['saturdays'])},{yn_to_bool(data['sundays'])},'{data['facultyDescription']}','{career_to_code(data['career'])}',{sanitize_meeting_patten_number(data['meetingPatternNumber'])}"

# Sessions Table
SESSIONS_TABLE = "sessions"
SESSIONS_SCHEMA = "career, termcode, termdescription, sessioncode, sessiondescription, sessionbegindate, sessionenddate"
def session_filter(career="*", term="*", subject="*"):
    return f"/course/session/filter/{career}/{term}/{subject}"
def session_api_to_db(data):
    return f"'{data['career']}',{data['termCode']},'{data['termDescription']}','{data['sessionCode']}','{data['sessionDescription']}',TO_DATE('{data['sessionBeginDate']}','DD-MM-YYYY'),TO_DATE('{data['sessionEndDate']}','DD-MM-YYYY')"

# Gets info from API
def fetch_data(filter):
    url = f"{API_URL}{filter}"
    response = requests.get(url, auth=("926","997264599ee22d81379687f476270e7f"))
    response.raise_for_status()
    # Replace empty fields (null) with empty strings for easier SQL insertion
    data = json.dumps(response.json()).replace("null",'""')
    return json.loads(data)

def insert_into(conn, table, schema, data, api_to_db_func: callable):
    sql = f"INSERT INTO public.{table} ({schema}) VALUES "
    for row in data:
        sql += f"({api_to_db_func(row)})"
        sql += ","
    
    sql = sql[:-1]  # Remove last comma
    with open(f"{table}_insert.sql", "w") as f:
        f.write(sql)

    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM public.{table};")
        cur.execute(sql)
    
    conn.commit()


def main():
    # Need to run this in elevated powershell before. Also VPN.
    # ssh -L 9999:db-teach:5432 [netname]@login.encs.concordia.ca
    conn = psycopg2.connect(
            host="localhost",
            port=9999,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

    tuples = [[building_filter(), BUILDING_TABLE, BUILDING_SCHEMA, building_api_to_db],
              [session_filter(), SESSIONS_TABLE, SESSIONS_SCHEMA, session_api_to_db],
              [facultydept_filter(), FACULTYDEPT_TABLE, FACULTYDEPT_SCHEMA, facultydept_api_to_db],
              [catalog_filter(), CATALOG_TABLE, CATALOG_SCHEMA, catalog_api_to_db],
              [section_filter(), SECTION_TABLE, SECTION_SCHEMA, section_api_to_db],
              [scheduleTerm_filter(), SCHEDULETERM_TABLE, SCHEDULETERM_SCHEMA, scheduleTerm_api_to_db]]
    
    for t in tuples:
        print(f"Fetching data for table {t[1]}...")
        data = fetch_data(t[0])
        if len(data) != 0:
            print(f"Fetched {len(data)} rows")
            print(data[0])
            insert_into(conn, t[1], t[2], data, t[3])
            print("Data insertion complete.")
        else:
            print("No data found. Exiting.")
    
    conn.close()

if __name__ == "__main__":
    main()
