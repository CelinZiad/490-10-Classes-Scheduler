from waitlist_algorithm.algorithm.time_block import TimeBlock, to_minutes

def load_room_busy_for_course(cur, subject: str, catalog: str, week1_monday) -> list[TimeBlock]:
    sql = """
    WITH allowed_rooms AS (
      SELECT lr.building, lr.room
      FROM courselabs cl
      JOIN labrooms lr ON lr.labroomid = cl.labroomid
      WHERE cl.subject = %s AND cl.catalog = %s
    ),
    meetings AS (
      SELECT
        st.classstartdate, st.classenddate,
        st.classstarttime, st.classendtime,
        st.mondays, st.tuesdays, st.wednesdays, st.thursdays, st.fridays,
        st.saturdays, st.sundays
      FROM scheduleterm st
      JOIN allowed_rooms ar
        ON ar.building = st.buildingcode
       AND ar.room     = st.room
    ),
    days AS (
      SELECT (%s::date + gs)::date AS d, (gs + 1) AS day_index
      FROM generate_series(0, 13) AS gs
    )
    SELECT
      d.day_index AS day,
      m.classstarttime AS start_time,
      m.classendtime   AS end_time
    FROM meetings m
    JOIN days d
      ON d.d BETWEEN m.classstartdate AND m.classenddate
     AND (
          (extract(isodow from d.d) = 1 AND m.mondays) OR
          (extract(isodow from d.d) = 2 AND m.tuesdays) OR
          (extract(isodow from d.d) = 3 AND m.wednesdays) OR
          (extract(isodow from d.d) = 4 AND m.thursdays) OR
          (extract(isodow from d.d) = 5 AND m.fridays) OR
          (extract(isodow from d.d) = 6 AND m.saturdays) OR
          (extract(isodow from d.d) = 7 AND m.sundays)
        )
    ORDER BY day, start_time;
    """

    cur.execute(sql, (subject, catalog, week1_monday))
    rows = cur.fetchall()



    room_busy: list[TimeBlock] = []
    for day, start_t, end_t in rows:
        room_busy.append(TimeBlock(day=int(day), start=to_minutes(start_t), end=to_minutes(end_t)))

    return room_busy
