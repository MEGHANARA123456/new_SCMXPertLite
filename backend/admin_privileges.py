from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from pymongo import MongoClient
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from bson import ObjectId
from backend import shipments_da
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
replies_col = db["adminreplies"]  

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
#========================================
# SUPER ADMIN CHECK (for critical actions)
#========================================
def require_super_admin(user):
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
# ======================================================
#  ADMIN — GET LOGGED SESSIONS
# ======================================================
@router.delete("/superadmin/delete-user/{username}")
def delete_user(username: str, current_user=Depends(get_current_user)):
    require_super_admin(current_user)

    user = users_col.find_one({"username": username})
    if not user:
        raise HTTPException(404, "User not found")

    users_col.delete_one({"username": username})

    # also delete sessions
    sessions_col.delete_many({"username": username})

    return {"success": True, "message": f"{username} deleted"}  
# ======================================================
#  ADMIN — DELETE ADMIN USER
# ======================================================
@router.delete("/superadmin/delete-admin/{username}")
def delete_admin(username: str, current_user=Depends(get_current_user)):
    require_super_admin(current_user)

    user = users_col.find_one({"username": username})
    if not user:
        raise HTTPException(404, "User not found")

    if user.get("role") != "admin":
        raise HTTPException(400, "User is not admin")

    users_col.delete_one({"username": username})
    sessions_col.delete_many({"username": username})

    return {"success": True, "message": "Admin deleted"}  
# ======================================================
#  ADMIN — FORCE LOGOUT USER
# ======================================================

@router.post("/superadmin/force-logout/{username}")
def force_logout(username: str, current_user=Depends(get_current_user)):
    require_super_admin(current_user)

    result = sessions_col.delete_many({"username": username})

    return {
        "success": True,
        "message": f"{username} logged out",
        "sessions_removed": result.deleted_count
    }

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
    require_role(current_user, ["admin","super_admin"])
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
    require_role(current_user, ["admin","super_admin"])
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
    require_role(current_user, ["admin","super_admin"])
    users = list(users_col.find({}, {"_id": 0}))
    return {"users": users}


# ======================================================
#  ADMIN — APPROVE REQUEST
# ======================================================
@router.post("/admin/requests/{request_id}/approve")
def approve_request(request_id: str, current_user=Depends(get_current_user)):
    require_role(current_user, ["admin","super_admin"])

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
    require_role(current_user, ["admin","super_admin"])

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
#  ADMIN — SEND REPLY   stores in "adminreplies" collection
# ======================================================
@router.post("/admin/requests/{request_id}/reply")
def reply_to_request(request_id: str, payload: dict,
                     current_user=Depends(get_current_user)):
    require_role(current_user, ["admin","super_admin"])

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

    replies_col.insert_one(reply_doc)   

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
    require_role(current_user, ["admin","super_admin"])
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
    require_role(current_user, ["admin", "super_admin"])

    new_role = payload.get("role")
    if not new_role:
        raise HTTPException(400, "Role required")

    user = users_col.find_one({"username": username})
    if not user:
        raise HTTPException(404, "User not found")

    current_role = user.get("role")

    #  RULE 1: Admin cannot create super_admin
    if new_role == "super_admin" and current_user.get("role") != "super_admin":
        raise HTTPException(403, "Only super admin can assign super_admin role")

    #  RULE 2: Admin cannot modify super_admin
    if current_role == "super_admin" and current_user.get("role") != "super_admin":
        raise HTTPException(403, "Cannot modify super admin")

    #  RULE 3: Prevent self-downgrade accident
    if username == current_user.get("username") and new_role != "super_admin":
        raise HTTPException(400, "You cannot downgrade yourself")

    users_col.update_one(
        {"username": username},
        {"$set": {"role": new_role}}
    )

    if user.get("email"):
        send_email(
            user["email"],
            "Role Changed",
            f"Your role has been updated to: {new_role}"
        )

    return {
        "success": True,
        "message": f"{username} role updated to {new_role}"
    }


# ======================================================
#  ADMIN — GET LOGGED SESSIONS  
# ======================================================
@router.get("/admin/loggedin")
def get_logged_sessions(current_user=Depends(get_current_user)):
    require_role(current_user, ["admin","super_admin"])

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
    require_role(current_user, ["admin","super_admin"])

    req = requests_col.find_one({"_id": request_id})
    if not req:
        raise HTTPException(404, "Request not found")

    requests_col.update_one(
        {"_id": request_id},
        {"$set": {"status": "resolved", "admin_action_at": datetime.utcnow()}}
    )

    return {"success": True}


# ======================================================
#  SUPER ADMIN — GET ALL CREDENTIALS & USER DATA
# ======================================================
@router.get("/superadmin/all-credentials")
def get_all_credentials(current_user=Depends(get_current_user)):
    """Super admin only — retrieve all user credentials and sensitive data"""
    require_super_admin(current_user)
    
    users_data = list(users_col.find({}, {
        "_id": 1,
        "username": 1,
        "email": 1,
        "role": 1,
        "created_at": 1,
        "fullname": 1,
        "picture": 1
    }))
    
    for u in users_data:
        u["_id"] = str(u["_id"])
    
    return {
        "success": True,
        "total_users": len(users_data),
        "users": users_data
    }


# ======================================================
#  SUPER ADMIN — GET ALL ADMINS ONLY
# ======================================================
@router.get("/superadmin/all-admins")
def get_all_admins(current_user=Depends(get_current_user)):
    """Super admin only — retrieve all admin and super_admin users"""
    require_super_admin(current_user)
    
    admin_users = list(users_col.find(
        {"role": {"$in": ["admin", "super_admin"]}},
        {"_id": 1, "username": 1, "email": 1, "role": 1, "created_at": 1, "fullname": 1}
    ))
    
    for u in admin_users:
        u["_id"] = str(u["_id"])
    
    return {
        "success": True,
        "total_admins": len(admin_users),
        "admins": admin_users
    }


