from waitlist_algorithm.db import get_conn

query = """
SELECT classnumber, subject, catalog, termcode,
       classstarttime, classendtime,
       mondays, tuesdays, wednesdays, thursdays, fridays
FROM scheduleterm
WHERE subject = 'COEN'
LIMIT 5;
"""



with get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute(query)
        rows= cur.fetchall()

for row in rows:
    print(row)