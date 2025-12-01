# backend/shipments.py
from fastapi import APIRouter, Form, Depends, HTTPException, Body
from pymongo import MongoClient
from datetime import datetime
from backend.auth_utils import get_current_user
from pydantic import BaseModel
import os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB_APP")
client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
shipments_collection = db["shipments"]


class ShipmentCreate(BaseModel):
    shipment_number: str
    container_number: str
    route_from: str
    route_to: str
    goods_type: str
    expected_delivery_date: str
    po_number: str
    ndc_number: str
    serial_number_goods: str
    delivery_number: str
    batch_id: str
    shipment_description: str
    device: str


@router.post("/api/shipments/create")
def create_shipment(shipment: ShipmentCreate = Body(...), current_user: dict = Depends(get_current_user)):
    shipment_number = shipment.shipment_number
    if shipments_collection.find_one({"shipment_number": shipment_number}):
        raise HTTPException(400, "Shipment number already exists")

    doc = shipment.dict()
    doc.update({"created_by": current_user["username"], "created_at": datetime.utcnow()})

    shipments_collection.insert_one(doc)
    return {"message": "Shipment created successfully"}


@router.get("/api/shipments")
def get_shipments():
    data = list(shipments_collection.find({}, {"_id": 0}))
    return {"total": len(data), "shipments": data}