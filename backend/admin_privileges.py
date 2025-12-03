from fastapi import APIRouter, Depends, HTTPException, Form
from datetime import datetime
from pymongo import MongoClient
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

from backend.auth_utils import get_current_user, require_role

load_dotenv()
router = APIRouter()

# DB
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_APP")]
requests_col = db["admin_requests"]
users_col = db["user"]
sessions_col = db["logged_sessions"]

# EMAIL CONFIG
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = int(os.getenv("MAIL_PORT"))


# ======================================================
#  EMAIL SENDER (Reusable for all notifications)
# ======================================================
def send_email(to_email: str, subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM
    msg["To"] = to_email

    try:
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_FROM, to_email, msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)


# ======================================================
# 1️⃣ USER REQUESTS ADMIN ACCESS — SEND EMAIL TO ADMIN
# ======================================================
@router.post("/admin/request-access")
def request_admin(current_user: dict = Depends(get_current_user)):
    username = current_user["username"]
    email = current_user.get("email")

    if current_user["role"] == "admin":
        raise HTTPException(400, "Already admin")

    if requests_col.find_one({"username": username}):
        raise HTTPException(400, "Already requested")

    requests_col.insert_one({
        "username": username,
        "email": email,
        "requested_at": datetime.utcnow(),
        "status": "pending"
    })

    # Notify admin email
    admin_email = MAIL_USERNAME

    subject = "New Admin Access Request"
    body = f"""
User {username} has requested admin access.

Time: {datetime.utcnow()} UTC
Email: {email}

Login to SCMXpertLite Admin Dashboard to approve or reject.
"""

    email_sent, email_error = send_email(admin_email, subject, body)

    return {
        "message": "Admin request submitted",
        "email_sent": email_sent,
        "email_error": email_error
    }


# ======================================================
# 2️⃣ GET PENDING REQUESTS
# ======================================================
@router.get("/admin/pending")
def get_pending(current_user: dict = Depends(get_current_user)):
    require_role(current_user, ["admin"])
    
    data = list(requests_col.find({"status": "pending"}, {"_id": 0}))
    return {"total": len(data), "requests": data}


# ======================================================
# 3️⃣ ADMIN UPDATES ANY USER ROLE  (used in modal)
# ======================================================
@router.post("/admin/set-role/{username}")
def set_role_api(username: str, payload: dict, current_user: dict = Depends(get_current_user)):
    require_role(current_user, ["admin"])

    new_role = payload.get("role")
    if not new_role:
        raise HTTPException(400, "Role is required")

    user = users_col.find_one({"username": username})
    if not user:
        raise HTTPException(404, "User not found")

    users_col.update_one({"username": username}, {"$set": {"role": new_role}})

    # Notify the user by email
    email = user.get("email")
    if email:
        subject = "Your Role Has Been Updated"
        body = f"""
Hello {username},

Your SCMXpertLite role has been updated.

New Role: {new_role}
Updated by Admin: {current_user['username']}

If you did not expect this change, contact support.
"""
        email_sent, email_error = send_email(email, subject, body)
    else:
        email_sent = False
        email_error = "User has no email saved"

    return {
        "message": "Role updated successfully",
        "email_sent": email_sent,
        "email_error": email_error
    }


# ======================================================
# 4️⃣ APPROVE ADMIN REQUEST — SEND EMAIL
# ======================================================
@router.post("/admin/role/approve")
def approve_role(username: str = Form(...), current_user: dict = Depends(get_current_user)):
    require_role(current_user, ["admin"])

    users_col.update_one({"username": username}, {"$set": {"role": "admin"}})

    req = requests_col.find_one({"username": username})

    requests_col.update_one(
        {"username": username},
        {"$set": {
            "status": "approved",
            "admin_action_at": datetime.utcnow()
        }}
    )

    # send email
    email = req.get("email") if req else None
    if email:
        subject = "Your Admin Access Request Has Been Approved"
        body = f"""
Hello {username},

Your request for admin access has been APPROVED.

You now have full administrative privileges.

Approved by: {current_user['username']}
"""
        email_sent, email_error = send_email(email, subject, body)
    else:
        email_sent, email_error = False, "No email on file"

    return {
        "message": "Role approved successfully",
        "email_sent": email_sent,
        "email_error": email_error
    }


# ======================================================
# 5️⃣ REJECT ADMIN REQUEST — SEND EMAIL
# ======================================================
@router.post("/admin/role/reject")
def reject_role(username: str = Form(...), current_user: dict = Depends(get_current_user)):
    require_role(current_user, ["admin"])

    req = requests_col.find_one({"username": username})

    requests_col.update_one(
        {"username": username, "status": "pending"},
        {"$set": {
            "status": "rejected",
            "admin_action_at": datetime.utcnow()
        }}
    )

    # send email
    email = req.get("email") if req else None
    if email:
        subject = "Your Admin Access Request Was Rejected"
        body = f"""
Hello {username},

Your request for admin access has been REJECTED.

Reviewed by: {current_user['username']}

You may submit a new request later if needed.
"""
        email_sent, email_error = send_email(email, subject, body)
    else:
        email_sent, email_error = False, "No email on file"

    return {
        "message": "User request rejected",
        "email_sent": email_sent,
        "email_error": email_error
    }


# ======================================================
# 6️⃣ LOG SESSIONS (Sidebar "Active users")
# ======================================================
@router.post("/admin/loggedin")
def record_logged_in(payload: dict, current_user: dict = Depends(get_current_user)):
    username = payload.get("username") or current_user.get("username")
    ts = payload.get("ts")

    if not username:
        raise HTTPException(400, "username required")

    sessions_col.update_one(
        {"username": username},
        {"$set": {"ts": ts}},
        upsert=True
    )
    return {"message": "recorded"}
