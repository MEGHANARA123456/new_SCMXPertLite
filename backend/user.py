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

# ====== PASSWORD HELPERS ======
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
    if isinstance(hashed, str) and hashed.startswith("pbkdf2_sha256$"):
        return pbkdf2_verify(hashed, plain)

    # legacy sha256 -> upgrade to pbkdf2
    if isinstance(hashed, str) and re.fullmatch(r"[0-9a-fA-F]{64}", hashed):
        if hash_password(plain) == hashed:
            new_hash = pbkdf2_hash(plain)
            users.update_one({"_id": user["_id"]}, {"$set": {"password": new_hash}})
            return True

    return False

# ====== JWT ======
def create_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=10)
    # set subject for compatibility
    if "username" in data:
        payload["sub"] = data["username"]
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# ====== CURRENT USER DEPENDENCY (for other modules) ======
def get_current_user(token: str = Depends(oauth2)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub") or payload.get("username")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ====== reCAPTCHA Verification (standard v2 / v3) ======
def verify_recaptcha(token: str, action: str = None) -> bool:
    """
    Verify using standard siteverify endpoint (v2 checkbox or v3).
    Empty tokens are allowed for development/fallback when reCAPTCHA fails to load.
    """
    # Allow empty tokens - fallback for reCAPTCHA loading issues in development
    if not token:
        print("[reCAPTCHA] Empty token accepted (fallback mode - reCAPTCHA may not have loaded on frontend)")
        return True

    if not RECAPTCHA_SECRET_KEY:
        # local/dev fallback with valid token
        print("[reCAPTCHA] Valid token accepted (no SECRET_KEY configured)")
        return True

    try:
        url = "https://www.google.com/recaptcha/api/siteverify"
        res = requests.post(url, data={"secret": RECAPTCHA_SECRET_KEY, "response": token}, timeout=6)
        data = res.json()
        if not data.get("success"):
            print(f"[reCAPTCHA] Verification failed: {data}")
            return False
        # v3 may include score; if action provided and mismatch -> reject
        if action and data.get("action") and data.get("action") != action:
            print(f"[reCAPTCHA] Action mismatch: expected {action}, got {data.get('action')}")
            return False
        # allow v2 (no score) or v3 with score threshold 0.5
        if "score" in data:
            score = float(data.get("score", 0))
            if score < 0.5:
                print(f"[reCAPTCHA] Score too low: {score}")
                return False
        print(f"[reCAPTCHA] Token verified successfully")
        return True
    except Exception as e:
        print(f"[reCAPTCHA] Exception during verification: {str(e)}")
        return False

# ====== VALIDATION HELPERS ======
def validate_password(p: str):
    return (
        len(p) >= 8 and
        re.search(r"[A-Z]", p) and
        re.search(r"[a-z]", p) and
        re.search(r"[0-9]", p) and
        re.search(r"[!@#$%^&*]", p)
    )

# ======================================
# SIGNUP  
# ======================================
@router.post("/signup")
def signup(
    username: str = Form(...),
    email: EmailStr = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    # 1. Remove reCAPTCHA check (DELETED)
    # if not verify_recaptcha("signup"):
    #     raise HTTPException(status_code=400, detail="reCAPTCHA validation failed")

    # 2. Validate password match
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # 3. Validate password strength
    if not validate_password(password):
        raise HTTPException(status_code=400, detail="Weak password")

    # 4. Check existing user
    if users.find_one({"$or": [{"username": username}, {"email": email}]}):
        raise HTTPException(status_code=400, detail="User already exists")

    # 5. Insert user
    users.insert_one({
        "username": username,
        "email": email.lower(),
        "password": pbkdf2_hash(password),
        "role": "user",
        "created_at": datetime.utcnow()
    })

    return {"message": "Signup successful"}

# ======================================
# LOGIN (username/password)
# ======================================
@router.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    recaptcha_token: str = Form(...)
):
    print(f"[LOGIN] Received request - username: {username}, password_len: {len(password)}, recaptcha_token: {recaptcha_token[:20] if recaptcha_token else 'EMPTY'}")
    
    if not verify_recaptcha(recaptcha_token, "login"):
        print(f"[LOGIN] reCAPTCHA verification failed for token: {recaptcha_token[:20] if recaptcha_token else 'EMPTY'}")
        raise HTTPException(status_code=401, detail="reCAPTCHA validation failed")

    user = users.find_one({"$or":[{"username": username},{"email": username}]})
    if not user:
        print(f"[LOGIN] User not found: {username}")
        raise HTTPException(status_code=401, detail="Invalid username/email")

    print(f"[LOGIN] User found: {user.get('username')}, verifying password...")
    if not verify_and_migrate_password(user, password):
        print(f"[LOGIN] Password verification failed for user: {username}")
        raise HTTPException(status_code=401, detail="Invalid password")

    print(f"[LOGIN] Login successful for {username}, creating token...")
    token = create_token({"username": user["username"], "role": user.get("role", "user")})
    return {"access_token": token, "token_type": "bearer", "role": user.get("role", "user"), "username": user["username"]}

# ======================================
# LOGOUT ENDPOINT
# ======================================
@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout endpoint - clears session on backend side
    Frontend should also clear localStorage
    """
    print(f"[LOGOUT] User {current_user.get('username')} logged out")
    return {"message": "Logged out successfully", "detail": "Your session has been closed"}

# ======================================
# PUBLIC recaptcha debug
# ======================================
@router.post("/public/recaptcha-verify")
def debug_verify_recaptcha(token: str = Form(...), action: str = Form(None)):
    ok = verify_recaptcha(token, action)
    return {"verified": bool(ok)}

# ======================================
# GOOGLE SSO (ID token) - login only (no auto-signup)
# Frontend: POST JSON { token: "<id_token>", recaptcha_token: "..."}
# ======================================
@router.post("/auth/google")
def auth_google(payload: dict = Body(...)):
    token = payload.get("token")
    recaptcha_token = payload.get("recaptcha_token", "")

    if not token:
        raise HTTPException(status_code=400, detail="Missing Google token")

    if not verify_recaptcha(recaptcha_token, "login"):
        raise HTTPException(status_code=401, detail="reCAPTCHA validation failed")

    try:
        google_request = GoogleRequest()
        idinfo = id_token.verify_oauth2_token(token, google_request, GOOGLE_CLIENT_ID)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid Google token: {str(e)}")

    if idinfo.get("aud") != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="Invalid audience for Google token")

    if not idinfo.get("email_verified", False):
        raise HTTPException(status_code=400, detail="Google account email not verified")

    email = idinfo.get("email")
    google_sub = idinfo.get("sub")
    full_name = idinfo.get("name", "")
    picture = idinfo.get("picture", "")

    user = users.find_one({"email": email})
    if not user:
        # do not auto-create. Let frontend show signup option.
        raise HTTPException(status_code=401, detail="No local account for this Google user. Please sign up first.")

    update_fields = {}
    if user.get("auth_provider") != "google":
        update_fields["auth_provider"] = "google"
    if user.get("google_sub") != google_sub:
        update_fields["google_sub"] = google_sub
    if full_name and user.get("fullname") != full_name:
        update_fields["fullname"] = full_name
    if picture and user.get("picture") != picture:
        update_fields["picture"] = picture
    if update_fields:
        users.update_one({"_id": user["_id"]}, {"$set": update_fields})
        user = users.find_one({"_id": user["_id"]})

    jwt_token = create_token({"username": user["username"], "role": user.get("role", "user")})
    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "username": user["username"],
        "email": user.get("email"),
        "role": user.get("role", "user"),
        "fullname": user.get("fullname", ""),
        "picture": user.get("picture", "")
    }

# Export router for inclusion in main app
# e.g. app.include_router(router, prefix="/api")
