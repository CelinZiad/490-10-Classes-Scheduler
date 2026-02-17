from waitlist_algorithm.algorithm.time_block import TimeBlock, to_minutes



def get_two_week_anchor_monday(cur, studyids: list[int]):
    sql = """
    WITH sched AS (
      SELECT ss.studentscheduleid
      FROM studentschedule ss
      WHERE ss.studyid = ANY(%s)
    )
    SELECT date_trunc('week',
             COALESCE(
               MIN(st.classstartdate) FILTER (WHERE st.componentcode <> 'LAB'),
               MIN(st.classstartdate)
             )
           )::date AS week1_monday
    FROM sched s
    JOIN studentscheduleclass ssc ON ssc.studentscheduleid = s.studentscheduleid
    JOIN scheduleterm st ON st.cid = ssc.cid;
    """
    cur.execute(sql, (studyids,))
    (week1_monday,) = cur.fetchone()
    return week1_monday



def load_students_busy_from_db(cur, studyids: list[int]) -> dict[int, list[TimeBlock]]:
    if not studyids:
        return {}

    week1_monday = get_two_week_anchor_monday(cur, studyids)


    sql = """
    WITH sched AS (
      SELECT ss.studyid, ss.studentscheduleid
      FROM studentschedule ss
      WHERE ss.studyid = ANY(%s)
    ),
    classes AS (
      SELECT
        s.studyid,
        st.componentcode,
        st.classstartdate, st.classenddate,
        st.classstarttime, st.classendtime,
        st.mondays, st.tuesdays, st.wednesdays, st.thursdays, st.fridays,
        st.saturdays, st.sundays
      FROM sched s
      JOIN studentscheduleclass ssc ON ssc.studentscheduleid = s.studentscheduleid
      JOIN scheduleterm st ON st.cid = ssc.cid
      WHERE NOT (st.classstarttime = TIME '00:00' AND st.classendtime = TIME '00:00')
    ),
    days AS (
      SELECT (%s::date + gs)::date AS d, (gs + 1) AS day_index
      FROM generate_series(0, 13) AS gs
    )
    SELECT
      c.studyid,
      c.componentcode,
      c.classstartdate,
      d.day_index AS day,
      c.classstarttime AS start_time,
      c.classendtime   AS end_time
    FROM classes c
    JOIN days d
      ON d.d BETWEEN c.classstartdate AND c.classenddate
     AND (
          (extract(isodow from d.d) = 1 AND c.mondays) OR
          (extract(isodow from d.d) = 2 AND c.tuesdays) OR
          (extract(isodow from d.d) = 3 AND c.wednesdays) OR
          (extract(isodow from d.d) = 4 AND c.thursdays) OR
          (extract(isodow from d.d) = 5 AND c.fridays) OR
          (extract(isodow from d.d) = 6 AND c.saturdays) OR
          (extract(isodow from d.d) = 7 AND c.sundays)
        )
    ORDER BY c.studyid, day, start_time;
    """

    cur.execute(sql, (studyids, week1_monday))
    rows = cur.fetchall()



    students_busy: dict[int, list[TimeBlock]] = {}
    lab_week: dict[int, int] = {}
    min_lab_date = None


    for studyid, comp, startdate, day, start_t, end_t in rows:
        if comp == "LAB":
            if min_lab_date is None or startdate < min_lab_date:
                min_lab_date = startdate


    if min_lab_date is not None:
        for studyid, comp, startdate, day, start_t, end_t in rows:
            if comp == "LAB":
                lab_week[studyid] = 1 if startdate == min_lab_date else 2


    for studyid, comp, startdate, day, start_t, end_t in rows:


        if comp == "LAB":
            wk = lab_week.get(studyid)
            if wk == 1 and day > 7:
                continue
            if wk == 2 and day <= 7:
                continue

        students_busy.setdefault(studyid, []).append(
            TimeBlock(
                day=int(day),
                start=to_minutes(start_t),
                end=to_minutes(end_t)
            )
        )

    return students_busy
