import sys
import csv
import requests
import psycopg2

"""
This script is used to import course sequence data from a CSV file into the database.
The CSV must be given as a command line argument to run the script. It has to be the first argument after the script name.
The format for the CSV file is separated into three parts: the student schedule study, the student schedules, and the schedule courses. Each part has its own header line.
The header line has to stay unmodified so the script can identify the parts. The header line for the study is:
StudyName,Owner,,,
The header line for the student schedules is:
ScheduleName,Notes,,,
The header line for the schedule courses is:
ScheduleName,Catalog,Subject,Section,TermNumber
An example file with only one term and one course is as follows:
Name,Program,EntryTerm,Option,DurationYears
"""

# PostgreSQL Configuration (REMOTE)
DB_HOST = "db-teach"
DB_PORT = 5432
DB_NAME = "uvo490_3"
DB_USER = "uvo490_3"
DB_PASSWORD = "coolbird18"

class StudentScheduleStudy:
    def __init__(self, studyname, owner):
        self.studyname = studyname
        self.owner = owner
        self.studyid = None

class StudentSchedule:
    def __init__(self, schedulename, notes):
        self.studentscheduleid = None
        self.schedulename = schedulename
        self.notes = notes
        self.studyid = None

class StudentScheduleClass:
    def __init__(self, schedulename, subject, catalog, section, termnumber):
        self.classentryid = None
        self.studentscheduleid = None
        self.classnumber = None
        self.cid = None
        self.schedulename = schedulename
        self.termnumber = termnumber
        self.subject = subject
        self.catalog = catalog
        self.section = section

# Reads the CSV file and returns a list of LabRoomAssignment objects
def import_student_schedule_study(csv_file_path):
    studentScheduleStudy = None
    studentSchedules = []
    studentScheduleClasses = []
    mode = 0 # 0 for study, 1 for schedule, 2 for classes
    with open(csv_file_path, newline='') as file:
        reader = csv.reader(file, delimiter=',', quotechar='"')
        next(reader)  # Skip header line, mode 0 first
        for row in reader:
            if (row[1].strip() == "Notes"):
                print("Importing student schedules...")
                mode = 1 # StudentSchedule
                continue
            elif (row[1].strip() == "Catalog"):
                print("Importing schedule courses...")
                mode = 2 # StudentScheduleClass
                continue

            print(f"Mode {mode} Importing row: {row}")

            if mode == 0:
                studentScheduleStudy = StudentScheduleStudy(
                    studyname=row[0].strip(),
                    owner=row[1].strip()
                )
            elif mode == 1:
                studentSchedule = StudentSchedule(
                    schedulename=row[0].strip(),
                    notes=row[1].strip()
                )
                studentSchedules.append(studentSchedule)
            elif mode == 2:
                studentScheduleClass = StudentScheduleClass(
                    schedulename=row[0].strip(),
                    subject=row[1].strip(),
                    catalog=row[2].strip(),
                    section=row[3].strip(),
                    termnumber=row[4].strip()
                )
                studentScheduleClasses.append(studentScheduleClass)

    return studentScheduleStudy, studentSchedules, studentScheduleClasses

def insert_student_schedule_study(conn, studentScheduleStudy: StudentScheduleStudy):
    try:
        with conn.cursor() as cursor:
            sql = f"SELECT studyid FROM studentschedulestudy WHERE studyname = '{studentScheduleStudy.studyname}' AND owner = '{studentScheduleStudy.owner}';"
            cursor.execute(sql)
            result = cursor.fetchone()
            if result:
                studentScheduleStudy.studyid = result[0]
                print(f"Found existing student study with id {studentScheduleStudy.studyid}, deleting existing schedule entries...")
                sql = f"DELETE FROM studentschedule WHERE studyid = {studentScheduleStudy.studyid};"
                cursor.execute(sql)
            else:
                sql = f"INSERT INTO studentschedulestudy (studyname, owner) VALUES ('{studentScheduleStudy.studyname}', '{studentScheduleStudy.owner}') RETURNING studyid;"
                cursor.execute(sql)
                studentScheduleStudy.studyid = cursor.fetchone()[0]
                print(f"Inserted new student study with id {studentScheduleStudy.studyid}")
    except Exception as e:
        print(f"Error inserting student study: {e}")
        conn.rollback()
        raise e

def insert_student_schedule(conn, studentSchedule: StudentSchedule):
    try:
        with conn.cursor() as cursor:
            sql = f"INSERT INTO studentschedule (schedulename, notes, studyid) VALUES ('{studentSchedule.schedulename}', '{studentSchedule.notes}', {studentSchedule.studyid}) RETURNING studentscheduleid;"
            cursor.execute(sql)
            studentSchedule.studentscheduleid = cursor.fetchone()[0]
            print(f"Inserted new student schedule with id {studentSchedule.studentscheduleid}")
    except Exception as e:
        print(f"Error inserting student schedule: {e}")
        conn.rollback()
        raise e

def insert_schedule_class(conn, studentScheduleClass: StudentScheduleClass):
    try:
        with conn.cursor() as cursor:
            sql = (f"SELECT classnumber, cid FROM scheduleterm WHERE "
                   + f"subject = '{studentScheduleClass.subject}' AND catalog = '{studentScheduleClass.catalog}' AND "
                   + f"section = '{studentScheduleClass.section}' AND termcode = {studentScheduleClass.termnumber} "
                   + f"ORDER BY meetingpatternnumber ASC LIMIT 1;")
            cursor.execute(sql)
            result = cursor.fetchone()
            if result: 
                studentScheduleClass.classnumber = result[0]
                studentScheduleClass.cid = result[1]
            else:
                print(f"Error finding classnumber and cid for course {studentScheduleClass.subject} {studentScheduleClass.catalog} section {studentScheduleClass.section} term {studentScheduleClass.termnumber}")
                raise Exception("Class not found")
            sql = f"INSERT INTO studentscheduleclass (studentscheduleid, classnumber, term, section, cid) VALUES ({studentScheduleClass.studentscheduleid}, {studentScheduleClass.classnumber}, {studentScheduleClass.termnumber}, '{studentScheduleClass.section}', {studentScheduleClass.cid})"
            cursor.execute(sql)
            print(f"Inserted new student course {studentScheduleClass.subject} {studentScheduleClass.catalog}")
    except Exception as e:
        print(f"Error inserting student course: {e}")
        conn.rollback()
        raise e


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide the path to the CSV file as an argument.")
        sys.exit(1)

    studentScheduleStudy, studentSchedules, studentScheduleClasses = import_student_schedule_study(sys.argv[1])
    # Need to run this in elevated powershell before. Also VPN.
    # ssh -L 9999:db-teach:5432 [netname]@login.encs.concordia.ca
    conn = psycopg2.connect(
            host="localhost",
            port=9999,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

    insert_student_schedule_study(conn, studentScheduleStudy)

    if studentScheduleStudy.studyid is None:
        print("Study insertion failed. Exiting.")
        sys.exit(1)

    for schedule in studentSchedules:
        schedule.studyid = studentScheduleStudy.studyid
        insert_student_schedule(conn, schedule)
    for course in studentScheduleClasses:
        # Find the corresponding schedule for the course
        for schedule in studentSchedules:
            if course.schedulename == schedule.schedulename:
                course.studentscheduleid = schedule.studentscheduleid
                break
        insert_schedule_class(conn, course)

    conn.commit()
    conn.close()