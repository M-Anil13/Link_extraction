import os
import smtplib
import ssl
from email.message import EmailMessage

# Gmail SMTP. Set SMTP_USER = your gmail, SMTP_PASS = a Gmail App Password
# (Google Account -> Security -> App passwords; NOT your normal password).
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)


def send_email(to, subject, body):
    """Send a plain-text email. Returns True on success. Never raises."""
    if not SMTP_USER or not SMTP_PASS:
        print("SMTP not configured (set SMTP_USER / SMTP_PASS)")
        return False
    try:
        msg = EmailMessage()
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as s:
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        return True
    except Exception as e:
        print("send_email failed:", repr(e))
        return False
