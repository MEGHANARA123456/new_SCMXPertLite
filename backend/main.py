from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from dotenv import load_dotenv
from pathlib import Path
import os
import logging
import sys
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend import db
import user
import shipments_da
import device_data
import admin_privileges
import role_management
import backend.auth_utils as auth_utils
import backend.db as db
import backend.models as models
import backend.forgetpassword as forgetpassword


load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="SCMXpertLite Backend", version="1.0.0")

#  CORS MUST come first — before routers and static mounts
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

# -------------------- ROUTERS ------------------------
app.include_router(forgetpassword.router)
app.include_router(user.router)
app.include_router(shipments_da.router)
app.include_router(device_data.router)
app.include_router(admin_privileges.router)
app.include_router(role_management.router)

# -------------------- FRONTEND PATH ------------------------
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
print("FRONTEND_DIR:", FRONTEND_DIR)

app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

# -------------------- PAGE ROUTES ------------------------

@app.get("/")
async def root():
    return RedirectResponse("/frontend/user.html", status_code=302)

@app.get("/login")
async def login_page():
    return RedirectResponse("/frontend/user.html", status_code=302)

@app.get("/admin")
async def admin_page():
    return RedirectResponse("/frontend/admin_dashboard.html", status_code=302)

@app.get("/dashboard")
async def dashboard_page():
    return RedirectResponse("/frontend/dashboard.html", status_code=302)

@app.get("/shipments")
async def shipments_page():
    return RedirectResponse("/frontend/shipments.html", status_code=302)

@app.get("/create-shipment")
async def create_shipment_page():
    return RedirectResponse("/frontend/shipment_data.html", status_code=302)

@app.get("/device-data")
async def device_data_page():
    return RedirectResponse("/frontend/device_data.html", status_code=302)

@app.get("/logout")
async def logout_page():
    return RedirectResponse("/frontend/logout.html", status_code=302)


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True  # optional but helpful during dev
    )