import sys
import csv
import requests
import psycopg2

"""
This script is used to import schedule data from a CSV file into the database.
Format for the CSV file is:
1st line is for headers only and will be ignored.
AcYr,FrisYr,Sess,Dept,Sect,Course,Msec,Rel1,Rel2,Cap,MarkCal,Activity,Class Day,Start,Finish,U/G,Disc Date
"""

# PostgreSQL Configuration (REMOTE)
DB_HOST = "db-teach"
DB_PORT = 5432
DB_NAME = "uvo490_3"
DB_USER = "uvo490_3"
DB_PASSWORD = "coolbird18"

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
            if len(row) != 17:
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
                departmentcode='ELECCOEN',
                facultycode='ENCS',
                classstarttime=row[13].strip(),
                classendtime=row[14].strip(),
                classstartdate='',
                classenddate='',
                mondays=days[0],
                tuesdays=days[1],
                wednesdays=days[2],
                thursdays=days[3],
                fridays=days[4],
                saturdays=days[5],
                sundays=days[6],
                facultydescription='',
                career=career,
                meetingpatternnumber='',
                cid=''
            )
            items.append(schedule_item)
            print(schedule_item.__dict__)
    return items

def complete_schedule_item_data(schedule_item):
    # This function can be used to complete missing data for a schedule item by querying the database or using other logic.
    # For example, we can query the database to get the class number, building code, room, etc. based on the subject, catalog, and section.
    pass

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

    conn.close()