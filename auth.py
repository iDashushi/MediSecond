import hashlib
import logging
from db import connect

logger = logging.getLogger("medisecond.auth")

def hash_pass(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def register(username: str, password: str, role: str) -> bool:
    username = username.strip()
    role = role.strip().lower()
    if not username or not password or role not in ("patient", "doctor"):
        return False
    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, hash_pass(password), role)
        )
        conn.commit()
        logger.info("Registered %s: %s", role, username)
        return True
    except Exception as e:
        logger.warning("Registration failed for %s: %s", username, e)
        return False
    finally:
        conn.close()

def login(username: str, password: str):
    username = username.strip()
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT role FROM users WHERE username=? AND password=?",
        (username, hash_pass(password))
    )
    row = cur.fetchone()
    conn.close()
    if row:
        logger.info("Login successful: %s", username)
        return row[0]
    logger.warning("Login failed: %s", username)
    return None

def list_doctors():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE role='doctor' ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]
