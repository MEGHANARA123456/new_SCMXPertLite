from fastapi import APIRouter, Form, HTTPException, Depends, Body
from bson import ObjectId
from pydantic import EmailStr,BaseModel
from jose import jwt
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
import os, hashlib, re, base64, hmac, requests,random, smtplib,json
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from backend.models import SignupOtpRequest, SignupVerifyOtpRequest
load_dotenv()

router = APIRouter()

# ====== CONFIG ======
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_APP = os.getenv("MONGO_DB_APP")

# Email config
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = int(os.getenv("MAIL_PORT")) # type: ignore
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_APP] # type: ignore
users = db["user"]
otp_col = db["otp_store"]
sessions_col = db["logged_sessions"]
oauth2 = OAuth2PasswordBearer(tokenUrl="login")
# DB collections (add these after your existing db setup)
shipments = db["shipments"]
devices = db["devices"]

# ============================================================
# PASSWORD HELPERS
# ============================================================
def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()


def pbkdf2_hash(password: str, iterations: int = 200_000) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def pbkdf2_verify(stored: str, password: str) -> bool:
    try:
        algo, iters, salt_b64, dk_b64 = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iters)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(dk_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def verify_and_migrate_password(user: dict, plain: str) -> bool:
    hashed = user.get("password", "")

    # Already PBKDF2
    if isinstance(hashed, str) and hashed.startswith("pbkdf2_sha256$"):
        return pbkdf2_verify(hashed, plain)

    # Legacy SHA256 → upgrade
    if isinstance(hashed, str) and re.fullmatch(r"[0-9a-fA-F]{64}", hashed):
        if hash_password(plain) == hashed:
            new_hash = pbkdf2_hash(plain)
            users.update_one({"_id": user["_id"]}, {"$set": {"password": new_hash}})
            return True

    return False


# ============================================================
# JWT TOKEN FIXED (FULL ROLE SUPPORT)
# ============================================================
def create_token(data: dict):
    payload = data.copy()

    # required for admin dashboard
    payload["role"] = data.get("role", "user")
    payload["sub"] = data.get("username")  # identity

    payload["exp"] = datetime.utcnow() + timedelta(hours=10)

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM) # type: ignore


