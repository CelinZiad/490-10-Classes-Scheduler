from waitlist_algorithm.algorithm.time_block import TimeBlock,to_minutes


def load_room_busy_for_course(cur, subject: str, catalog: str) -> list[TimeBlock]:
    sql = """
    WITH allowed_rooms AS (
        SELECT lr.building, lr.room
        FROM courselabs cl
        JOIN labrooms lr
          ON lr.labroomid = cl.labroomid
        WHERE cl.subject = %s
          AND cl.catalog = %s
    ),
    meetings AS (
        SELECT
            CASE
              WHEN (COALESCE(st.meetingpatternnumber, 1) %% 2) = 0 THEN 2
              ELSE 1
            END AS wk,
            st.classstarttime,
            st.classendtime,
            st.mondays, st.tuesdays, st.wednesdays, st.thursdays, st.fridays,
            st.saturdays, st.sundays
        FROM scheduleterm st
        JOIN allowed_rooms ar
          ON ar.building = st.buildingcode
         AND ar.room     = st.room
    )
    SELECT day, classstarttime AS start_time, classendtime AS end_time
    FROM (
        SELECT ((wk - 1) * 7) + 1 AS day, classstarttime, classendtime FROM meetings WHERE mondays = TRUE
        UNION ALL
        SELECT ((wk - 1) * 7) + 2 AS day, classstarttime, classendtime FROM meetings WHERE tuesdays = TRUE
        UNION ALL
        SELECT ((wk - 1) * 7) + 3 AS day, classstarttime, classendtime FROM meetings WHERE wednesdays = TRUE
        UNION ALL
        SELECT ((wk - 1) * 7) + 4 AS day, classstarttime, classendtime FROM meetings WHERE thursdays = TRUE
        UNION ALL
        SELECT ((wk - 1) * 7) + 5 AS day, classstarttime, classendtime FROM meetings WHERE fridays = TRUE
        UNION ALL
        SELECT ((wk - 1) * 7) + 6 AS day, classstarttime, classendtime FROM meetings WHERE saturdays = TRUE
        UNION ALL
        SELECT ((wk - 1) * 7) + 7 AS day, classstarttime, classendtime FROM meetings WHERE sundays = TRUE
    ) x
    ORDER BY day, start_time;
    """

    cur.execute(sql, (subject, catalog))
    rows = cur.fetchall()

    room_busy: list[TimeBlock] = []
    for day, start_t, end_t in rows:
        room_busy.append(TimeBlock(day=int(day), start=to_minutes(start_t), end=to_minutes(end_t)))

    return room_busy
