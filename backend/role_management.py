# =======================================
# role_management.py  (FINAL WORKING)
# =======================================

from fastapi import APIRouter, Depends, HTTPException, Body
from pymongo import MongoClient
import os
from dotenv import load_dotenv

from backend.auth_utils import get_current_user, require_role, send_email

load_dotenv()
router = APIRouter()

# DB
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_APP")]
users = db["user"]

ALLOWED = ["admin", "manager", "editor", "viewer", "user"]

# =======================================
# FRONTEND-COMPATIBLE ENDPOINT
# Called by admin_dashboard: POST /admin/set-role/{username}
# =======================================
@router.post("/admin/set-role/{username}")
async def set_role(username: str, data: dict = Body(...), current_user=Depends(get_current_user)):

    # only admin can edit roles
    require_role(current_user, ["admin"])

    new_role = data.get("role", "").lower().strip()

    if new_role not in ALLOWED:
        raise HTTPException(400, "Invalid role")

    # Fetch user from DB
    user = users.find_one({"username": username})
    if not user:
        raise HTTPException(404, "User not found")

    old_role = user.get("role", "user")
    user_email = user.get("email")

    # Update DB
    users.update_one(
        {"username": username},
        {"$set": {"role": new_role}}
    )

    # Send email notification and report status
    email_sent = False
    email_error = None
    if user_email:
        try:
            await send_email(
                subject="SCMXpert Role Updated",
                recipients=[user_email],
                body=f"""
                <h3>Role Updated</h3>
                <p>Hello <b>{username}</b>,</p>
                <p>Your SCMXpert role was updated.</p>
                <p><b>Old Role:</b> {old_role}<br>
                <b>New Role:</b> {new_role}</p>
                """
            )
            email_sent = True
        except Exception as e:
            email_error = str(e)
            print("Email send error:", e)

    return {
        "message": "Role updated successfully",
        "old_role": old_role,
        "new_role": new_role,
        "email_sent": email_sent,
        "email_error": email_error
    }
