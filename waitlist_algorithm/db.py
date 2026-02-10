import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    host = os.getenv("PGHOST")
    port = os.getenv("PGPORT")
    dbname = os.getenv("PGNAME")
    user = os.getenv("PGUSER")
    password = os.getenv("PGPASSWORD")

    return psycopg.connect(
        host = host,
        port = port,
        dbname = dbname,
        user = user,
        password = password,
    )

