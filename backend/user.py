# backend/user.py
from fastapi import APIRouter, Form, HTTPException, Depends, Body
from pydantic import EmailStr
from jose import jwt
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
import os, hashlib, re, base64, hmac, requests
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token

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
MAIL_PORT = int(os.getenv("MAIL_PORT"))
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_APP]
users = db["user"]
otp_col = db["otp_store"]
oauth2 = OAuth2PasswordBearer(tokenUrl="login")


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

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ============================================================
# CURRENT USER FIX (returns role always)
# ============================================================
def get_current_user(token: str = Depends(oauth2)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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
def verify_recaptcha(token: str, action: str = None) -> bool:

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
# SIGNUP
# ============================================================
@router.post("/signup")
def signup(
    username: str = Form(...),
    email: EmailStr = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):

    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if not validate_password(password):
        raise HTTPException(status_code=400, detail="Weak password")

    if users.find_one({"$or": [{"username": username}, {"email": email}]}):
        raise HTTPException(status_code=400, detail="User already exists")

    users.insert_one({
        "username": username,
        "email": email.lower(),
        "password": pbkdf2_hash(password),
        "role": "user",
        "created_at": datetime.utcnow()
    })

    return {"message": "Signup successful"}


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
        "username": user["username"],
        "email": user["email"],
        "role": user.get("role", "user")
    })

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "username": user["username"],
        "email": user.get("email"),
        "role": user.get("role", "user"),
        "fullname": user.get("fullname", ""),
        "picture": user.get("picture", "")
    }
