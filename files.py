import os
import base64
import logging
from db import connect

BASE_DIR = "storage"
logger = logging.getLogger("medisecond.files")

def ensure_storage():
    os.makedirs(BASE_DIR, exist_ok=True)

def safe_folder_name(value: str) -> str:
    value = os.path.basename(str(value).strip())
    return "".join(ch for ch in value if ch.isalnum() or ch in ("_", "-", ".")) or "user"

def create_group(owner: str, doctor: str) -> int:
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO file_groups (owner, doctor) VALUES (?, ?)", (owner, doctor))
    group_id = cur.lastrowid
    conn.commit()
    conn.close()
    logger.info("Created group %s: owner=%s doctor=%s", group_id, owner, doctor)
    return group_id

def save_file_to_group(group_id: int, filename: str, data_b64: str, owner: str, doctor: str) -> bool:
    ensure_storage()
    safe_name = os.path.basename(filename)
    safe_owner = safe_folder_name(owner)
    group_dir = os.path.join(BASE_DIR, safe_owner, f"group_{group_id}")
    os.makedirs(group_dir, exist_ok=True)
    filepath = os.path.join(group_dir, safe_name)

    try:
        file_bytes = base64.b64decode(data_b64.encode("utf-8"), validate=True)
    except Exception as e:
        logger.error("Invalid Base64 data for %s: %s", safe_name, e)
        return False

    with open(filepath, "wb") as f:
        f.write(file_bytes)

    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO files (group_id, filename, owner, doctor, filepath) VALUES (?, ?, ?, ?, ?)",
        (group_id, safe_name, owner, doctor, filepath)
    )
    conn.commit()
    conn.close()
    logger.info("Saved file: group=%s filename=%s", group_id, safe_name)
    return True

def get_patient_groups(owner: str):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT fg.id, fg.owner, fg.doctor, fg.created_at, COUNT(f.id)
        FROM file_groups fg
        LEFT JOIN files f ON fg.id = f.group_id
        WHERE fg.owner = ?
        GROUP BY fg.id
        ORDER BY fg.id DESC
    """, (owner,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_doctor_groups(doctor: str):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT fg.id, fg.owner, fg.doctor, fg.created_at, COUNT(f.id)
        FROM file_groups fg
        LEFT JOIN files f ON fg.id = f.group_id
        WHERE fg.doctor = ?
        GROUP BY fg.id
        ORDER BY fg.id DESC
    """, (doctor,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_group_files(group_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, filename, owner, doctor, filepath
        FROM files
        WHERE group_id = ?
        ORDER BY id
    """, (group_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def load_file(file_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, group_id, filename, owner, doctor, filepath
        FROM files
        WHERE id = ?
    """, (file_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        logger.warning("File id not found: %s", file_id)
        return None

    file_id, group_id, filename, owner, doctor, filepath = row
    if not os.path.exists(filepath):
        logger.warning("File path missing: %s", filepath)
        return None

    with open(filepath, "rb") as f:
        data_b64 = base64.b64encode(f.read()).decode("utf-8")

    return {"id": file_id, "group_id": group_id, "filename": filename, "owner": owner, "doctor": doctor, "data": data_b64}

def add_group_comment(group_id: int, doctor: str, comment: str) -> bool:
    comment = comment.strip()
    if not comment:
        return False
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO comments (group_id, doctor, comment) VALUES (?, ?, ?)", (group_id, doctor, comment))
    conn.commit()
    conn.close()
    logger.info("Comment saved: group=%s doctor=%s", group_id, doctor)
    return True

def get_comments_for_patient(owner: str):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT fg.id, fg.created_at, c.doctor, c.comment
        FROM comments c
        JOIN file_groups fg ON c.group_id = fg.id
        WHERE fg.owner = ?
        ORDER BY c.id DESC
    """, (owner,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_comments_for_group(group_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT doctor, comment, created_at
        FROM comments
        WHERE group_id = ?
        ORDER BY id DESC
    """, (group_id,))
    rows = cur.fetchall()
    conn.close()
    return rows
