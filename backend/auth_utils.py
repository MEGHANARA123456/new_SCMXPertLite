from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from datetime import datetime
import os
from dotenv import load_dotenv
from pymongo import MongoClient
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
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT")),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),

    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS") == "True",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS") == "True",

    USE_CREDENTIALS=True
)

# ================= SEND EMAIL HELPERS ================= #
async def send_email(subject: str, recipients: list, body: str):
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=body,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)