# ============================================================
# CURRENT USER FIX (returns role always)
# ============================================================
def get_current_user(token: str = Depends(oauth2)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # type: ignore
        username = payload.get("sub") or payload.get("username")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    user["_id"] = str(user["_id"])
    user["role"] = user.get("role", "user")  # ensure role exists

    return user


# ============================================================
# reCAPTCHA Verification
# ============================================================
def verify_recaptcha(token: str, action: str = None) -> bool: # type: ignore

    if not token:
        print("[reCAPTCHA] Empty token accepted (fallback mode)")
        return True

    if not RECAPTCHA_SECRET_KEY:
        print("[reCAPTCHA] No secret key → auto-pass")
        return True

    try:
        url = "https://www.google.com/recaptcha/api/siteverify"
        res = requests.post(url, data={"secret": RECAPTCHA_SECRET_KEY, "response": token}, timeout=6)
        data = res.json()

        if not data.get("success"):
            print("[reCAPTCHA] Failed", data)
            return False

        if action and data.get("action") and data.get("action") != action:
            return False

        if "score" in data and float(data.get("score", 0)) < 0.5:
            return False

        return True

    except Exception as e:
        print("[reCAPTCHA] exception:", e)
        return False


# ============================================================
# Validation Helpers
# ============================================================
def validate_password(p: str):
    return (
        len(p) >= 8 and
        re.search(r"[A-Z]", p) and
        re.search(r"[a-z]", p) and
        re.search(r"[0-9]", p) and
        re.search(r"[!@#$%^&*]", p)
    )
# ============================================================
# GET CURRENT USER PROFILE
# ============================================================
@router.get("/user/profile")
def get_profile(current_user: dict = Depends(get_current_user)): # type: ignore
    return {
        "username": current_user["username"],
        "email": current_user.get("email"),
        "role": current_user.get("role", "user"),
        "fullname": current_user.get("fullname", ""),
        "picture": current_user.get("picture", ""),
        "created_at": str(current_user.get("created_at", ""))
    }
# ============================================================
# GET ONLY THIS USER'S SHIPMENTS
# ============================================================
@router.get("/user/shipments")
def get_my_shipments(current_user: dict = Depends(get_current_user)):
    username = current_user["username"]

    my_shipments = list(shipments.find({"created_by": username}))

    for s in my_shipments:
        s["_id"] = str(s["_id"])

    return {"shipments": my_shipments, "total": len(my_shipments)}

# ============================================================
# GET ONLY THIS USER'S DEVICES
# ============================================================
@router.get("/user/devices")
def get_my_devices(current_user: dict = Depends(get_current_user)):
    username = current_user["username"]

    my_devices = list(devices.find({"created_by": username}))

    for d in my_devices:
        d["_id"] = str(d["_id"])

    return {"devices": my_devices, "total": len(my_devices)}

# ============================================================
# GET DASHBOARD SUMMARY (counts only for this user)
# ============================================================
@router.get("/user/dashboard")
def get_my_dashboard(current_user: dict = Depends(get_current_user)):
    username = current_user["username"]

    total_shipments = shipments.count_documents({"created_by": username})
    active_shipments = shipments.count_documents({"created_by": username, "status": "active"})
    delivered = shipments.count_documents({"created_by": username, "status": "delivered"})
    total_devices = devices.count_documents({"created_by": username})

    return {
        "username": username,
        "total_shipments": total_shipments,
        "active_shipments": active_shipments,
        "delivered": delivered,
        "total_devices": total_devices
    }

# ============================================================
# Helper: send OTP email
# ============================================================
def send_otp_email(to_email: str, otp: str, firstname: str):
    msg = MIMEText(f"Hi {firstname},\n\nYour SCMXpertLite signup OTP is: {otp}\n\nValid for 10 minutes.")
    msg["Subject"] = "Your SCMXpertLite Signup OTP"
    msg["From"] = MAIL_FROM # type: ignore
    msg["To"] = to_email
    with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as smtp: # type: ignore
        smtp.starttls()
        smtp.login(MAIL_FROM, MAIL_PASSWORD) # type: ignore
        smtp.sendmail(MAIL_FROM, to_email, msg.as_string()) # type: ignore

# ============================================================
# STEP 1 — Validate details, store temp, send OTP
# ============================================================
@router.post("/signup/send-otp")
def signup_send_otp(data: SignupOtpRequest):
    if users.find_one({"$or": [{"username": data.username}, {"email": data.email.lower()}]}):
        raise HTTPException(status_code=400, detail="Username or email already exists")

    if not validate_password(data.password):
        raise HTTPException(status_code=400, detail="Weak password. Min 8 chars, upper, lower, digit, special (!@#$%^&*)")

    otp = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    # Upsert: overwrite any previous pending OTP for this email
    otp_col.update_one(
        {"email": data.email.lower()},
        {"$set": {
            "email":     data.email.lower(),
            "otp":       otp,
            "expires_at": expires_at,
            "pending_user": {
                "firstname": data.firstname,
                "lastname":  data.lastname,
                "username":  data.username,
                "email":     data.email.lower(),
                "password":  pbkdf2_hash(data.password),
                "role":      "user",
                "created_at": datetime.utcnow()
            }
        }},
        upsert=True
    )

    try:
        send_otp_email(data.email, otp, data.firstname)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send OTP email: {str(e)}")

    return {"message": "OTP sent to email"}

# ============================================================
# STEP 2 — Verify OTP and create user
# ============================================================
@router.post("/signup/verify-otp")
def signup_verify_otp(data: SignupVerifyOtpRequest):
    record = otp_col.find_one({"email": data.email.lower()})

    if not record:
        raise HTTPException(status_code=400, detail="No OTP found for this email. Please request again.")

    if datetime.utcnow() > record["expires_at"]:
        otp_col.delete_one({"email": data.email.lower()})
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")

    if record["otp"] != data.otp.strip():
        raise HTTPException(status_code=400, detail="Invalid OTP")

    pending = record["pending_user"]

    # Final duplicate check
    if users.find_one({"$or": [{"username": pending["username"]}, {"email": pending["email"]}]}):
        raise HTTPException(status_code=400, detail="User already exists")

    users.insert_one(pending)
    otp_col.delete_one({"email": data.email.lower()})

    return {"message": "Account created successfully"}
# ============================================================
# LOGIN  (FIXED with role + email)
# ============================================================
@router.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    recaptcha_token: str = Form(...)
):

    if not verify_recaptcha(recaptcha_token, "login"):
        raise HTTPException(status_code=401, detail="reCAPTCHA validation failed")

    user = users.find_one({"$or": [{"username": username}, {"email": username}]} )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username/email")

    if not verify_and_migrate_password(user, password):
        raise HTTPException(status_code=401, detail="Invalid password")

    token = create_token({
        "username": user["username"],
        "email": user.get("email"),
        "role": user.get("role", "user")
    })

    now = datetime.utcnow()
    sessions_col.insert_one({
        "username": user["username"],
        "email": user.get("email"),
        "role": user.get("role", "user"),
        "ts": int(now.timestamp() * 1000),
        "logged_at": now,
        "login_method": "password"
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "email": user.get("email"),
        "role": user.get("role", "user")
    }


# ============================================================
# LOGOUT
# ============================================================
@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):
    print(f"[LOGOUT] {current_user.get('username')} logged out")
    return {"message": "Logged out"}


