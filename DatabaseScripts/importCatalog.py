import sys
import csv
import requests
import psycopg2

"""
This script is used to import course catalog data from a CSV file into the database.
The format for the CSV file is:
Subject,Catalog,Title,Career,ClassUnit,Prerequisites
The first line is for headers only and will be ignored.
Example of a row:
COEN,99234,TestImport,UGRD,4.5,COEN314
"""

# PostgreSQL Configuration (REMOTE)
DB_HOST = "db-teach"
DB_PORT = 5432
DB_NAME = "uvo490_3"
DB_USER = "uvo490_3"
DB_PASSWORD = "coolbird18"

class Catalog:
    def __init__(self, title, subject, catalog, career, classunit, prerequisites):
        self.title = title
        self.subject = subject
        self.catalog = catalog
        self.career = career
        self.classunit = classunit
        self.prerequisites = prerequisites  
        self.id = None

# Reads the CSV file and returns a list of Catalog objects
def import_catalog_data(csv_file_path):
    items = []
    with open(csv_file_path, newline='') as file:
        reader = csv.reader(file, delimiter=',', quotechar='"')
        next(reader)  # Skip header line
        for row in reader:
            if len(row) != 6:
                print(f"Skipping invalid row: {row}")
                continue
            print(f"Importing row: {row}")
            item = Catalog(
                subject=row[0].strip(),
                catalog=row[1].strip(),
                title=row[2].strip(),
                career=row[3].strip(),
                classunit=row[4].strip(),
                prerequisites=row[5].strip()
            )
            items.append(item)
    return items

def update_or_insert_catalog(conn, catalog):
    try:
        with conn.cursor() as cursor:
            sql = f"SELECT id FROM catalog WHERE subject = '{catalog.subject}' AND catalog = '{catalog.catalog}';"
            cursor.execute(sql)
            result = cursor.fetchone()
            if result:
                sql = f"UPDATE catalog SET title = '{catalog.title}', career = '{catalog.career}', classunit = '{catalog.classunit}', prerequisites = '{catalog.prerequisites}' WHERE subject = '{catalog.subject}' AND catalog = '{catalog.catalog}';"
                cursor.execute(sql)
                print(f"Updated existing catalog entry for {catalog.subject} {catalog.catalog}")
            else:
                sql = (f"INSERT INTO catalog (id, subject, catalog, title, career, classunit, prerequisites) VALUES ("
                       + f"(SELECT COALESCE(MAX(id), 0) + 1 FROM catalog), "
                       + f"'{catalog.subject}', '{catalog.catalog}', '{catalog.title}', '{catalog.career}', '{catalog.classunit}', '{catalog.prerequisites}');")
                cursor.execute(sql)
                print(f"Inserted new catalog entry for {catalog.subject} {catalog.catalog}")

    except Exception as e:
        print(f"Error upserting catalog entry for {catalog.subject} {catalog.catalog}: {e}")
        conn.rollback()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide the path to the CSV file as an argument.")
        sys.exit(1)
    items = import_catalog_data(sys.argv[1])
    # Need to run this in elevated powershell before. Also VPN.
    # ssh -L 9999:db-teach:5432 [netname]@login.encs.concordia.ca
    conn = psycopg2.connect(
            host="localhost",
            port=9999,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    
    for item in items:
        update_or_insert_catalog(conn, item)

    conn.commit()
    conn.close()