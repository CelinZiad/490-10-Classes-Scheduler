import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    dbname = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    return psycopg.connect(
        host = host,
        port = port,
        dbname = dbname,
        user = user,
        password = password,
    )