# ============================================================
# reCAPTCHA DEBUG
# ============================================================
@router.post("/public/recaptcha-verify")
def debug_verify_recaptcha(token: str = Form(...), action: str = Form(None)):
    ok = verify_recaptcha(token, action)
    return {"verified": bool(ok)}


# ============================================================
# GOOGLE LOGIN (Auto-create)
# ============================================================
@router.post("/auth/google")
def auth_google(payload: dict = Body(...)):

    token = payload.get("token")
    recaptcha_token = payload.get("recaptcha_token", "")

    if not token:
        raise HTTPException(400, "Missing Google token")

    if not verify_recaptcha(recaptcha_token, "login"):
        raise HTTPException(401, "reCAPTCHA validation failed")

    try:
        google_req = GoogleRequest()
        idinfo = id_token.verify_oauth2_token(token, google_req, GOOGLE_CLIENT_ID)
    except Exception as e:
        raise HTTPException(400, f"Invalid Google token: {str(e)}")

    email = idinfo.get("email")
    if not email:
        raise HTTPException(400, "Google account has no email")

    if not idinfo.get("email_verified", False):
        raise HTTPException(400, "Google email not verified")

    fullname = idinfo.get("name", "")
    picture = idinfo.get("picture", "")
    google_sub = idinfo.get("sub")
    username = email.split("@")[0]

    user = users.find_one({"email": email})

    if not user:
        new_user = {
            "email": email,
            "username": username,
            "fullname": fullname,
            "picture": picture,
            "google_sub": google_sub,
            "auth_provider": "google",
            "password": None,
            "role": "user",
            "created_at": datetime.utcnow()
        }
        users.insert_one(new_user)
        user = new_user
    else:
        update_data = {}
        if user.get("auth_provider") != "google":
            update_data["auth_provider"] = "google"
        if user.get("google_sub") != google_sub:
            update_data["google_sub"] = google_sub
        if fullname and user.get("fullname") != fullname:
            update_data["fullname"] = fullname
        if picture and user.get("picture") != picture:
            update_data["picture"] = picture

        if update_data:
            users.update_one({"_id": user["_id"]}, {"$set": update_data})
            user = users.find_one({"_id": user["_id"]})

    jwt_token = create_token({
        "username": user["username"], # type: ignore
        "email": user["email"], # type: ignore
        "role": user.get("role", "user") # type: ignore
    })

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "username": user["username"], # type: ignore
        "email": user.get("email"), # type: ignore
        "role": user.get("role", "user"), # type: ignore
        "fullname": user.get("fullname", ""), # type: ignore
        "picture": user.get("picture", "") # type: ignore
    }
