from fastapi import APIRouter, Form, Depends, HTTPException
from pymongo import MongoClient
from datetime import datetime, timezone
from backend.user import get_current_user
import os
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

# ============================================================
# 🔌 DATABASE CONNECTION
# ============================================================
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

# Collection: sensor_readings (IoT data)
device_data_collection = db["sensor_readings"]


# ============================================================
# 1️⃣  FETCH UNIQUE DEVICE LIST   (Used in dropdown)
# ============================================================
@router.get("/devices/list")
def list_devices():

    pipeline = [
        {"$sort": {"timestamp": -1}},
        {"$group": {"_id": "$Device_ID"}},
        {"$project": {"device_id": "$_id", "_id": 0}}
    ]

    result = list(device_data_collection.aggregate(pipeline))
    return {"total": len(result), "devices": result}


# ============================================================
# 2️⃣  INSERT DEVICE DATA  (Manual + IoT ingestion)
# ============================================================
@router.post("/device-data")
def add_device_data(
    Device_ID: str = Form(...),
    Battery_Level: str = Form(...),
    First_Sensor_temperature: str = Form(...),
    Route_From: str = Form(...),
    Route_To: str = Form(...),
    timestamp: str = Form(default_factory=lambda: datetime.now(timezone.utc).isoformat()),
    current_user: dict = Depends(get_current_user)
):

    doc = {
        "Device_ID": Device_ID,
        "Battery_Level": Battery_Level,
        "First_Sensor_temperature": First_Sensor_temperature,
        "Route_From": Route_From,
        "Route_To": Route_To,
        "timestamp": timestamp,
        "created_by": current_user["username"],
        "created_at": datetime.utcnow()
    }

    device_data_collection.insert_one(doc)
    return {"message": "Device data stored successfully"}


# ============================================================
# 3️⃣  FETCH LIVE STREAM DATA FOR A DEVICE
# ============================================================
@router.get("/device-data/{device_id}")
def get_device_data(device_id: str):

    # Support both Device_ID and device_id (Kafka vs Form input)
    query = {
        "$or": [
            {"Device_ID": device_id},
            {"device_id": device_id}
        ]
    }

    # Latest 50 records
    records = list(
        device_data_collection
        .find(query, {"_id": 0})
        .sort("_id", -1)
        .limit(50)
    )

    if not records:
        raise HTTPException(404, "No data found for this device")

    return records
