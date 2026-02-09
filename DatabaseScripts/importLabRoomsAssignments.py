import sys
import csv
import requests
import psycopg2

"""
This script is used to import lab rooms assignments data from the API into the database.
The CSV must be given as a command line argument to run the script. It has to be the first argument after the script name.
The format for the CSV file is:
Course Code, Title, Room, Capacity, CapacityMax, Responsible, Comments
The first line is for headers only and will be ignored.
The course code is like COEN 243, with a space between the subject and the catalog number.
The room can be of the format [Building Code]-[Room Number], like H-915. It can also be exactly AITS for labs to be scheduled in any computer lab.
Capacity max can also be exactly AITS.
Each row of the CSV represents exactly one pair of course and room assignment. 
If a course is assigned to multiple rooms, it needs multiple rows in the CSV file.
Example of a row:
COEN 316,COMPUTER ARCHITECT. + DESIGN,H-859,14,16,Ted,"H-913 can be used as well if a COEN 316 and  COEN 313 sections need to be scheduled concurrently, or there is a conflict between them."
"""

# PostgreSQL Configuration (REMOTE)
DB_HOST = "db-teach"
DB_PORT = 5432
DB_NAME = "uvo490_3"
DB_USER = "uvo490_3"
DB_PASSWORD = "coolbird18"

class LabRoomAssignment:
    def __init__(self, course_code, title, room, capacity, capacity_max, responsible, comments):
        self.course_code = course_code
        self.title = title
        self.room = room
        self.capacity = capacity
        self.capacity_max = capacity_max
        self.responsible = responsible
        self.comments = comments

# Reads the CSV file and returns a list of LabRoomAssignment objects
def import_lab_rooms_assignments(csv_file_path):
    items = []
    with open(csv_file_path, newline='') as file:
        reader = csv.reader(file, delimiter=',', quotechar='"')
        next(reader)  # Skip header line
        for row in reader:
            if len(row) != 7:
                print(f"Skipping invalid row: {row}")
                continue
            print(f"Importing row: {row}")
            assignment = LabRoomAssignment(
                course_code=row[0].strip(),
                title=row[1].strip(),
                room=row[2].strip(),
                capacity=row[3].strip(),
                capacity_max=row[4].strip(),
                responsible=row[5].strip(),
                comments=row[6].strip()
            )
            items.append(assignment)
    return items

def update_or_insert_lab_room(conn, assignment):
    try:
        with conn.cursor() as cursor:
            sql = f"INSERT INTO labrooms (campus, building, room, capacity, capacitymax) VALUES "
            if (assignment.room == "AITS"):
                sql += f"('SGW', 'H', 'AITS', {int(assignment.capacity)}, 100) "
            else:
                building, room = assignment.room.split("-", 1)
                sql += f"('SGW', '{building}', '{room}', {int(assignment.capacity)}, {int(assignment.capacity_max)}) "

            sql += f"ON CONFLICT (campus, building, room) DO UPDATE SET capacity = EXCLUDED.capacity, capacitymax = EXCLUDED.capacitymax;"
            cursor.execute(sql)
            print(f"Upserted new lab room {assignment.room}")
            
    except Exception as e:
        print(f"Error upserting lab room {assignment.room}: {e}")
        conn.rollback()

def update_or_insert_assignment(conn, assignment):
    try:
        with conn.cursor() as cursor:
            subject, catalog = assignment.course_code.split(" ", 1)
            campus = "SGW"
            room = ""
            building = ""
            if (assignment.room == "AITS"):
                room = "AITS"
                building = "H"
            else:
                building, room = assignment.room.split("-", 1)

            sql = (f"INSERT INTO courselabs (labroomid, subject, catalog, comments) "
            + f"VALUES ((SELECT labroomid FROM labrooms WHERE campus = '{campus}' AND building = '{building}' AND room = '{room}'), '{subject}', '{catalog}', '{assignment.comments}') "
            + f"ON CONFLICT (labroomid, subject, catalog) DO UPDATE SET comments = EXCLUDED.comments;")

            cursor.execute(sql)
            print(f"Upserted course lab assignment for course {assignment.course_code} in room {assignment.room}")
    except Exception as e:
        print(f"Error upserting course lab assignment for course {assignment.course_code} in room {assignment.room}: {e}")
        conn.rollback()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide the path to the CSV file as an argument.")
        sys.exit(1)
    items = import_lab_rooms_assignments(sys.argv[1])
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
        update_or_insert_lab_room(conn, item)
        conn.commit()
        update_or_insert_assignment(conn, item)
        conn.commit()

    conn.close()