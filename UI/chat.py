"""Chat interface for HR Helpdesk."""

import os
import sqlite3
from datetime import datetime
from pathlib import Path

import bcrypt
import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/ask")
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "src" / "db" / "employee_auth.db"
EMPLOYEE_DB_PATH = Path(os.getenv("EMPLOYEE_DB_PATH", str(DEFAULT_DB_PATH)))


def _get_connection() -> sqlite3.Connection:
    """Return a DB connection with dict-like row access."""
    EMPLOYEE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(EMPLOYEE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _parse_seed_credentials(raw: str) -> list[tuple[str, str]]:
    """Parse EMPLOYEE_CREDENTIALS env format username:password,..."""
    credentials: list[tuple[str, str]] = []
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        employee_id, password = pair.split(":", 1)
        employee_id = employee_id.strip()
        password = password.strip()
        if employee_id and password:
            credentials.append((employee_id, password))
    return credentials


def _initialize_employee_auth_db() -> None:
    """Create auth table and seed initial users for first run."""
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

        existing_count = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        if existing_count > 0:
            return

        raw_credentials = os.getenv("EMPLOYEE_CREDENTIALS", "employee:employee123")
        seed_users = _parse_seed_credentials(raw_credentials)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        for employee_id, password in seed_users:
            conn.execute(
                """
                INSERT INTO employees (employee_id, full_name, role, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    employee_id,
                    employee_id,
                    "Employee",
                    _hash_password(password),
                    now,
                ),
            )


def _create_chat_session() -> dict[str, object]:
    """Create a new chat session entry."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return {
        "id": timestamp,
        "title": "New Chat",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "messages": [],
    }


def _initialize_chat_state():
    """Initialize chat-related session state variables."""
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = [_create_chat_session()]
    if "active_chat_id" not in st.session_state:
        st.session_state.active_chat_id = st.session_state.chat_sessions[0]["id"]


def _get_active_chat_session() -> dict[str, object]:
    """Return the currently active chat session."""
    for session in st.session_state.chat_sessions:
        if session["id"] == st.session_state.active_chat_id:
            return session

    # Recover if active chat id no longer exists.
    st.session_state.active_chat_id = st.session_state.chat_sessions[0]["id"]
    return st.session_state.chat_sessions[0]


def _authenticate_employee(employee_id: str, password: str) -> dict[str, str] | None:
    """Validate employee credentials and return profile on success."""
    with _get_connection() as conn:
        row = conn.execute(
            """
            SELECT employee_id, full_name, role, password_hash
            FROM employees
            WHERE employee_id = ?
            """,
            (employee_id,),
        ).fetchone()

    if not row:
        return None

    if not _verify_password(password, row["password_hash"]):
        return None

    return {
        "employee_id": row["employee_id"],
        "full_name": row["full_name"] or row["employee_id"],
        "role": row["role"],
    }


def _render_sidebar(display_name: str):
    """Render the left sidebar with profile and chat history."""
    with st.sidebar:
        st.header("Employee Profile")
        st.write(f"Name: {display_name}")
        st.write(f"Employee ID: {st.session_state.get('employee_id', '')}")
        st.write(f"Role: {st.session_state.get('employee_role', 'Employee')}")
        if st.session_state.get("employee_login_time"):
            st.write(f"Login Time: {st.session_state.employee_login_time}")

        st.divider()
        st.subheader("Chat History")

        if st.button("+ New Chat", use_container_width=True):
            new_session = _create_chat_session()
            st.session_state.chat_sessions.insert(0, new_session)
            st.session_state.active_chat_id = new_session["id"]
            st.rerun()

        for session in st.session_state.chat_sessions:
            title = str(session["title"])
            button_label = f"{title[:35]}" if len(title) > 35 else title
            if st.button(button_label, key=f"chat_{session['id']}", use_container_width=True):
                st.session_state.active_chat_id = session["id"]
                st.rerun()
            st.caption(f"Created: {session['created_at']}")


def show_login():
    """Display employee login form."""
    st.title("Employee Login")
    st.caption("Sign in to access the HR Helpdesk chat.")

    with st.form("employee_login_form", clear_on_submit=False):
        username = st.text_input("Employee ID")
        password = st.text_input("Password", type="password")
        login_clicked = st.form_submit_button("Login")

    if login_clicked:
        profile = _authenticate_employee(username.strip(), password)
        if profile:
            st.session_state.is_authenticated = True
            st.session_state.employee_username = profile["full_name"]
            st.session_state.employee_id = profile["employee_id"]
            st.session_state.employee_role = profile["role"]
            st.session_state.employee_login_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            st.session_state.login_error = ""
            st.rerun()
        else:
            st.session_state.login_error = "Invalid username or password."

    if st.session_state.get("login_error"):
        st.error(st.session_state.login_error)


def show_chat():
    """Display the chat interface."""
    username = st.session_state.get("employee_username", "Employee")
    _initialize_chat_state()
    _render_sidebar(username)

    st.title("HR Helpdesk Agent")
    st.caption(f"Logged in as: {username}")

    if st.button("Logout"):
        st.session_state.is_authenticated = False
        st.session_state.employee_username = ""
        st.session_state.employee_id = ""
        st.session_state.employee_role = ""
        st.session_state.employee_login_time = ""
        st.session_state.chat_sessions = []
        st.session_state.active_chat_id = ""
        st.rerun()

    active_session = _get_active_chat_session()
    messages = active_session["messages"]

    # Display chat history
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    user_input = st.chat_input("Ask your HR question...")

    if user_input:
        # Add user message
        messages.append({"role": "user", "content": user_input})
        if active_session["title"] == "New Chat":
            active_session["title"] = user_input[:50]

        with st.chat_message("user"):
            st.markdown(user_input)

        # Get assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        API_URL,
                        json={"query": user_input},
                        timeout=60,
                    )
                    response.raise_for_status()
                    result = response.json()
                    answer = result.get("answer", "No answer found.")
                except requests.exceptions.RequestException as e:
                    answer = f"Error: Could not connect to server. Is the API running?\n\nDetails: {str(e)}"

            st.markdown(answer)
            messages.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    st.set_page_config(page_title="HR Helpdesk", page_icon="HR")
    _initialize_employee_auth_db()

    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False
    if "employee_username" not in st.session_state:
        st.session_state.employee_username = ""
    if "employee_id" not in st.session_state:
        st.session_state.employee_id = ""
    if "employee_role" not in st.session_state:
        st.session_state.employee_role = ""
    if "login_error" not in st.session_state:
        st.session_state.login_error = ""
    if "employee_login_time" not in st.session_state:
        st.session_state.employee_login_time = ""

    if st.session_state.is_authenticated:
        show_chat()
    else:
        show_login()
