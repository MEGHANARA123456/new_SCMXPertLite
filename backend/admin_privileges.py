from fastapi import APIRouter, Depends, HTTPException, Form
from datetime import datetime
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from backend.auth_utils import get_current_user
from backend.auth_utils import require_role

load_dotenv()
router = APIRouter()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_APP")]
requests_col = db["admin_requests"]
users_col = db["user"]
sessions_col = db["logged_sessions"]

# ======================================================
# 1️⃣ USER REQUESTS ACCESS
# ======================================================
@router.post("/admin/request-access")
def request_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] == "admin":
        raise HTTPException(400, "Already admin")

    if requests_col.find_one({"username": current_user["username"]}):
        raise HTTPException(400, "Already requested")

    requests_col.insert_one({
        "username": current_user["username"],
        "requested_at": datetime.utcnow(),
        "status": "pending"
    })
    return {"message": "Admin request submitted"}


# ======================================================
# 2️⃣ ADMIN SEE PENDING REQUESTS
# ======================================================
@router.get("/admin/pending")
def get_pending(current_user: dict = Depends(get_current_user)):
    require_role(current_user, ["admin"])
    data = list(requests_col.find({"status": "pending"}, {"_id": 0}))
    return {"total": len(data), "requests": data}


# ======================================================
# ⭐ ADD YOUR NEW ROLE APPROVAL/REJECTION ROUTES HERE ⭐
# ======================================================

@router.post("/admin/role/approve")
def approve_role(username: str = Form(...), current_user: dict = Depends(get_current_user)):
    require_role(current_user, ["admin"])

    users_col.update_one({"username": username}, {"$set": {"role": "admin"}})

    requests_col.update_one(
        {"username": username, "status": "pending"},
        {"$set": {
            "status": "approved",
            "admin_action_at": datetime.utcnow()
        }}
    )
    return {"message": "Role approved successfully"}


@router.post("/admin/role/reject")
def reject_role(username: str = Form(...), current_user: dict = Depends(get_current_user)):
    require_role(current_user, ["admin"])

    requests_col.update_one(
        {"username": username, "status": "pending"},
        {"$set": {
            "status": "rejected",
            "admin_action_at": datetime.utcnow()
        }}
    )
    return {"message": "User request rejected"}


# ======================================================
# 3️⃣ OPTIONAL: Active session log
# ======================================================
@router.post("/admin/loggedin")
def record_logged_in(payload: dict, current_user: dict = Depends(get_current_user)):
    username = payload.get("username") or current_user.get("username")
    ts = payload.get("ts")

    if not username:
        raise HTTPException(400, "username required")

    sessions_col.update_one(
        {"username": username},
        {"$set": {"username": username, "ts": ts}},
        upsert=True
    )
    return {"message": "recorded"}
