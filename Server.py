import socket
import threading
import json
import traceback
import logging
import os

from db import setup
from auth import register, login, list_doctors
from files import (
    create_group,
    save_file_to_group,
    get_patient_groups,
    get_doctor_groups,
    get_group_files,
    load_file,
    add_group_comment,
    get_comments_for_patient,
    get_comments_for_group
)

HOST = "0.0.0.0"
PORT = 5555
MAX_MESSAGE_SIZE = 200_000_000

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename=os.path.join("logs", "server.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("medisecond.server")

def send_msg(client, data: dict):
    raw = json.dumps(data).encode("utf-8")
    client.sendall(len(raw).to_bytes(4, "big") + raw)

def recv_exact(sock, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            return b""
        data += chunk
    return data

def recv_msg(client):
    length_bytes = recv_exact(client, 4)
    if not length_bytes:
        return None
    size = int.from_bytes(length_bytes, "big")
    if size <= 0 or size > MAX_MESSAGE_SIZE:
        raise ValueError(f"Invalid message size: {size}")
    payload = recv_exact(client, size)
    if not payload:
        return None
    return json.loads(payload.decode("utf-8"))

def require_fields(req, fields):
    missing = [field for field in fields if field not in req]
    if missing:
        raise ValueError("Missing required fields: " + ", ".join(missing))

def handle_client(client, addr=None):
    try:
        req = recv_msg(client)
        if req is None:
            logger.info("Client disconnected before sending data: %s", addr)
            return

        action = req.get("action")
        logger.info("Request from %s: %s", addr, action)

        if action == "register":
            require_fields(req, ["user", "pass", "role"])
            ok = register(req["user"], req["pass"], req["role"])
            send_msg(client, {"ok": ok, "error": None if ok else "Username already exists or invalid role"})

        elif action == "login":
            require_fields(req, ["user", "pass"])
            role = login(req["user"], req["pass"])
            send_msg(client, {"ok": role is not None, "role": role, "error": None if role else "Invalid username or password"})

        elif action == "list_doctors":
            send_msg(client, {"ok": True, "doctors": list_doctors()})

        elif action == "upload_group":
            require_fields(req, ["owner", "doctor", "files"])
            owner = req["owner"]
            doctor = req["doctor"].strip()
            uploaded_files = req["files"]

            if doctor not in list_doctors():
                logger.warning("Upload denied: doctor does not exist: %s", doctor)
                send_msg(client, {"ok": False, "error": "Doctor does not exist"})
                return

            if not uploaded_files:
                send_msg(client, {"ok": False, "error": "No files were selected"})
                return

            group_id = create_group(owner, doctor)
            saved_count = 0
            for file_item in uploaded_files:
                if save_file_to_group(group_id, file_item.get("filename", "unnamed_file"), file_item.get("data", ""), owner, doctor):
                    saved_count += 1

            if saved_count == 0:
                send_msg(client, {"ok": False, "error": "No files could be saved"})
                return

            logger.info("Upload completed: group=%s owner=%s doctor=%s files=%s", group_id, owner, doctor, saved_count)
            send_msg(client, {"ok": True, "group_id": group_id, "saved_files": saved_count})

        elif action == "patient_groups":
            require_fields(req, ["owner"])
            send_msg(client, {"ok": True, "groups": get_patient_groups(req["owner"])})

        elif action == "doctor_groups":
            require_fields(req, ["doctor"])
            send_msg(client, {"ok": True, "groups": get_doctor_groups(req["doctor"])})

        elif action == "group_files":
            require_fields(req, ["group_id"])
            send_msg(client, {"ok": True, "files": get_group_files(req["group_id"])})

        elif action == "download":
            require_fields(req, ["file_id"])
            file_data = load_file(req["file_id"])
            send_msg(client, {"ok": file_data is not None, "file": file_data, "error": None if file_data else "File not found"})

        elif action == "comment_group":
            require_fields(req, ["group_id", "doctor", "comment"])
            ok = add_group_comment(req["group_id"], req["doctor"], req["comment"])
            send_msg(client, {"ok": ok, "error": None if ok else "Empty comment"})

        elif action == "group_comments":
            require_fields(req, ["group_id"])
            send_msg(client, {"ok": True, "comments": get_comments_for_group(req["group_id"])})

        elif action == "patient_comments":
            require_fields(req, ["owner"])
            send_msg(client, {"ok": True, "comments": get_comments_for_patient(req["owner"])})

        else:
            send_msg(client, {"ok": False, "error": f"Unknown action: {action}"})

    except Exception as e:
        logger.exception("Server error for %s: %s", addr, e)
        print("\n===== SERVER ERROR =====")
        print("Client:", addr)
        print("Error:", e)
        traceback.print_exc()
        print("========================\n")
        try:
            send_msg(client, {"ok": False, "error": str(e)})
        except Exception:
            pass
    finally:
        client.close()

def start_server():
    setup()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(20)
    logger.info("Server running on %s:%s", HOST, PORT)
    print(f"Server running on {HOST}:{PORT}")

    while True:
        client, addr = server.accept()
        logger.info("Connected: %s", addr)
        print("Connected:", addr)
        threading.Thread(target=handle_client, args=(client, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()
