from mysql.connector import pooling
from typing import Any

import os
import threading


_pool: pooling.MySQLConnectionPool | None = None
_pool_lock = threading.Lock()


def _get_pool() -> pooling.MySQLConnectionPool:
    """Creates the connection pool on first use.

    Connection parameters are read from the environment (DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME).
    If any of them are missing, Docker-friendly MMT defaults are used.
    A pool is used instead of a single shared connection, as requests are handled in parallel threads.
    """
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = pooling.MySQLConnectionPool(
                pool_name="mmt_ai",
                pool_size=int(os.getenv("DB_POOL_SIZE", 5)),
                pool_reset_session=True,
                host=os.getenv("DB_HOST", "mariadb"),
                port=int(os.getenv("DB_PORT", "3306")),
                user=os.getenv("DB_USER", "my_app"),
                password=os.getenv("DB_PASS", "secret"),
                database=os.getenv("DB_NAME", "my_app"),
            )
        return _pool


def fetch_all(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Executes a SELECT query and returns the rows as dictionaries."""
    conn = _get_pool().get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        return rows
    finally:
        conn.close()


def execute(sql: str, params: tuple = ()) -> int:
    """Executes a statement that changes the database and commits it. Returns the number of affected rows."""
    conn = _get_pool().get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        count = cursor.rowcount
        cursor.close()
        return count
    finally:
        conn.close()


def run_script(sql: str) -> None:
    """Executes several semicolon-separated statements, e.g. a migration file."""
    for statement in (part.strip() for part in sql.split(";")):
        if statement:
            execute(statement)
