# =======================================
# role_management.py  (FINAL VERSION)
# =======================================

from fastapi import APIRouter, Depends, HTTPException, Body
from pymongo import MongoClient
from dotenv import load_dotenv
import os

from backend.auth_utils import get_current_user, require_role
from backend.auth_utils import send_email

load_dotenv()
router = APIRouter()

# ---------------------------------------
# Database Connection
# ---------------------------------------
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_APP")]
users = db["user"]

# Allowed roles
ALLOWED = ["admin", "manager", "user", "viewer"]

# ---------------------------------------
# DEFAULT ROLE SEEDING
# ---------------------------------------
DEFAULT_ROLES = {
    "meghana": "admin",
    "kamatammeghana": "manager",
    "raji": "user"
}


def apply_default_roles():
    """Auto-create or update seeded default users."""
    for username, role in DEFAULT_ROLES.items():
        role = role.lower().strip()
        if role not in ALLOWED:
            continue

        existing = users.find_one({"username": username})

        if not existing:
            users.insert_one({
                "username": username,
                "email": f"{username}@gmail.com",
                "password": "",    # no login password (optional)
                "role": role
            })
            print(f"Created default user '{username}' with role '{role}'")

        else:
            if existing.get("role") != role:
                users.update_one(
                    {"username": username},
                    {"$set": {"role": role}}
                )
                print(f"Updated '{username}' role → {role}")


# Run once at import
apply_default_roles()


# =======================================
# ROLE UPDATE ENDPOINT WITH EMAIL NOTIFY
# =======================================
@router.post("/update-role")
async def update_role(
    username: str = Body(...),
    new_role: str = Body(...),
    current_user=Depends(get_current_user)
):

    # Only admin allowed
    require_role(current_user, ["admin"])

    new_role = new_role.lower().strip()
    if new_role not in ALLOWED:
        raise HTTPException(400, "Invalid role")

    # Find user
    user = users.find_one({"username": username})
    if not user:
        raise HTTPException(404, "User not found")

    old_role = user.get("role", "user")
    user_email = user.get("email")

    # Update the role in DB
    users.update_one(
        {"username": username},
        {"$set": {"role": new_role}}
    )

    # ---------------------------------------
    # EMAIL NOTIFICATION
    # ---------------------------------------
    if user_email:
        try:
            await send_email(
                subject="SCMXpert Role Updated",
                recipients=[user_email],
                body=f"""
                <h2>Role Updated</h2>
                <p>Hello <b>{username}</b>,</p>
                <p>Your SCMXpert role has been updated.</p>
                <p><b>Old role:</b> {old_role}<br>
                <b>New role:</b> {new_role}</p>
                <br>
                <p>If this wasn't you, please contact support immediately.</p>
                """
            )
        except Exception as e:
            print("Email sending failed:", e)

    return {
        "message": "Role updated successfully",
        "old_role": old_role,
        "new_role": new_role
    }


# =======================================
# ADMIN MANUAL ROUTE (NO EMAIL)
# =======================================
@router.post("/admin/set-role/{username}")
def admin_set_role(
    username: str,
    role: str = Body(...),
    current_user=Depends(get_current_user)
):

    require_role(current_user, ["admin"])

    role = role.lower().strip()
    if role not in ALLOWED:
        raise HTTPException(400, "Invalid role")

    if not users.find_one({"username": username}):
        raise HTTPException(404, "User not found")

    users.update_one({"username": username}, {"$set": {"role": role}})

    return {"message": f"Role updated to {role}"}
