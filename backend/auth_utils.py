from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from datetime import datetime
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

load_dotenv()

# ================= JWT CONFIG ================= #
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
oauth2 = OAuth2PasswordBearer(tokenUrl="login")

# ================= MONGO ================= #
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_APP")]
users = db["user"]

# ================= AUTH HELPERS ================= #
def get_current_user(token: str = Depends(oauth2)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub") or payload.get("username")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def require_role(user, allowed_roles: list):
    role = user.get("role")
    if role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Required role(s): {allowed_roles}"
        )


# ================= EMAIL CONFIG ================= #
# Gmail SMTP (Correct)
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM") or MAIL_USERNAME
MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() in ("1", "true", "yes")


def _sync_send_email(subject: str, recipients: list, body: str):
    if not MAIL_USERNAME or not MAIL_PASSWORD or not MAIL_FROM:
        raise RuntimeError("SMTP credentials not configured (MAIL_USERNAME/MAIL_PASSWORD/MAIL_FROM)")

    msg = MIMEMultipart()
    msg["From"] = MAIL_FROM
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = Header(subject, 'utf-8')
    msg.attach(MIMEText(body, "html", "utf-8"))

    # connect and send
    server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10)
    try:
        if MAIL_USE_TLS:
            server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.sendmail(MAIL_FROM, recipients, msg.as_string())
    finally:
        try:
            server.quit()
        except Exception:
            pass


async def send_email(subject: str, recipients: list, body: str):
    """
    Send an HTML email using configured SMTP. This runs the blocking SMTP call in a thread.
    Raises RuntimeError on missing config or smtplib.SMTPException on send errors.
    """
    return await asyncio.to_thread(_sync_send_email, subject, recipients, body)
