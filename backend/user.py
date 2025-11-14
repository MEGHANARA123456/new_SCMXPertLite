from fastapi import APIRouter, Form, HTTPException, Depends
from pydantic import EmailStr, BaseModel, Field
from jose import jwt, JWTError
from typing import Union, Optional, Dict, Any
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
import os, hashlib, random, re, logging

load_dotenv()
router = APIRouter()

# ---------------------------
# ENV / CONFIG
# ---------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

# Strict validation: fail fast with a clear error if Mongo configuration is missing.
if not MONGO_URI or not MONGO_DB:
    raise RuntimeError(
        "MONGO_URI and MONGO_DB must be set in environment or .env before importing backend.user"
    )

# Create a Mongo client for this module (main also creates one for app-level checks).
try:
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    users_collection = db["users"]
except Exception as e:
    raise RuntimeError(f"Failed to connect to MongoDB: {e}")

# In-memory OTP store
otp_store = {}

# ---------------------------
# Helper functions
# ---------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def validate_password(password: str) -> bool:
    return (
        len(password) >= 8
        and re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"[0-9]", password)
        and re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
    )

def create_access_token(data: dict, expires_delta=None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ---------------------------
# Routes
# ---------------------------

@router.post("/signup")
def signup(username: str = Form(...), email: EmailStr = Form(...),
           password: str = Form(...), confirm_password: str = Form(...)):
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if not validate_password(password):
        raise HTTPException(status_code=400, detail="Weak password. Use upper, lower, number, special char.")
    if users_collection.find_one({"$or": [{"username": username}, {"email": email}]}):
        raise HTTPException(status_code=400, detail="Username or email already exists")

    users_collection.insert_one({
        "username": username,
        "email": email,
        "password": hash_password(password),
    })
    return {"message": f"Signup successful for {username}"}


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    username_or_email = form_data.username
    password = form_data.password

    user = users_collection.find_one({
        "$or": [
            {"username": username_or_email},
            {"email": username_or_email}
        ]
    })

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if hash_password(password) != user["password"]:
        raise HTTPException(status_code=401, detail="Invalid password")

    token = create_access_token({"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}


# ---------------------------
# Forgot Password (OTP)
# ---------------------------

@router.post("/forgot-password")
def forgot_password(email: EmailStr = Form(...)):
    """Generates a 6-digit OTP and stores it temporarily (valid for 5 minutes)."""
    user = users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp = str(random.randint(100000, 999999))
    expiry = datetime.utcnow() + timedelta(minutes=5)
    otp_store[email] = {"otp": otp, "expiry": expiry}

    return {
        "message": f"OTP generated for {email}",
        "otp": otp,
        "valid_for_minutes": 5
    }

@router.post("/reset-password")
def reset_password(
    email: EmailStr = Form(...),
    otp: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    """Verifies OTP and resets the user's password."""
    entry = otp_store.get(email)
    if not entry:
        raise HTTPException(status_code=400, detail="No OTP found for this email. Request again.")
    if datetime.utcnow() > entry["expiry"]:
        del otp_store[email]
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")
    if entry["otp"] != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP.")
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    if not validate_password(new_password):
        raise HTTPException(status_code=400, detail="Weak password format.")

    users_collection.update_one(
        {"email": email},
        {"$set": {"password": hash_password(new_password)}}
    )
    del otp_store[email]
    return {"message": "Password reset successful. You can now log in with your new password."}