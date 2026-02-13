

def prompt_waitlisted_studyids():
    raw = input("Enter waitlisted studyid(s) (comma-separated): ").strip()
    if not raw:
        return []


    parts = raw.replace(" ", ",").split(",")
    ids = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if not p.isdigit():
            raise ValueError(f"Invalid id '{p}'. Use only integers like 5001,5002.")
        ids.append(int(p))


    seen = set()
    out = []
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
    found = [row[0] for row in cur.fetchall()]
    return found


def get_waitlisted_students_from_user_and_db(cur) -> list[int]:
    requested = prompt_waitlisted_studyids()
    found = fetch_existing_studyids(cur, requested)

    missing = sorted(set(requested) - set(found))
    if missing:
        print(f"Warning: these studyid(s) do not exist in studentschedulestudy and will be ignored: {missing}")

    if not found:
        print("No valid waitlisted studyids entered.")
    else:
        print(f"Using waitlisted studyid(s): {found}")

    return found
