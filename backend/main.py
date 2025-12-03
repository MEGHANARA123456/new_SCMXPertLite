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
import backend.auth_utils as auth_utils
import backend.models as models
import backend.forgetpassword as forgetpassword
import backend.user as user_module
# -------------------- ENV + DATABASE --------------------
load_dotenv()
logging.basicConfig(level=logging.INFO)
# -------------------- FASTAPI APP ------------------------
app = FastAPI(title="SCMXpertLite Backend", version="1.0.0")

# -------------------- ROUTERS ------------------------
app.include_router(forgetpassword.router)
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
from pathlib import Path

# main.py is inside /backend
# So parent.parent = project root
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

print("FRONTEND_DIR:", FRONTEND_DIR)  # DEBUG LINE

# serve static files
app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

def page(name: str):
    path = FRONTEND_DIR / name
    print("Loading page:", path)  # DEBUG LINE
    return FileResponse(path)


# -------------------- PAGE ROUTES (FRIENDLY URLS) ------------------------

@app.get("/")
async def root():
    return RedirectResponse("/frontend/user.html")      # default page is login/signup


@app.get("/login")
async def login_page():
    return RedirectResponse("/frontend/user.html")

@app.get("/admin")
async def admin_page():
    return RedirectResponse("/frontend/admin_dashboard.html")

@app.get("/dashboard")
async def dashboard_page():
    return RedirectResponse("/frontend/dashboard.html")

@app.get("/shipments")
async def shipments_page():
    return RedirectResponse("/frontend/shipments.html")

@app.get("/create-shipment")
async def create_shipment_page():
    return RedirectResponse("/frontend/shipment_data.html")

@app.get("/device-data")
async def device_data_page():
    return RedirectResponse("/frontend/device_data.html")

@app.get("/logout")
async def logout_page():
    return RedirectResponse("/frontend/logout.html")
