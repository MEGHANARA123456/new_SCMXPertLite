from fastapi import APIRouter, Form, HTTPException, Depends, Request
from pydantic import EmailStr
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
import os, hashlib, random, re
import base64, hmac
import requests

load_dotenv()
router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# ===== reCAPTCHA configuration (Enterprise or standard) =====
# Support multiple env var names for convenience
RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY") or os.getenv("RECAPTCHA_SITEKEY")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY") or os.getenv("YOUR_RECAPTCHA_SECURITY_KEY")
RECAPTCHA_PROJECT_ID = os.getenv("RECAPTCHA_PROJECT_ID")


def verify_recaptcha(token: str, action: str):
    """Verify reCAPTCHA token.
    - If `RECAPTCHA_PROJECT_ID` is set we attempt reCAPTCHA Enterprise assessment.
    - Otherwise if `RECAPTCHA_SECRET_KEY` is set we call the standard siteverify API.
    - If no secret is configured, verification is skipped (useful for local dev).
    Returns True when verification passes, False otherwise.
    """
    if not token:
        return False

    # 1) Enterprise path
    if RECAPTCHA_PROJECT_ID and RECAPTCHA_SECRET_KEY:
        try:
            url = (
                f"https://recaptchaenterprise.googleapis.com/v1/projects/"
                f"{RECAPTCHA_PROJECT_ID}/assessments?key={RECAPTCHA_SECRET_KEY}"
            )
            payload = {
                "event": {"token": token, "expectedAction": action, "siteKey": RECAPTCHA_SITE_KEY}
            }
            res = requests.post(url, json=payload, timeout=5)
            data = res.json()
            # basic checks
            if not data.get("tokenProperties", {}).get("valid"):
                return False
            score = data.get("riskAnalysis", {}).get("score", 0)
            return score >= 0.5
        except Exception:
            return False

    # 2) Standard reCAPTCHA siteverify (v2/v3)
    if RECAPTCHA_SECRET_KEY:
        try:
            url = "https://www.google.com/recaptcha/api/siteverify"
            res = requests.post(url, data={"secret": RECAPTCHA_SECRET_KEY, "response": token}, timeout=5)
            data = res.json()
            # data = { success: bool, score: float (v3), action: str, ... }
            if not data.get("success"):
                return False
            # if v3, we can check score and action
            if "score" in data:
                if data.get("action") and data.get("action") != action:
                    return False
                return float(data.get("score", 0)) >= 0.5
            return True
        except Exception:
            return False

    # 3) No recaptcha configured — allow (development)
    return True

# ==== MONGO ====
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
users = db["user"]
oauth2 = OAuth2PasswordBearer(tokenUrl="login")
otp_store = {}

# ========================
# PASSWORD UTILITIES
# ========================

def hash_password(p):
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

def verify_and_migrate_password(user, plain):
    hashed = user.get("password", "")

    # pbkdf2
    if isinstance(hashed, str) and hashed.startswith("pbkdf2_sha256$"):
        return pbkdf2_verify(hashed, plain)

    # legacy SHA256
    if isinstance(hashed, str) and re.fullmatch(r"[0-9a-fA-F]{64}", hashed):
        if hash_password(plain) == hashed:
            new_hash = pbkdf2_hash(plain)
            users.update_one({"_id": user["_id"]}, {"$set": {"password": new_hash}})
            return True

    return False

# ========================
# TOKEN
# ========================

def create_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=10)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def validate_password(p):
    return (
        len(p) >= 8 and
        re.search(r"[A-Z]", p) and
        re.search(r"[a-z]", p) and
        re.search(r"[0-9]", p) and
        re.search(r"[!@#$%^&*]", p)
    )

def get_current_user(token: str = Depends(oauth2)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub") or payload.get("username")
    except:
        raise HTTPException(401, "Invalid or expired token")

    user = users.find_one({"username": username})
    if not user:
        raise HTTPException(401, "User not found")
    return user

# ========================
# SIGNUP
# ========================

@router.post("/signup")
def signup(
    username: str = Form(...),
    email: EmailStr = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    recaptcha_token: str = Form(...),
    recaptcha_action: str = Form(...)
):

    #  NEW: recaptcha verify
    if not verify_recaptcha(recaptcha_token, recaptcha_action):
        raise HTTPException(400, "reCAPTCHA validation failed")

    if password != confirm_password:
        raise HTTPException(400, "Passwords do not match")

    if not validate_password(password):
        raise HTTPException(400, "Weak password format")

    if users.find_one({"$or": [{"username": username}, {"email": email}]}):
        raise HTTPException(400, "User already exists")

    users.insert_one({
        "username": username,
        "email": email,
        "password": pbkdf2_hash(password),
        "role": "user",
        "created_at": datetime.utcnow()
    })
    return {"message": "Signup successful"}

# ========================
# LOGIN
# ========================

@router.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    recaptcha_token: str = Form(...),
    recaptcha_action: str = Form(...)
):

    #  NEW: recaptcha verify
    if not verify_recaptcha(recaptcha_token, recaptcha_action):
        raise HTTPException(401, "reCAPTCHA validation failed")

    user = users.find_one(
        {"$or": [
            {"username": username},
            {"email": username}
        ]}
    )

    if not user:
        raise HTTPException(401, "Invalid username/email")

    if not verify_and_migrate_password(user, password):
        raise HTTPException(401, "Invalid password")

    token = create_token({"username": user["username"], "role": user["role"]})

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "username": user["username"]
    }


@router.post("/public/recaptcha-verify")
def debug_verify_recaptcha(token: str = Form(...), action: str = Form(...)):
    """Debug endpoint: POST a recaptcha token+action to verify server-side.
    Returns JSON { verified: bool } so you can test tokens acquired from the browser.
    """
    ok = verify_recaptcha(token, action)
    return {"verified": bool(ok)}
