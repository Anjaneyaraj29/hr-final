"""CLI utility to add or update employee login credentials."""

import argparse
import os
import sqlite3
from datetime import datetime
from getpass import getpass
from pathlib import Path

import bcrypt
from dotenv import load_dotenv


load_dotenv()


DEFAULT_DB_PATH = Path(__file__).resolve().parent / "src" / "db" / "employee_auth.db"
EMPLOYEE_DB_PATH = Path(os.getenv("EMPLOYEE_DB_PATH", str(DEFAULT_DB_PATH)))


def _get_connection() -> sqlite3.Connection:
    """Return DB connection and ensure parent directory exists."""
    EMPLOYEE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(EMPLOYEE_DB_PATH)


def _hash_password(password: str) -> str:
    """Hash plaintext password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def init_db() -> None:
    """Create employees table if missing."""
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                employee_id TEXT PRIMARY KEY,
                full_name TEXT,
                role TEXT NOT NULL DEFAULT 'Employee',
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def upsert_employee(employee_id: str, password: str, full_name: str, role: str) -> None:
    """Insert new employee or update existing employee password/profile."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    password_hash = _hash_password(password)

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO employees (employee_id, full_name, role, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(employee_id) DO UPDATE SET
                full_name = excluded.full_name,
                role = excluded.role,
                password_hash = excluded.password_hash
            """,
            (employee_id, full_name, role, password_hash, now),
        )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Add or update employee login credentials")
    parser.add_argument("--employee-id", required=True, help="Employee ID used at login")
    parser.add_argument("--full-name", default="", help="Employee full name")
    parser.add_argument("--role", default="Employee", help="Employee role")
    parser.add_argument("--password", default="", help="Password (if omitted, prompt securely)")
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    init_db()

    employee_id = args.employee_id.strip()
    full_name = args.full_name.strip() or employee_id
    role = args.role.strip() or "Employee"

    password = args.password
    if not password:
        password = getpass("Password: ")

    if not employee_id:
        raise ValueError("employee-id cannot be empty")
    if not password:
        raise ValueError("password cannot be empty")

    upsert_employee(employee_id, password, full_name, role)
    print(f"Employee '{employee_id}' saved in {EMPLOYEE_DB_PATH}")


if __name__ == "__main__":
    main()
