from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from pymongo import MongoClient
import os
import random
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from backend.user import pbkdf2_hash
load_dotenv()

router = APIRouter()

# Mongo
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_APP")]  # use your app DB
users_col = db["user"]
otp_col = db["otp_store"]

# Email config
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = int(os.getenv("MAIL_PORT"))

# Payload models
class ForgotPass(BaseModel):
    email: str

class VerifyOTP(BaseModel):
    email: str
    otp: str

class ResetPassword(BaseModel):
    email: str
    new_password: str


def send_email(to_email: str, subject: str, body: str):
    print("DEBUG SEND EMAIL:", MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM
    msg["To"] = to_email

    try:
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_FROM, to_email, msg.as_string())
    except Exception as e:
        print("EMAIL ERROR:", e)
        raise HTTPException(status_code=500, detail="Failed to send email")



# 1 SEND OTP
@router.post("/forgot-password")
def forgot_password(data: ForgotPass):
    email = data.email.lower()

    # case-insensitive search
    user = users_col.find_one({"email": {"$regex": f"^{email}$", "$options": "i"}})

    if not user:
        raise HTTPException(status_code=404, detail="Email not registered")

    otp = str(random.randint(100000, 999999))

    otp_col.update_one(
        {"email": email},
        {
            "$set": {
                "otp": otp,
                "expires_at": datetime.utcnow() + timedelta(minutes=5)
            }
        },
        upsert=True
    )

    send_email(
        to_email=email,
        subject="SCMXpertLite - Password Reset OTP",
        body=f"Your OTP is {otp}. It expires in 5 minutes."
    )

    return {"message": "OTP sent successfully"}


# 2 VERIFY OTP
@router.post("/verify-otp")
def verify_otp(data: VerifyOTP):
    entry = otp_col.find_one({"email": data.email.lower()})
    if not entry:
        raise HTTPException(status_code=400, detail="OTP not found")

    if entry["otp"] != data.otp:
        raise HTTPException(status_code=400, detail="Incorrect OTP")

    if entry["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")

    return {"message": "OTP verified"}


# 3 RESET PASSWORD
@router.post("/reset-password")
def reset_password(data: ResetPassword):
    email = data.email.lower()

    # hash new password before saving
    hashed_pw = pbkdf2_hash(data.new_password)

    result = users_col.update_one(
        {"email": email},
        {"$set": {"password": hashed_pw}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Password reset failed")

    otp_col.delete_one({"email": email})

    return {"message": "Password updated successfully"}



# 1 SEND OTP
@router.post("/forgot-password")
def forgot_password(data: ForgotPass):
    email = data.email.lower()

    # case-insensitive search
    user = users_col.find_one({"email": {"$regex": f"^{email}$", "$options": "i"}})

    if not user:
        raise HTTPException(status_code=404, detail="Email not registered")

    otp = str(random.randint(100000, 999999))

    otp_col.update_one(
        {"email": email},
        {
            "$set": {
                "otp": otp,
                "expires_at": datetime.utcnow() + timedelta(minutes=5)
            }
        },
        upsert=True
    )

    send_email(
        to_email=email,
        subject="SCMXpertLite - Password Reset OTP",
        body=f"Your OTP is {otp}. It expires in 5 minutes."
    )

    return {"message": "OTP sent successfully"}


# 2 VERIFY OTP
@router.post("/verify-otp")
def verify_otp(data: VerifyOTP):
    entry = otp_col.find_one({"email": data.email.lower()})
    if not entry:
        raise HTTPException(status_code=400, detail="OTP not found")

    if entry["otp"] != data.otp:
        raise HTTPException(status_code=400, detail="Incorrect OTP")

    if entry["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")

    return {"message": "OTP verified"}


# 3 RESET PASSWORD
@router.post("/reset-password")
def reset_password(data: ResetPassword):
    email = data.email.lower()

    result = users_col.update_one(
        {"email": email},
        {"$set": {"password": data.new_password}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Password reset failed")

    otp_col.delete_one({"email": email})

    return {"message": "Password updated successfully"}
print("DEBUG EMAIL VALUES:", MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM)
