from datetime import time


def minutes_to_time(mins: int) -> time:
    return time(mins // 60, mins % 60)


def save_lab_results_to_db(
    cur,
    subject: str,
    catalog: str,
    lab_duration_min: int,
    results: dict
) -> None:

    if not results:
        return

    insert_sql = """
        INSERT INTO lab_slot_result (
            subject,
            catalog,
            classstarttime,
            classendtime,
            mondays,
            tuesdays,
            wednesdays,
            thursdays,
            fridays,
            saturdays,
            sundays,
            studyids
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """

    for (day, start_min), studyids in results.items():
        start_min = int(start_min)
        end_min = start_min + int(lab_duration_min)

        isodow = ((int(day) - 1) % 7) + 1

        mondays    = isodow == 1
        tuesdays   = isodow == 2
        wednesdays = isodow == 3
        thursdays  = isodow == 4
        fridays    = isodow == 5
        saturdays  = isodow == 6
        sundays    = isodow == 7

        start_time = minutes_to_time(start_min)
        end_time   = minutes_to_time(end_min)

        cur.execute(
            insert_sql,
            (
                subject,
                catalog,
                start_time,
                end_time,
                mondays,
                tuesdays,
                wednesdays,
                thursdays,
                fridays,
                saturdays,
                sundays,
                list(map(int, studyids)),
            ),
        )

