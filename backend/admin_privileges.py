from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from pymongo import MongoClient
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from bson import ObjectId
from backend.auth_utils import get_current_user, require_role

load_dotenv()
router = APIRouter()

# ======================================================
#  DATABASE CONNECTION
# ======================================================
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_APP")]  # type: ignore

requests_col = db["admin_requests"]
users_col = db["user"]
sessions_col = db["logged_sessions"]
replies_col = db["adminreplies"]   # ✅ FIXED: matches actual MongoDB collection name

# ======================================================
#  SMTP CONFIG
# ======================================================
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = int(os.getenv("MAIL_PORT"))  # type: ignore

# ======================================================
#  SMTP SENDER
# ======================================================
def send_email(to_email: str, subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM  # type: ignore
    msg["To"] = to_email

    try:
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:  # type: ignore
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)  # type: ignore
            server.sendmail(MAIL_FROM, to_email, msg.as_string())  # type: ignore
        return True, None
    except Exception as e:
        return False, str(e)


# ======================================================
#  UNIVERSAL FIND FUNCTION (string ID + old ObjectId)
# ======================================================
def find_request_by_id(request_id: str):
    """Match both string IDs and old ObjectIds."""
    if ObjectId.is_valid(request_id):
        return requests_col.find_one({
            "$or": [
                {"_id": request_id},           # string ID
                {"_id": ObjectId(request_id)}  # old ObjectId
            ]
        })
    else:
        return requests_col.find_one({"_id": request_id})


# ======================================================
#  USER CREATES REQUEST
# ======================================================
@router.post("/requests")
def create_request(data: dict, user=Depends(get_current_user)):
    payload = {
        "_id": str(datetime.utcnow().timestamp()).replace(".", ""),  # string ID
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
#  ADMIN — GET ALL REQUESTS
# ======================================================
@router.get("/admin/requests")
def get_all_requests(current_user=Depends(get_current_user)):
    require_role(current_user, ["admin"])
    reqs = []
    for r in requests_col.find({}):
        r["_id"] = str(r["_id"])
        reqs.append(r)
    return {"requests": reqs}


# ======================================================
#  ADMIN — GET ONLY PENDING REQUESTS
# ======================================================
@router.get("/admin/pending")
def get_pending(current_user=Depends(get_current_user)):
    require_role(current_user, ["admin"])
    data = []
    for r in requests_col.find({"status": "pending"}):
        r["_id"] = str(r["_id"])
        data.append(r)
    return {"requests": data}


# ======================================================
#  ADMIN — GET ALL USERS
# ======================================================
@router.get("/admin/users")
def get_users(current_user=Depends(get_current_user)):
    require_role(current_user, ["admin"])
    users = list(users_col.find({}, {"_id": 0}))
    return {"users": users}


# ======================================================
#  ADMIN — APPROVE REQUEST
# ======================================================
@router.post("/admin/requests/{request_id}/approve")
def approve_request(request_id: str, current_user=Depends(get_current_user)):
    require_role(current_user, ["admin"])

    req = requests_col.find_one({"_id": request_id})
    if not req:
        raise HTTPException(404, "Request not found")

    requests_col.update_one(
        {"_id": request_id},
        {"$set": {"status": "approved", "admin_action_at": datetime.utcnow()}}
    )
    users_col.update_one(
        {"username": req["username"]},
        {"$set": {"role": "admin"}}
    )

    if req.get("email"):
        send_email(req["email"],
                   "Your Request Was Approved",
                   f"Hello {req['username']}, your request has been approved.")

    return {"success": True}


# ======================================================
#  ADMIN — REJECT REQUEST
# ======================================================
@router.post("/admin/requests/{request_id}/reject")
def reject_request(request_id: str, current_user=Depends(get_current_user)):
    require_role(current_user, ["admin"])

    req = requests_col.find_one({"_id": request_id})
    if not req:
        raise HTTPException(404, "Request not found")

    requests_col.update_one(
        {"_id": request_id},
        {"$set": {"status": "rejected", "admin_action_at": datetime.utcnow()}}
    )

    if req.get("email"):
        send_email(req["email"],
                   "Your Request Was Rejected",
                   f"Hello {req['username']}, your request has been rejected.")

    return {"success": True}


# ======================================================
#  ADMIN — SEND REPLY  ✅ stores in "adminreplies" collection
# ======================================================
@router.post("/admin/requests/{request_id}/reply")
def reply_to_request(request_id: str, payload: dict,
                     current_user=Depends(get_current_user)):
    require_role(current_user, ["admin"])

    req = requests_col.find_one({"_id": request_id})
    if not req:
        raise HTTPException(404, "Request not found")

    text = payload.get("reply")
    if not text:
        raise HTTPException(400, "Reply message required")

    reply_doc = {
        "request_id": request_id,
        "username": req["username"],
        "admin": current_user["username"],
        "reply": text,
        "request_title": req.get("title") or req.get("type"),
        "sent_at": datetime.utcnow()
    }

    replies_col.insert_one(reply_doc)   # ✅ now saves to correct collection

    requests_col.update_one(
        {"_id": request_id},
        {"$set": {"status": "resolved", "admin_action_at": datetime.utcnow()}}
    )

    return {"success": True, "message": "Reply sent & request resolved"}


# ======================================================
#  ADMIN — GET ALL REPLIES
# ======================================================
@router.get("/admin/replies")
def get_replies(current_user=Depends(get_current_user)):
    require_role(current_user, ["admin"])
    data = []
    for r in replies_col.find().sort("sent_at", -1):
        r["_id"] = str(r["_id"])
        data.append(r)
    return {"replies": data}


# ======================================================
#  USER — GET THEIR REPLIES
# ======================================================
@router.get("/user/replies")
def get_user_replies(current_user=Depends(get_current_user)):
    data = list(replies_col.find(
        {"username": current_user["username"]},
        {"_id": 0}
    ))
    return {"replies": data}


# ======================================================
#  ADMIN — UPDATE USER ROLE
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

    if user.get("email"):
        send_email(user["email"], "Role Changed",
                   f"Your role is now: {new_role}")

    return {"success": True}


# ======================================================
#  ADMIN — GET LOGGED SESSIONS  ✅ duplicate removed
# ======================================================
@router.get("/admin/loggedin")
def get_logged_sessions(current_user=Depends(get_current_user)):
    require_role(current_user, ["admin"])

    sessions = list(
        sessions_col.find({}, {"_id": 1, "username": 1, "ts": 1, "logged_at": 1})
        .sort("logged_at", -1)
        .limit(100)
    )
    for s in sessions:
        s["_id"] = str(s["_id"])

    return {"sessions": sessions}


# ======================================================
#  ADMIN — RESOLVE REQUEST
# ======================================================
@router.post("/admin/requests/{request_id}/resolve")
def resolve_request(request_id: str, current_user=Depends(get_current_user)):
    require_role(current_user, ["admin"])

    req = requests_col.find_one({"_id": request_id})
    if not req:
        raise HTTPException(404, "Request not found")

    requests_col.update_one(
        {"_id": request_id},
        {"$set": {"status": "resolved", "admin_action_at": datetime.utcnow()}}
    )

    return {"success": True}