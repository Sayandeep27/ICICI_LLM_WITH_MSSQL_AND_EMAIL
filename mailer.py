# mailer.py
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

# Default SMTP settings for Gmail. Change if you use another SMTP provider.
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))  # use 465 for SSL, 587 for STARTTLS

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_PASSWORD")  # your Gmail app password

if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
    # don't raise at import time, but it's useful to know early in logs
    # callers will see the detailed error if they try to send
    pass


def send_email(to_address: str, subject: str, body: str, html: str = None, from_address: str = None):
    """
    Send an email.

    Parameters:
      - to_address (str): recipient email address (string like 'Name <addr>' or 'addr')
      - subject (str): subject string
      - body (str): plain-text body
      - html (str): optional html body (if provided, the email will be multipart/alternative)
      - from_address (str): optional from (defaults to EMAIL_ADDRESS)

    Raises:
      - ValueError if environment/missing args
      - smtplib.SMTPException / other exceptions from smtplib on failure
    """
    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        raise ValueError("Missing EMAIL_ADDRESS or EMAIL_PASSWORD in environment")

    if not to_address:
        raise ValueError("Missing to_address")

    if not subject:
        subject = "(no subject)"

    if from_address is None:
        from_address = EMAIL_ADDRESS

    # build EmailMessage
    msg = EmailMessage()
    msg["From"] = from_address
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body or "")

    if html:
        msg.add_alternative(html, subtype="html")

    # connect and send
    try:
        # Using STARTTLS (port 587)
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
        server.ehlo()
        if SMTP_PORT == 587:
            server.starttls()
            server.ehlo()

        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email sent to {to_address} (subject: {subject})")
        return True
    except Exception as e:
        # raise to caller so app.py can respond with JSON error message
        raise e