# ======================================================
#  SUPER ADMIN — GET SYSTEM STATISTICS
# ======================================================
@router.get("/superadmin/system-stats")
def get_system_stats(current_user=Depends(get_current_user)):
    """Super admin only — comprehensive system statistics"""
    require_super_admin(current_user)
    
    total_users = users_col.count_documents({})
    total_admins = users_col.count_documents({"role": {"$in": ["admin", "super_admin"]}})
    total_requests = requests_col.count_documents({})
    pending_requests = requests_col.count_documents({"status": "pending"})
    total_sessions = sessions_col.count_documents({})
    total_replies = replies_col.count_documents({})
    
    return {
        "success": True,
        "stats": {
            "total_users": total_users,
            "total_admins": total_admins,
            "total_requests": total_requests,
            "pending_requests": pending_requests,
            "active_sessions": total_sessions,
            "total_replies": total_replies,
            "timestamp": datetime.utcnow().isoformat()
        }
    }


# ======================================================
#  SUPER ADMIN — FORCE LOGOUT ALL SESSIONS
# ======================================================
@router.post("/superadmin/force-logout-all")
def force_logout_all_sessions(current_user=Depends(get_current_user)):
    """Super admin only — clear all active sessions system-wide"""
    require_super_admin(current_user)
    
    result = sessions_col.delete_many({})
    
    return {
        "success": True,
        "message": f"All {result.deleted_count} sessions cleared",
        "sessions_cleared": result.deleted_count
    }


# ======================================================
#  RESTRICT DELETE POWER TO SUPER ADMIN ONLY
# ======================================================
@router.delete("/admin/delete-user/{username}")
def admin_delete_user(username: str, current_user=Depends(get_current_user)):
    """
    Regular admin cannot delete users. 
    Only super_admin has delete power.
    """
    # Must be super admin to delete
    require_super_admin(current_user)
    
    user = users_col.find_one({"username": username})
    if not user:
        raise HTTPException(404, "User not found")
    
    # Prevent self-deletion
    if username == current_user.get("username"):
        raise HTTPException(400, "Cannot delete yourself")
    
    users_col.delete_one({"username": username})
    sessions_col.delete_many({"username": username})
    
    return {
        "success": True,
        "message": f"User {username} deleted permanently"
    }


# ======================================================
#  SUPER ADMIN — PROMOTE USER TO ADMIN
# ======================================================
@router.post("/superadmin/promote-to-admin/{username}")
def promote_to_admin(username: str, current_user=Depends(get_current_user)):
    """Super admin only — promote regular user to admin"""
    require_super_admin(current_user)
    
    user = users_col.find_one({"username": username})
    if not user:
        raise HTTPException(404, "User not found")
    
    old_role = user.get("role", "user")
    
    if old_role == "admin" or old_role == "super_admin":
        raise HTTPException(400, f"User already has admin role: {old_role}")
    
    users_col.update_one(
        {"username": username},
        {"$set": {"role": "admin", "promoted_by": current_user.get("username"), "promoted_at": datetime.utcnow()}}
    )
    
    if user.get("email"):
        send_email(
            user["email"],
            "Promoted to Admin",
            f"Congratulations! You have been promoted to Admin role on SCMXpert."
        )
    
    return {
        "success": True,
        "message": f"{username} promoted to admin",
        "old_role": old_role,
        "new_role": "admin"
    }


# ======================================================
#  SUPER ADMIN — DEMOTE ADMIN TO USER
# ======================================================
@router.post("/superadmin/demote-admin/{username}")
def demote_admin_to_user(username: str, current_user=Depends(get_current_user)):
    """Super admin only — demote admin back to regular user"""
    require_super_admin(current_user)
    
    user = users_col.find_one({"username": username})
    if not user:
        raise HTTPException(404, "User not found")
    
    current_role = user.get("role", "user")
    
    if current_role != "admin":
        raise HTTPException(400, f"User is not an admin (current role: {current_role})")
    
    if username == current_user.get("username"):
        raise HTTPException(400, "Cannot demote yourself")
    
    users_col.update_one(
        {"username": username},
        {"$set": {"role": "user", "demoted_by": current_user.get("username"), "demoted_at": datetime.utcnow()}}
    )
    
    if user.get("email"):
        send_email(
            user["email"],
            "Admin Role Removed",
            f"Your admin privileges have been revoked on SCMXpert."
        )
    
    return {
        "success": True,
        "message": f"{username} demoted to user",
        "old_role": "admin",
        "new_role": "user"
    }


# ======================================================
#  SUPER ADMIN — AUDIT LOG (WHO DID WHAT)
# ======================================================
@router.get("/superadmin/audit-log")
def get_audit_log(current_user=Depends(get_current_user)):
    """Super admin only — get audit trail of admin actions"""
    require_super_admin(current_user)
    
    # Get recent role changes from user documents
    recent_changes = list(users_col.find(
        {"promoted_at": {"$exists": True}},
        {"username": 1, "promoted_by": 1, "promoted_at": 1, "demoted_by": 1, "demoted_at": 1, "role": 1}
    ).sort("promoted_at", -1).limit(50))
    
    for item in recent_changes:
        item["_id"] = str(item["_id"])
    
    return {
        "success": True,
        "audit_entries": recent_changes
    }
 

 