import sys
import os
import csv
import psycopg2
from dotenv import load_dotenv

"""
This script is used to import schedule data from a CSV file into the database.
Format for the CSV file is:
1st line is for headers only and will be ignored.
AcYr,FrisYr,Sess,Dept,Sect,Course,Msec,Rel1,Rel2,Cap,MarkCal,Activity,Class Day,Start,Finish,U/G,Disc Date,ClassStartDate,ClassEndDate
"""

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 9999))
DB_NAME = os.getenv("DB_NAME", "uvo490_3")
DB_USER = os.getenv("DB_USER", "uvo490_3")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

class ScheduleItem:
    def __init__(self, subject, catalog, section, componentcode, termcode, classnumber, session, buildingcode, room, instructionmodecode, locationcode, currentwaitlisttotal, waitlistcapacity, enrollmentcapacity, currentenrollment, departmentcode, facultycode, classstarttime, classendtime, classstartdate, classenddate, mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays, facultydescription, career, meetingpatternnumber,cid):
        self.subject = subject
        self.catalog = catalog
        self.section = section
        self.componentcode = componentcode
        self.termcode = termcode
        self.classnumber = classnumber
        self.session = session
        self.buildingcode = buildingcode
        self.room = room
        self.instructionmodecode = instructionmodecode
        self.locationcode = locationcode
        self.currentwaitlisttotal = currentwaitlisttotal
        self.waitlistcapacity = waitlistcapacity
        self.enrollmentcapacity = enrollmentcapacity
        self.currentenrollment = currentenrollment
        self.departmentcode = departmentcode
        self.facultycode = facultycode
        self.classstarttime = classstarttime
        self.classendtime = classendtime
        self.classstartdate = classstartdate
        self.classenddate = classenddate
        self.mondays = mondays
        self.tuesdays = tuesdays
        self.wednesdays = wednesdays
        self.thursdays = thursdays
        self.fridays = fridays
        self.saturdays = saturdays
        self.sundays = sundays  
        self.facultydescription= facultydescription  
        self.career= career  
        self.meetingpatternnumber= meetingpatternnumber  
        self.cid= cid  

# Monday is first, sunday is last.
def get_course_days(class_day_string):
    if len(class_day_string) != 7:
        print(f"Invalid class day string: {class_day_string}")
        return None
    days = []
    for index, char in enumerate(class_day_string):
        if char == '-':
            days.append(False)
        else:
            days.append(True)
    return days

# Only gets data from the CSV file. The DB will need to complete missing data.
def import_csv_schedule(csv_file_path):
    items = []
    with open(csv_file_path, newline='') as file:
        reader = csv.reader(file, delimiter=',', quotechar='"')
        next(reader)  # Skip header line
        for row in reader:
            if len(row) != 19:
                print(f"Skipping invalid row: {row}")
                continue
            days = get_course_days(row[12].strip())
            if days is None:
                print(f"Skipping row with invalid class day string: {row}")
                continue
            print(f"Importing row: {row}")

            section = ""
            if (row[6].strip() != ""):
                section = row[6].strip()
            else:
                section = row[7].strip()

            # 1st, 3rd, 4th digit of year + (1 (summer), 2(fall), 3(fall/winter), 4(winter), 5(spring, CCCE), 6(winter, CCCE))
            if (row[2].strip() == "Winter"):
                year = int(row[0].strip()) - 1
                year_str = str(year)
                session = '13W'
                termcode = year_str[0] + year_str[2] + year_str[3] + '4'
            elif (row[2].strip() == "Summer"):
                if (row[6].strip() == 'COEN390' or row[6].strip() == 'ELEC390'):
                    year = int(row[0].strip())
                    year_str = str(year)
                    session = '13W'
                    termcode = year_str[0] + year_str[2] + year_str[3] + '1'
                else:
                    year = int(row[0].strip())
                    year_str = str(year)
                    if (int(row[16].strip().split('-')[1]) <= 6):
                        session = '6H1'
                    else:
                        session = '6H2'
                    termcode = year_str[0] + year_str[2] + year_str[3] + '1'
            else: # Fall
                year = int(row[0].strip())
                year_str = str(year)
                session = '13W'
                termcode = year_str[0] + year_str[2] + year_str[3] + '2'

            career = 'UGRD' if row[15].strip() == 'U' else 'GRAD'

            department = ""
            faculty = ""
            facultydescription = ""
            if (row[3].strip() == "ECE"):
                department = 'ELECCOEN'
                faculty = 'ENCS'
                facultydescription = 'Gina Cody School of Engineering & Computer Science'

            schedule_item = ScheduleItem(
                subject=row[5].strip()[:4],
                catalog=row[5].strip()[4:],
                section=section,
                componentcode=row[11].strip().split("-")[0],
                termcode=termcode,
                classnumber='',
                session=session,
                buildingcode='',
                room='',
                instructionmodecode='',
                locationcode='',
                currentwaitlisttotal='',
                waitlistcapacity='',
                enrollmentcapacity=row[9].strip(),
                currentenrollment='',
                departmentcode=department,
                facultycode=faculty,
                classstarttime=row[13].strip(),
                classendtime=row[14].strip(),
                classstartdate=row[17].strip(),
                classenddate=row[18].strip(),
                mondays=days[0],
                tuesdays=days[1],
                wednesdays=days[2],
                thursdays=days[3],
                fridays=days[4],
                saturdays=days[5],
                sundays=days[6],
                facultydescription=facultydescription,
                career=career,
                meetingpatternnumber='1',
                cid=''
            )
            items.append(schedule_item)
            print(schedule_item.__dict__)
    return items

