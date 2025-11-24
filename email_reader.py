# email_reader.py
import os
import imaplib
import email
from email.header import decode_header
from dotenv import load_dotenv
from llm_groq_extractor import extract_task_info, extract_status_update
from db_writer import insert_project, update_task_status, insert_project_update

load_dotenv()

EMAIL = os.getenv("EMAIL_ADDRESS")
PASSWORD = os.getenv("EMAIL_PASSWORD")
SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
PORT = int(os.getenv("IMAP_PORT", 993))

UID_FILE = "last_uid.txt"

def get_last_uid():
    if os.path.exists(UID_FILE):
        try:
            with open(UID_FILE, "r") as f:
                return int(f.read().strip())
        except:
            return 0
    return 0

def save_last_uid(uid):
    try:
        with open(UID_FILE, "w") as f:
            f.write(str(uid))
    except:
        pass

def clean_subject(raw):
    try:
        subject, enc = decode_header(raw)[0]
        if isinstance(subject, bytes):
            return subject.decode(enc or "utf-8", errors="ignore")
        return subject
    except:
        return raw or ""

def get_body(msg):
    try:
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == "text/plain":
                    try:
                        return part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    except:
                        pass
                if ctype == "text/html" and not part.get_content_maintype() == 'multipart':
                    try:
                        return part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    except:
                        pass
        else:
            content = msg.get_payload(decode=True)
            if content:
                return content.decode("utf-8", errors="ignore")
    except Exception:
        pass
    return ""

def read_inbox():
    last_uid = get_last_uid()
    print(f"\nLast processed UID = {last_uid}")

    mail = imaplib.IMAP4_SSL(SERVER, PORT)
    mail.login(EMAIL, PASSWORD)
    mail.select("inbox")

    search_criteria = f"(UID {last_uid + 1}:*)"
    status, data = mail.uid("search", None, search_criteria)
    new_uids = data[0].split() if data and data[0] else []
    print(f"\n=== Found {len(new_uids)} new emails ===\n")

    for uid in new_uids:
        try:
            _, msg_data = mail.uid("fetch", uid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
        except Exception as e:
            print("Failed to fetch message:", e)
            save_last_uid(int(uid))
            continue

        subject = clean_subject(msg.get("Subject", ""))
        sender = msg.get("From", "")
        body = get_body(msg)

        print(f"[EMAIL] From: {sender}\nSubject: {subject}")

        # 1) Check status-update first
        try:
            status_info = extract_status_update(subject, body)
        except Exception as e:
            print("Status extraction error:", e)
            status_info = {"is_status_update": False, "task_id": None, "new_status": None}

        if status_info.get("is_status_update"):
            tid = status_info.get("task_id")
            new_status = status_info.get("new_status")
            # insert the message into updates table for visibility
            try:
                if tid:
                    insert_project_update(project_id=tid, update_message=f"Sender update: {subject}\n\n{body}", from_email=sender, update_type="sender")
                if tid and new_status == "resolved":
                    update_task_status(tid, "resolved")
                    print(f"✅ Marked task {tid} resolved (from incoming sender email)")
                else:
                    print("ℹ Status update found but not marked resolved (no resolved keyword)")
            except Exception as e:
                print("Error handling status update:", e)
            save_last_uid(int(uid))
            continue

        # 2) Otherwise treat as normal incoming request -> create project
        try:
            extracted = extract_task_info(subject, body)
            extracted["owner_email"] = sender
            insert_project(extracted)
        except Exception as e:
            print("Error inserting project:", e)

        save_last_uid(int(uid))

    mail.logout()

if __name__ == "__main__":
    read_inbox()
