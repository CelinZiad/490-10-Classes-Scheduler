import os
from waitlist_algorithm.db import get_conn

def main():
    print("Starting DB check...")
    print("PGHOST =", os.getenv("PGHOST"))
    print("PGPORT =", os.getenv("PGPORT"))
    print("PGDATABASE =", os.getenv("PGDATABASE"))
    print("PGUSER =", os.getenv("PGUSER"))
    # Don't print password

    try:
        print("Connecting...")
        conn = get_conn()
        print("Connected!")

        with conn:
            with conn.cursor() as cur:
                print("Running query...")
                cur.execute("SELECT 1;")
                row = cur.fetchone()
                print("Result:", row)

        print("Done.")
    except Exception as e:
        print("ERROR:", repr(e))

if __name__ == "__main__":
    main()