def complete_schedule_item_data(conn, schedule_item : ScheduleItem):
    try:
        with conn.cursor() as cursor:
            sql = f"SELECT classnumber FROM section WHERE subject = '{schedule_item.subject}' AND catalog = '{schedule_item.catalog}' AND section = '{schedule_item.section}' AND term = '{schedule_item.termcode}';"
            cursor.execute(sql)
            result = cursor.fetchone()
            if result:
                schedule_item.classnumber = result[0]
            else:
                print(f"Could not find classnumber for {schedule_item.subject} {schedule_item.catalog} {schedule_item.section} {schedule_item.termcode}, creating new section.")
                sql = (f"INSERT INTO section (term, session, subject, catalog, component, classnumber, classenrollcapacity, section) VALUES ("
                    + f"{schedule_item.termcode}, '{schedule_item.session}', '{schedule_item.subject}', '{schedule_item.catalog}', '{schedule_item.componentcode}', "
                    + f"(SELECT COALESCE(MAX(classnumber), 0) + 1 FROM section), {schedule_item.enrollmentcapacity}, '{schedule_item.section}') RETURNING classnumber;")
                cursor.execute(sql)
                schedule_item.classnumber = cursor.fetchone()[0]
    except Exception as e:
        print(f"Error occurred while completing schedule item data: {e}")
        conn.rollback()
        raise e
    
def insert_schedule_data(conn, schedule_item : ScheduleItem):
    try:
        with conn.cursor() as cursor:
            sql = (f"INSERT INTO scheduleterm (subject, \"catalog\", \"section\", componentcode, termcode, "
                   + f"classnumber, \"session\", enrollmentcapacity, departmentcode, facultycode, "
                   + f"classstarttime, classendtime, classstartdate, classenddate, "
                   + f"mondays, tuesdays, wednesdays, thursdays, fridays, saturdays, sundays, "
                   + f"facultydescription, career, meetingpatternnumber) VALUES ("
                   + f"'{schedule_item.subject}', '{schedule_item.catalog}', '{schedule_item.section}', '{schedule_item.componentcode}', '{schedule_item.termcode}', "
                   + f"'{schedule_item.classnumber}', '{schedule_item.session}', '{schedule_item.enrollmentcapacity}', '{schedule_item.departmentcode}', '{schedule_item.facultycode}', "
                   + f"'{schedule_item.classstarttime}', '{schedule_item.classendtime}', '{schedule_item.classstartdate}', '{schedule_item.classenddate}', "
                   + f"'{schedule_item.mondays}', '{schedule_item.tuesdays}', '{schedule_item.wednesdays}', '{schedule_item.thursdays}', '{schedule_item.fridays}', '{schedule_item.saturdays}', '{schedule_item.sundays}', "
                   + f"'{schedule_item.facultydescription}', '{schedule_item.career}', '{schedule_item.meetingpatternnumber}')"
                   + f"ON CONFLICT (subject, catalog, section, termcode, classnumber, meetingpatternnumber) DO UPDATE SET "
                   + f"componentcode = EXCLUDED.componentcode, session = EXCLUDED.session, enrollmentcapacity = EXCLUDED.enrollmentcapacity, departmentcode = EXCLUDED.departmentcode, facultycode = EXCLUDED.facultycode, "
                   + f"classstarttime = EXCLUDED.classstarttime, classendtime = EXCLUDED.classendtime, classstartdate = EXCLUDED.classstartdate, classenddate = EXCLUDED.classenddate, "
                   + f"mondays = EXCLUDED.mondays, tuesdays = EXCLUDED.tuesdays, wednesdays = EXCLUDED.wednesdays, thursdays = EXCLUDED.thursdays, fridays = EXCLUDED.fridays, saturdays = EXCLUDED.saturdays, sundays = EXCLUDED.sundays,"
                   + f"facultydescription = EXCLUDED.facultydescription, career = EXCLUDED.career")
            cursor.execute(sql)
            print(f"Inserted or updated schedule item for {schedule_item.subject} {schedule_item.catalog} {schedule_item.section} {schedule_item.termcode}")
    except Exception as e:
        print(f"Error occurred while inserting schedule item data: {e}")
        conn.rollback()
        raise e

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide the path to the CSV file as an argument.")
        sys.exit(1)
    items = import_csv_schedule(sys.argv[1])

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
        complete_schedule_item_data(conn, item)
        insert_schedule_data(conn, item)

    conn.commit()
    conn.close()
