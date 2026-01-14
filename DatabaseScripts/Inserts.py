import requests
import psycopg2
import json
import pandas as pd

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

# Building Table
BUILDING_TABLE = "building"
BUILDING_SCHEMA = "campus, building, buildingname, address, latitude, longitude"
def building_filter():
    return "/facilities/buildinglist/"
def building_api_to_db(data):
    return f"'{data['Campus']}','{data['Building']}','{data['Building_Name']}','{data['Address']}','{data['Latitude']}','{data['Longitude']}'"

def section_filter(subject="*", catalog="*", career="*", term="*"):
    return f"/course/section/filter/{subject}/{catalog}/{career}/{term}"

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

def scheduleTerm_filter(subject="*", termcode="*"):
    return f"/course/scheduleTerm/filter/{subject}/{termcode}"

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
              [catalog_filter(), CATALOG_TABLE, CATALOG_SCHEMA, catalog_api_to_db]]
    
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
