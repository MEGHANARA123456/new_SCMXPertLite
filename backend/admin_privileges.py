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

# ======================================================
#  DATABASE CONNECTION
# ======================================================
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_APP")]

requests_col = db["admin_requests"]          # main request collection
users_col = db["user"]
sessions_col = db["logged_sessions"]
replies_col = db["admin_replies"]            # NEW — reply collection


# ======================================================
#  SMTP CONFIG
# ======================================================
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = int(os.getenv("MAIL_PORT"))


# ======================================================
#  EMAIL SENDER
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
# 1️⃣ USER CREATES REQUEST
# ======================================================
@router.post("/requests")
def create_request(data: dict, user=Depends(get_current_user)):

    payload = {
        "username": user["username"],
        "email": user.get("email"),
        "type": data.get("type"),
        "title": data.get("title"),
        "description": data.get("description"),
        "requested_at": datetime.utcnow(),
        "status": "pending"
    }

    requests_col.insert_one(payload)
    return {"success": True, "message": "Request submitted"}


# ======================================================
# 2️⃣ GET ALL REQUESTS
# ======================================================
@router.get("/admin/requests")
def get_all_requests(current_user=Depends(get_current_user)):
    require_role(current_user, ["admin"])
    reqs = list(requests_col.find({}, {"_id": 0}))
    return {"requests": reqs}


# ======================================================
# 3️⃣ GET PENDING REQUESTS
# ======================================================
@router.get("/admin/pending")
def get_pending(current_user=Depends(get_current_user)):
    require_role(current_user, ["admin"])
    reqs = list(requests_col.find({"status": "pending"}, {"_id": 0}))
    return {"requests": reqs, "total": len(reqs)}


# ======================================================
# 4️⃣ APPROVE REQUEST
# ======================================================
@router.post("/admin/requests/{username}/approve")
def approve_request(username: str, current_user=Depends(get_current_user)):
    require_role(current_user, ["admin"])

    req = requests_col.find_one({"username": username})
    if not req:
        raise HTTPException(404, "Request not found")

    requests_col.update_one(
        {"username": username},
        {"$set": {"status": "approved", "admin_action_at": datetime.utcnow()}}
    )

    users_col.update_one(
        {"username": username},
        {"$set": {"role": "admin"}}
    )

    email = req.get("email")
    if email:
        subject = "Your Request Has Been Approved"
        body = f"""
Hello {username},

Your admin access request has been APPROVED.

Approved by: {current_user['username']}
"""
        send_email(email, subject, body)

    return {"success": True, "message": "Approved"}


# ======================================================
# 5️⃣ REJECT REQUEST
# ======================================================
@router.post("/admin/requests/{username}/reject")
def reject_request(username: str, current_user=Depends(get_current_user)):
    require_role(current_user, ["admin"])

    req = requests_col.find_one({"username": username})
    if not req:
        raise HTTPException(404, "Request not found")

    requests_col.update_one(
        {"username": username},
        {"$set": {"status": "rejected", "admin_action_at": datetime.utcnow()}}
    )

    email = req.get("email")
    if email:
        subject = "Your Request Was Rejected"
        body = f"""
Hello {username},

Your admin access request has been REJECTED.

Reviewed by: {current_user['username']}
"""
        send_email(email, subject, body)

    return {"success": True, "message": "Rejected"}


# ======================================================
# 6️⃣ ADMIN SENDS REPLY (drawer in admin dashboard)
# ======================================================
@router.post("/admin/reply")
def admin_reply_1(data: dict, current_user=Depends(get_current_user)):
    require_role(current_user, ["admin"])

    username = data.get("username")
    message = data.get("message")

    if not username or not message:
        raise HTTPException(400, "username & message required")

    replies_col.insert_one({
        "username": username,
        "admin": current_user["username"],
        "message": message,
        "sent_at": datetime.utcnow()
    })

    return {"success": True, "message": "Reply sent"}


# ======================================================
# 7️⃣ ADMIN SENDS REPLY (used by /admin/replies/send)
# ======================================================
@router.post("/admin/replies/send")
def admin_reply_2(payload: dict, current_user: dict = Depends(get_current_user)):
    require_role(current_user, ["admin"])

    username = payload.get("username")
    message = payload.get("message")

    if not username or not message:
        raise HTTPException(400, "username & message required")

    replies_col.insert_one({
        "username": username,
        "admin": current_user["username"],
        "message": message,
        "sent_at": datetime.utcnow()
    })

    return {"success": True, "message": "Reply sent"}


# ======================================================
# 8️⃣ ADMIN GETS ALL REPLIES
# ======================================================
@router.get("/admin/replies")
def get_replies(current_user=Depends(get_current_user)):
    require_role(current_user, ["admin"])
    items = list(replies_col.find({}, {"_id": 0}))
    return {"replies": items}


# ======================================================
# 9️⃣ USER FETCHES THEIR REPLIES
# ======================================================
@router.get("/user/replies")
def get_user_replies(current_user: dict = Depends(get_current_user)):

    username = current_user["username"]

    data = list(replies_col.find(
        {"username": username},
        {"_id": 0}
    ))

    return {"replies": data}


# ======================================================
# 🔟 ADMIN UPDATES ROLE
# ======================================================
@router.post("/admin/set-role/{username}")
def set_role(username: str, payload: dict, current_user=Depends(get_current_user)):
    require_role(current_user, ["admin"])

    new_role = payload.get("role")
    if not new_role:
        raise HTTPException(400, "Role required")

    user = users_col.find_one({"username": username})
    if not user:
        raise HTTPException(404, "User not found")

    users_col.update_one({"username": username}, {"$set": {"role": new_role}})

    email = user.get("email")
    if email:
        subject = "Your Role Has Changed"
        body = f"Your role is now: {new_role}"
        send_email(email, subject, body)

    return {"success": True, "message": "Role updated"}


# ======================================================
# 1️LOG ACTIVE SESSIONS
# ======================================================
@router.post("/admin/loggedin")
def record_logged_in(payload: dict, current_user=Depends(get_current_user)):
    username = payload.get("username") or current_user.get("username")
    ts = payload.get("ts")

    sessions_col.update_one(
        {"username": username},
        {"$set": {"ts": ts}},
        upsert=True
    )
    return {"message": "Recorded"}
