from fastapi import APIRouter, Depends, HTTPException, Body
from pymongo import MongoClient
import os
from dotenv import load_dotenv

from backend.user import get_current_user
from backend.auth_utils import require_role

load_dotenv()
router = APIRouter()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
users = db["user"]

ALLOWED = ["admin", "manager", "viewer", "user"]

# =============================
# DEFAULT ROLES SETUP
# =============================
DEFAULT_ROLES = {
    "meghana": "admin",
    "kamatammeghana": "manager",
    "raji": "user"
}


def apply_default_roles():
    """Auto-create or update default users with assigned roles."""
    for username, role in DEFAULT_ROLES.items():
        role = role.lower().strip()
        if role not in ALLOWED:
            continue
        found = users.find_one({"username": username})

        if not found:
            # Create user with empty password (or any placeholder)
            users.insert_one({
                "username": username,
                "email": f"{username}@gmail.com",
                "password": "",
                "role": role
            })
            print(f" Created default user '{username}' with role '{role}'")
        else:
            # Update role if different
            if found.get("role") != role:
                users.update_one(
                    {"username": username},
                    {"$set": {"role": role}}
                )
                print(f" Updated role of '{username}' → {role}")


# Run the default role setup once
apply_default_roles()


# =============================
#   SET ROLE ROUTE
# =============================
@router.post("/admin/set-role/{username}")
def set_role(username: str, role: str = Body(...), current_user=Depends(get_current_user)):

    require_role(current_user, ["admin"])

    role = role.lower().strip()
    if role not in ALLOWED:
        raise HTTPException(400, "Invalid role")

    if not users.find_one({"username": username}):
        raise HTTPException(404, "User not found")

    users.update_one({"username": username}, {"$set": {"role": role}})
    return {"message": f"Role updated to {role}"}
