from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from dotenv import load_dotenv
from pathlib import Path
import requests
from fastapi import HTTPException
import os
import logging
import sys

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

import user
import shipment_data
import device_data
import admin_privileges
import role_management
# -------------------- ENV + DATABASE --------------------
load_dotenv()
logging.basicConfig(level=logging.INFO)
# -------------------- FASTAPI APP ------------------------
app = FastAPI(title="SCMXpertLite Backend", version="1.0.0")

app.include_router(user.router)
app.include_router(shipment_data.router)
app.include_router(device_data.router)
app.include_router(admin_privileges.router)
app.include_router(role_management.router)

# -------------------- CORS ------------------------
origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- FRONTEND PATH ------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# serve the entire frontend folder at /frontend/...
app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

# Utility: load any html file by name
def page(name: str):
    return FileResponse(FRONTEND_DIR / name)


# -------------------- PAGE ROUTES (FRIENDLY URLS) ------------------------

@app.get("/")
def home_page():
    return page("user.html")     # default page is login/signup


@app.get("/login")
def login_page():
    return page("user.html")


@app.get("/dashboard")
def dashboard_page():
    return page("dashboard.html")


@app.get("/shipments")
def shipments_page():
    return page("shipments.html")


@app.get("/create-shipment")
def create_shipment_page():
    return page("shipment_data.html")


@app.get("/device-data")
def device_data_page():
    return page("device_data.html")


@app.get("/logout")
def logout_page():
    return page("logout.html")


@app.get("/ping")
def ping():
    return {"status": "ok"}


@app.get("/public/recaptcha-site-key")
def get_recaptcha_key():
    return {"site_key": os.getenv("RECAPTCHA_SITE_KEY")}
