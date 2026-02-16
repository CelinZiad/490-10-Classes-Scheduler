def prompt_waitlisted_studyids() -> list[int]:
    raw = input("Enter waitlisted studyid(s) (comma-separated): ").strip()
    if not raw:
        return []

    parts = raw.replace(" ", ",").split(",")
    ids: list[int] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if not p.isdigit():
            raise ValueError(f"Invalid id '{p}'. Use only integers like 5001,5002.")
        ids.append(int(p))


    seen = set()
    out: list[int] = []
    for x in ids:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def fetch_existing_studyids(cur, requested_ids: list[int]) -> list[int]:
    if not requested_ids:
        return []

    cur.execute(
        """
        SELECT studyid
        FROM studentschedulestudy
        WHERE studyid = ANY(%s)
        """,
        (requested_ids,)
    )
    return [row[0] for row in cur.fetchall()]


def prompt_target_course() -> tuple[str, str]:

    raw = input("Enter target course (e.g., COEN 243): ").strip()
    if not raw:
        raise ValueError("You must enter a course like 'COEN 243'.")


    parts = raw.replace(",", " ").split()
    if len(parts) != 2:
        raise ValueError("Invalid format. Use: COEN 243")

    subject = parts[0].upper()
    catalog = parts[1]
    return subject, catalog


def course_exists(cur, subject: str, catalog: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM sequencecourse
        WHERE subject = %s AND catalog = %s
        LIMIT 1
        """,
        (subject, catalog),
    )
    return cur.fetchone() is not None


def get_waitlisted_students_and_course_from_user(cur) -> tuple[list[int], tuple[str, str]]:

    requested = prompt_waitlisted_studyids()
    found = fetch_existing_studyids(cur, requested)

    missing = sorted(set(requested) - set(found))
    if missing:
        print(f"Warning: these studyid(s) do not exist in studentschedulestudy and will be ignored: {missing}")

    if not found:
        print("No valid waitlisted studyids entered.")
    else:
        print(f"Using waitlisted studyid(s): {found}")


    subject, catalog = prompt_target_course()
    if not course_exists(cur, subject, catalog):
        print(f"Warning: course {subject} {catalog} not found in sequencecourse (check spelling/case).")
    else:
        print(f"Target course: {subject} {catalog}")

    return found, (subject, catalog)