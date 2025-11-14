from fastapi import FastAPI
from dotenv import load_dotenv
from pymongo import MongoClient, errors
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import random, string, logging
from fastapi import Response
import os
from backend.db import client, db
from backend import user, shipment_data, device_data
load_dotenv()

logging.basicConfig(level=logging.INFO)

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

if not MONGO_URI or not MONGO_DB:
    raise RuntimeError("MONGO_URI and MONGO_DB must be set in .env file")

# client and db are imported from backend.db above

app = FastAPI(title="SCMXPertLite API")
# Routers
app.include_router(shipment_data.router)
app.include_router(device_data.router)
app.include_router(user.router)
# CORS
origins = [
    "http://127.0.0.1:5500",  #for frontend 5500
    "http://localhost:5500",
    "http://127.0.0.1:8000",   #for backend 8000  
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Frontend (compute absolute path relative to repo root)
frontend_path = Path(__file__).resolve().parent.parent / "frontend"
if frontend_path.exists() and frontend_path.is_dir():
    app.mount("/ui", StaticFiles(directory=str(frontend_path), html=True), name="ui")
else:
    logging.warning(f"Frontend directory not found at {frontend_path}. /ui will not be mounted.")

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "Backend running!"}


@app.on_event("startup")
async def startup_event():
    logging.info("Starting up: checking MongoDB connection...")
    try:
        # This will raise if the server is unreachable
        client.admin.command("ping")
        logging.info("MongoDB ping successful")
    except Exception as exc:
        logging.warning(f"MongoDB startup check failed (running in degraded mode): {exc}")


@app.on_event("shutdown")
async def shutdown_event():
    try:
        client.close()
        logging.info("MongoDB client closed")
    except Exception:
        pass