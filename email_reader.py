import os
import imaplib
import email
from email.header import decode_header
from dotenv import load_dotenv

from llm_groq_extractor import extract_task_info, extract_status_update
from db_writer import insert_project, update_task_status

load_dotenv()

# pending,resolved is working properly

EMAIL = os.getenv("EMAIL_ADDRESS")
PASSWORD = os.getenv("EMAIL_PASSWORD")
SERVER = os.getenv("IMAP_SERVER")
PORT = int(os.getenv("IMAP_PORT"))

UID_FILE = "last_uid.txt"


# --------------------------------------------
# UID LOAD / SAVE
# --------------------------------------------
def get_last_uid():
    if os.path.exists(UID_FILE):
        with open(UID_FILE, "r") as f:
            return int(f.read().strip())
    return 0


def save_last_uid(uid):
    with open(UID_FILE, "w") as f:
        f.write(str(uid))


# --------------------------------------------
# SAFE SUBJECT
# --------------------------------------------
def clean_subject(raw):
    try:
        subject, enc = decode_header(raw)[0]
        if isinstance(subject, bytes):
            return subject.decode(enc or "utf-8", errors="ignore")
        return subject
    except:
        return raw or ""


# --------------------------------------------
# SAFE BODY
# --------------------------------------------
def get_body(msg):
    try:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        return part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    except:
                        pass
                if part.get_content_type() == "text/html":
                    try:
                        return part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    except:
                        pass
        else:
            content = msg.get_payload(decode=True)
            if content:
                return content.decode("utf-8", errors="ignore")

    except:
        pass

    return ""


# --------------------------------------------
# MAIN READER — UID ONLY (RELIABLE)
# --------------------------------------------
def read_inbox():

    last_uid = get_last_uid()
    print(f"\nLast processed UID = {last_uid}")

    mail = imaplib.IMAP4_SSL(SERVER, PORT)
    mail.login(EMAIL, PASSWORD)
    mail.select("inbox")

    # Fetch ALL UIDs greater than last_uid
    search_criteria = f"(UID {last_uid + 1}:*)"
    _, data = mail.uid("search", None, search_criteria)
    new_uids = [uid for uid in data[0].split()]

    print(f"\n=== Found {len(new_uids)} new emails based on UID ===\n")

    for uid in new_uids:

        _, msg_data = mail.uid("fetch", uid, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        subject = clean_subject(msg.get("Subject", ""))
        sender = msg.get("From", "")
        body = get_body(msg)

        print(f"[EMAIL] From {sender} → {subject}")

        # -------------------------
        # 1. STATUS UPDATE CHECK
        # -------------------------
        status_info = extract_status_update(subject, body)

        if status_info["is_status_update"]:
            tid = status_info["task_id"]
            new_status = status_info["new_status"]

            print(f"🔍 Status update detected for Task {tid}")

            if tid and new_status == "resolved":
                update_task_status(tid, "resolved")
                print(f"✅ Task {tid} marked resolved")
            else:
                print("ℹ Status unchanged")

            save_last_uid(int(uid))
            continue

        # -------------------------
        # 2. REGULAR PROJECT CREATE
        # -------------------------
        data = extract_task_info(subject, body)
        data["owner_email"] = sender

        insert_project(data)

        save_last_uid(int(uid))

    mail.logout()


if __name__ == "__main__":
    read_inbox()