# ============================================================
# UPDATE PROFILE
# ============================================================
class ProfileUpdateRequest(BaseModel):
    firstname:  Optional[str] = None
    lastname:   Optional[str] = None
    bio:        Optional[str] = None
    phone:      Optional[str] = None
    department: Optional[str] = None
    city:       Optional[str] = None
    country:    Optional[str] = None

@router.patch("/user/profile")
def update_profile(
    data: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    update_fields = {k: v for k, v in data.dict().items() if v is not None}

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    users.update_one(
        {"_id": current_user["_id"] if isinstance(current_user["_id"], ObjectId) else ObjectId(current_user["_id"])},
        {"$set": update_fields}
    )

    return {"message": "Profile updated successfully"}
@router.get("/user/profile")
def get_profile(current_user: dict = Depends(get_current_user)):
    return {
        "username":    current_user["username"],
        "email":       current_user.get("email"),
        "role":        current_user.get("role", "user"),
        "firstname":   current_user.get("firstname", ""),   # ← add
        "lastname":    current_user.get("lastname", ""),    # ← add
        "bio":         current_user.get("bio", ""),         # ← add
        "phone":       current_user.get("phone", ""),       # ← add
        "department":  current_user.get("department", ""),  # ← add
        "city":        current_user.get("city", ""),        # ← add
        "country":     current_user.get("country", ""),     # ← add
        "auth_provider": current_user.get("auth_provider", "email"),  # ← add
        "created_at":  str(current_user.get("created_at", ""))
    }
# ============================================================
# CHANGE PASSWORD
# ============================================================
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/user/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    # Verify current password
    if not verify_and_migrate_password(current_user, data.current_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Validate new password strength
    if not validate_password(data.new_password):
        raise HTTPException(
            status_code=400,
            detail="Weak password. Min 8 chars with uppercase, lowercase, digit and special character (!@#$%^&*)"
        )

    # Hash and save new password
    new_hash = pbkdf2_hash(data.new_password)
    users.update_one(
        {"_id": current_user["_id"] if isinstance(current_user["_id"], ObjectId) else ObjectId(current_user["_id"])},
        {"$set": {"password": new_hash}}
    )

    return {"message": "Password updated successfully"}

# ============================================================
# DATA EXPORT — sends user data to their email
# ============================================================
@router.post("/user/export-data")
def export_data(current_user: dict = Depends(get_current_user)):
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="No email on file")

    username = current_user.get("username", "")

    # Gather user's shipments and devices
    my_shipments = list(shipments.find({"created_by": username}, {"_id": 0}))
    my_devices   = list(devices.find({"created_by": username}, {"_id": 0}))

    # Build plain-text summary
    shipment_lines = "\n".join(
        [f"  - {s.get('shipment_id','?')} | {s.get('status','?')} | {s.get('created_at','')}" for s in my_shipments]
    ) or "  No shipments found."

    device_lines = "\n".join(
        [f"  - {d.get('device_id','?')} | {d.get('name','?')}" for d in my_devices]
    ) or "  No devices found."

    body = f"""
Hi {username},

Here is your SCMXpertLite account data export:

# ============================================================
# USER PROFILE
# ============================================================
Username   : {username}
Email      : {email}
Role       : {current_user.get("role", "user")}
First Name : {current_user.get("firstname", "—")}
Last Name  : {current_user.get("lastname", "—")}
Joined     : {current_user.get("created_at", "—")}

# ============================================================
# SHIPMENTS ({len(my_shipments)} total)
# ============================================================
{shipment_lines}

# ============================================================
# DEVICES ({len(my_devices)} total)
# ============================================================
{device_lines}

# ============================================================
# DATA EXPORT — sends user data to their email
# ============================================================
This export was requested from your account settings.
— SCMXpertLite Team
"""

    try:
        msg = MIMEMultipart()
        msg["Subject"] = "SCMXpertLite — Your Data Export"
        msg["From"]    = MAIL_FROM # type: ignore
        msg["To"]      = email
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as smtp: # type: ignore
            smtp.starttls()
            smtp.login(MAIL_FROM, MAIL_PASSWORD) # type: ignore
            smtp.sendmail(MAIL_FROM, email, msg.as_string()) # type: ignore

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

    return {"message": "Data export sent to your email"}