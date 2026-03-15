import sys
import csv
import requests
import psycopg2

"""
This script is used to import course sequence data from a CSV file into the database.
The CSV must be given as a command line argument to run the script. It has to be the first argument after the script name.
The format for the CSV file is separated into three parts: the sequence plan, the sequence terms, and the sequence courses. Each part has its own header line.
The header line has to stay unmodified so the script can identify the parts. The header line for the sequence plan is:
Name,Program,EntryTerm,Option,DurationYears
The header line for the sequence terms is:
TermNumber,YearNumber,Season,WorkTerm,Notes
The header line for the sequence courses is:
TermNumber,Subject,Catalog,Label,
An example file with only one term and one course is as follows:
Name,Program,EntryTerm,Option,DurationYears
TESTIMPORT,COEN,fall,COOP,4
TermNumber,YearNumber,Season,WorkTerm,Notes
1,1,fall,FALSE,
TermNumber,Subject,Catalog,Label,
1,COEN,243,,
TermNumber is used to link the courses to the terms. A course with term number 1 will be linked to the term with term number 1.
The actual sequencetermid will be generated when inserting the sequence term into the database.
"""

# PostgreSQL Configuration (REMOTE)
DB_HOST = "db-teach"
DB_PORT = 5432
DB_NAME = "uvo490_3"
DB_USER = "uvo490_3"
DB_PASSWORD = "coolbird18"

class SequencePlan:
    def __init__(self, planname, program, entryterm, option, durationyears):
        self.planname = planname
        self.program = program
        self.entryterm = entryterm
        self.option = option
        self.durationyears = durationyears
        self.planid = None

class SequenceTerm:
    def __init__(self, termnumber, yearnumber, season, workterm, notes):
        self.planid = None
        self.yearnumber = yearnumber
        self.termnumber = termnumber
        self.season = season
        self.workterm = workterm
        self.notes = notes
        self.sequencetermid = None

class SequenceCourse:
    def __init__(self, termnumber, subject, catalog, label):
        self.sequencetermid = None
        self.termnumber = termnumber
        self.subject = subject
        self.catalog = catalog
        self.label = label

# Reads the CSV file and returns a list of LabRoomAssignment objects
def import_sequence(csv_file_path):
    sequencePlan = None
    sequenceTerms = []
    sequenceCourses = []
    mode = 0 # 0 for plan, 1 for term, 2 for course
    with open(csv_file_path, newline='') as file:
        reader = csv.reader(file, delimiter=',', quotechar='"')
        next(reader)  # Skip header line, mode 0 first
        for row in reader:
            if (row[1].strip() == "YearNumber"):
                print("Importing sequence terms...")
                mode = 1 # SequenceTerm
                continue
            elif (row[1].strip() == "Subject"):
                print("Importing sequence courses...")
                mode = 2 # SequenceCourse
                continue

            print(f"Mode {mode} Importing row: {row}")

            if mode == 0:
                sequencePlan = SequencePlan(
                    planname=row[0].strip(),
                    program=row[1].strip(),
                    entryterm=row[2].strip(),
                    option=row[3].strip(),
                    durationyears=row[4].strip()
                )
            elif mode == 1:
                sequenceTerm = SequenceTerm(
                    termnumber=row[0].strip(),
                    yearnumber=row[1].strip(),
                    season=row[2].strip(),
                    workterm=row[3].strip(),
                    notes=row[4].strip()
                )
                sequenceTerms.append(sequenceTerm)
            elif mode == 2:
                sequenceCourse = SequenceCourse(
                    termnumber=row[0].strip(),
                    subject=row[1].strip(),
                    catalog=row[2].strip(),
                    label=row[3].strip()
                )
                sequenceCourses.append(sequenceCourse)
            
    return sequencePlan, sequenceTerms, sequenceCourses

def insert_sequence_plan(conn, sequencePlan):
    try:
        with conn.cursor() as cursor:
            sql = f"INSERT INTO sequenceplan (planname, program, entryterm, option, durationyears) VALUES ('{sequencePlan.planname}', '{sequencePlan.program}', '{sequencePlan.entryterm}', '{sequencePlan.option}', {int(sequencePlan.durationyears)}) RETURNING planid;"
            cursor.execute(sql)
            sequencePlan.planid = cursor.fetchone()[0]
            print(f"Inserted new sequence plan with id {sequencePlan.planid}")
    except Exception as e:
        print(f"Error inserting sequence plan: {e}")
        conn.rollback()

def insert_sequence_term(conn, sequenceTerm):
    try:
        with conn.cursor() as cursor:
            sql = f"INSERT INTO sequenceterm (planid, yearnumber, season, workterm, notes) VALUES ({sequenceTerm.planid}, {int(sequenceTerm.yearnumber)}, '{sequenceTerm.season}', {sequenceTerm.workterm}, '{sequenceTerm.notes}') RETURNING sequencetermid;"
            cursor.execute(sql)
            sequenceTerm.sequencetermid = cursor.fetchone()[0]
            print(f"Inserted new sequence term with id {sequenceTerm.sequencetermid}")
    except Exception as e:
        print(f"Error inserting sequence term: {e}")
        conn.rollback()

def insert_sequence_course(conn, sequenceCourse):
    try:
        with conn.cursor() as cursor:
            sql = f"INSERT INTO sequencecourse (sequencetermid, subject, catalog, label) VALUES ({sequenceCourse.sequencetermid}, '{sequenceCourse.subject}', '{sequenceCourse.catalog}', '{sequenceCourse.label}');"
            cursor.execute(sql)
            print(f"Inserted new sequence course {sequenceCourse.subject} {sequenceCourse.catalog}")
    except Exception as e:
        print(f"Error inserting sequence course: {e}")
        conn.rollback()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide the path to the CSV file as an argument.")
        sys.exit(1)
    sequencePlan, sequenceTerms, sequenceCourses = import_sequence(sys.argv[1])
    # Need to run this in elevated powershell before. Also VPN.
    # ssh -L 9999:db-teach:5432 [netname]@login.encs.concordia.ca
    conn = psycopg2.connect(
            host="localhost",
            port=9999,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

    insert_sequence_plan(conn, sequencePlan)

    if sequencePlan.planid is None:
        print("Sequence plan insertion failed. Exiting.")
        sys.exit(1)

    for term in sequenceTerms:
        term.planid = sequencePlan.planid
        insert_sequence_term(conn, term)
    for course in sequenceCourses:
        # Find the corresponding term for the course
        for term in sequenceTerms:
            if term.termnumber == course.termnumber:
                course.sequencetermid = term.sequencetermid
                break
        insert_sequence_course(conn, course)

    conn.commit()
    conn.close()