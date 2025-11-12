import os
import imaplib
import email
from dotenv import load_dotenv
from email.header import decode_header
from db_writer import insert_project
from llm_groq_extractor import extract_task_info

load_dotenv()

EMAIL = os.getenv("EMAIL_ADDRESS")
PASSWORD = os.getenv("EMAIL_PASSWORD")
SERVER = os.getenv("IMAP_SERVER")
PORT = int(os.getenv("IMAP_PORT"))
UID_FILE = "last_uid.txt"

def get_last_uid():
    if os.path.exists(UID_FILE):
        with open(UID_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_uid(uid):
    with open(UID_FILE, "w") as f:
        f.write(str(uid))

def clean_subject(s):
    try:
        subject, encoding = decode_header(s)[0]
        if isinstance(subject, bytes):
            return subject.decode(encoding or "utf-8", errors="ignore")
        return subject
    except:
        return s

def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(errors="ignore")
    else:
        return msg.get_payload(decode=True).decode(errors="ignore")
    return ""

def read_inbox():
    mail = imaplib.IMAP4_SSL(SERVER, PORT)
    mail.login(EMAIL, PASSWORD)
    mail.select("inbox")

    last_uid = get_last_uid()
    if last_uid:
        search_criteria = f"(UID {int(last_uid)+1}:*)"
    else:
        import datetime
        today = datetime.date.today().strftime("%d-%b-%Y")
        search_criteria = f'(SINCE {today})'

    status, data = mail.uid("search", None, search_criteria)
    email_uids = data[0].split()

    print(f"Found {len(email_uids)} truly new emails")

    for e_uid in email_uids:
        result, email_data = mail.uid("fetch", e_uid, "(RFC822)")
        raw_email = email_data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = clean_subject(msg["Subject"])
        from_email = msg.get("From")
        body = get_body(msg)

        print(f"\n[NEW EMAIL] From: {from_email}\nSubject: {subject}")

        try:
            task_data = extract_task_info(subject, body)
            task_data["owner_email"] = from_email
            insert_project(task_data)
        except Exception as e:
            print("Error inserting project:", e)

        # Save last processed UID
        save_last_uid(e_uid.decode())

    mail.logout()

if __name__ == "__main__":
    read_inbox()
