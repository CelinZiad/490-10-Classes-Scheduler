from waitlist_algorithm.algorithm.time_block import TimeBlock,to_minutes


def load_students_busy_from_db(cur, studyids: list[int]) -> dict[int, list[TimeBlock]]:
    if not studyids:
        return {}

    sql = """
    WITH sched AS (
      SELECT ss.studyid, ss.studentscheduleid
      FROM studentschedule ss
      WHERE ss.studyid = ANY(%s)
    ),
    meetings AS (
      SELECT
          s.studyid,
          CASE
            WHEN (COALESCE(st.meetingpatternnumber, 1) %% 2) = 0 THEN 2
            ELSE 1
          END AS wk,
          st.classstarttime,
          st.classendtime,
          st.mondays, st.tuesdays, st.wednesdays, st.thursdays, st.fridays,
          st.saturdays, st.sundays
      FROM sched s
      JOIN studentscheduleclass ssc
        ON ssc.studentscheduleid = s.studentscheduleid
      JOIN scheduleterm st
        ON st.cid = ssc.cid
    )
    SELECT studyid, day, classstarttime AS start_time, classendtime AS end_time
    FROM (
      SELECT studyid, ((wk - 1) * 7) + 1 AS day, classstarttime, classendtime FROM meetings WHERE mondays = TRUE
      UNION ALL
      SELECT studyid, ((wk - 1) * 7) + 2 AS day, classstarttime, classendtime FROM meetings WHERE tuesdays = TRUE
      UNION ALL
      SELECT studyid, ((wk - 1) * 7) + 3 AS day, classstarttime, classendtime FROM meetings WHERE wednesdays = TRUE
      UNION ALL
      SELECT studyid, ((wk - 1) * 7) + 4 AS day, classstarttime, classendtime FROM meetings WHERE thursdays = TRUE
      UNION ALL
      SELECT studyid, ((wk - 1) * 7) + 5 AS day, classstarttime, classendtime FROM meetings WHERE fridays = TRUE
      UNION ALL
      SELECT studyid, ((wk - 1) * 7) + 6 AS day, classstarttime, classendtime FROM meetings WHERE saturdays = TRUE
      UNION ALL
      SELECT studyid, ((wk - 1) * 7) + 7 AS day, classstarttime, classendtime FROM meetings WHERE sundays = TRUE
    ) x
    ORDER BY studyid, day, start_time;
    """

    cur.execute(sql, (studyids,))
    rows = cur.fetchall()

    students_busy: dict[int, list[TimeBlock]] = {}
    for studyid, day, start_t, end_t in rows:
        students_busy.setdefault(studyid, []).append(
            TimeBlock(day=int(day), start=to_minutes(start_t), end=to_minutes(end_t))
        )

    return students_busy

