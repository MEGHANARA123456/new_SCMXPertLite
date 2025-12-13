from fastapi import APIRouter, Form, Depends, HTTPException
from pymongo import MongoClient
from datetime import datetime, timezone
from backend.auth_utils import get_current_user
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

# ============================================================
#  DATABASE CONNECTION
# ============================================================
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB_IOT")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

# Main IoT collection
device_data_collection = db["sensor_readings"]


# ============================================================
#  Utility: Convert _id to string
# ============================================================
def fix_id(record: dict):
    if "_id" in record:
        record["_id"] = str(record["_id"])
    return record


# ============================================================
# 1️ FETCH UNIQUE DEVICE LIST
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
# 2️ INSERT DEVICE DATA
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
# 3️  FETCH STREAM DATA FOR A DEVICE 
# ============================================================
@router.get("/device-data/recent")
def get_recent_data():
    try:
        print("DEBUG: Connecting to MongoDB...")
        print("DEBUG COLLECTION:", device_data_collection)

        records = list(
            device_data_collection
            .find({})
            .sort("timestamp", -1)
            .limit(50)
        )

        print("DEBUG RECORD COUNT:", len(records))

        final_records = []
        for r in records:
            final_records.append({
                "Device_ID": r.get("Device_ID", ""),
                "Battery_Level": r.get("Battery_Level", ""),
                "First_Sensor_temperature": r.get("First_Sensor_temperature", ""),
                "Route_From": r.get("Route_From", ""),
                "Route_To": r.get("Route_To", ""),
                "timestamp": r.get("timestamp", "")
            })

        return {"records": final_records}

    except Exception as e:
        print(" ERROR in /device-data/recent:", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/device-data/{device_id}")
def get_device_by_id(device_id: str):

    # Convert to int if possible (Mongo stores numbers, not strings)
    try:
        device_id = int(device_id)
    except ValueError:
        pass

    records = list(
        device_data_collection
        .find({"Device_ID": device_id})
        .sort("timestamp", -1)
    )

    final = []
    for r in records:
        final.append({
            "Device_ID": r.get("Device_ID", ""),
            "Battery_Level": r.get("Battery_Level", ""),
            "First_Sensor_temperature": r.get("First_Sensor_temperature", ""),
            "Route_From": r.get("Route_From", ""),
            "Route_To": r.get("Route_To", ""),
            "timestamp": r.get("timestamp", ""),
        })

    return {"records": final}


