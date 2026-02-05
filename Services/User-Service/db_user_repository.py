import os
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "lastmile")
DB_USER = os.getenv("DB_USER", os.getenv("DB_USER", "postgres"))
DB_PASSWORD = os.getenv("DB_PASSWORD", "Sghu*560")


def _get_connection():
    """Create and return a new PostgreSQL connection for the user service."""
    print(f"Connecting to database: {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER}")
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor,
    )


def create_user(name: str, phone: str, role: str, password: str) -> Optional[int]:
    """Insert a new user into the users table and return generated user_id."""

    insert_sql = """
        INSERT INTO users (name, phone, role, password)
        VALUES (%s, %s, %s, %s)
        RETURNING user_id;
    """

    conn = None
    try:
        conn = _get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(insert_sql, (name, phone, role, password))
                row = cur.fetchone()
                if not row:
                    return None
                return int(row["user_id"])
    finally:
        if conn is not None:
            conn.close()


def get_user_by_phone(phone: str) -> Optional[dict]:
    """Fetch a single user row by phone number."""

    select_sql = "SELECT user_id, name, phone, role, password FROM users WHERE phone = %s;"

    conn = None
    try:
        conn = _get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(select_sql, (phone,))
                row = cur.fetchone()
                return row
    finally:
        if conn is not None:
            conn.close()
