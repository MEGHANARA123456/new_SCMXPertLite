from fastapi import APIRouter, Form, Depends, HTTPException, Body
from pymongo import MongoClient
from datetime import datetime
from backend.auth_utils import get_current_user
from pydantic import BaseModel, Field, validator
import os
from datetime import date, datetime
import re
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB_APP")
client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
shipments_collection = db["shipments"]

class ShipmentCreate(BaseModel):
    shipment_number: str = Field(..., min_length=1, max_length=50)
    route_from: str = Field(..., min_length=2, max_length=50)
    route_to: str = Field(..., min_length=2, max_length=50)
    device: str = Field(..., min_length=1, max_length=80)
    po_number: str = Field(..., min_length=1, max_length=50)
    ndc_number: str = Field(..., min_length=1, max_length=100)
    serial_number_goods: str = Field(..., min_length=1, max_length=80)

    shipment_priority: str = Field(..., pattern="^(high|medium|low)$")
    shipment_health: str = Field(..., pattern="^(high|medium|low)$")

    container_number: str = Field(..., min_length=3, max_length=50)
    goods_type: str = Field(..., min_length=2, max_length=50)

    expected_delivery_date: date

    delivery_number: str = Field(..., min_length=1, max_length=50)
    batch_id: str = Field(..., min_length=1, max_length=50)

    shipment_description: str | None = Field(default="", max_length=300)


    # -------------------------
    #   CUSTOM VALIDATORS
    # -------------------------

    @validator(
        "shipment_number", "route_from", "route_to", "device",
        "po_number", "ndc_number", "serial_number_goods",
        "container_number", "goods_type", "delivery_number",
        "batch_id", pre=True
    )
    def no_empty_strings(cls, v):
        """Prevent empty strings and trim spaces."""
        if isinstance(v, str):
            v = v.strip()
        if not v:
            raise ValueError("This field cannot be empty.")
        return v


    @validator("expected_delivery_date")
    def validate_date(cls, v):
        """Ensure expected date is not in the past."""
        if v < date.today():
            raise ValueError("Expected delivery date cannot be in the past.")
        return v


    @validator("route_from", "route_to")
    def letters_only(cls, v):
        """Ensure route locations contain only letters (basic validation)."""
        if not re.match(r"^[A-Za-z ]+$", v):
            raise ValueError("Route fields must contain only letters.")
        return v


    @validator("ndc_number")
    def ndc_format(cls, v):
        """Allow digits, hyphens. Example: 12345-6789-12"""
        if not re.match(r"^[0-9\-]+$", v):
            raise ValueError("NDC number must contain only numbers and hyphens.")
        return v


    @validator("po_number", "container_number", "delivery_number")
    def alphanumeric(cls, v):
        """Allow alphanumeric + hyphens."""
        if not re.match(r"^[A-Za-z0-9\-]+$", v):
            raise ValueError("This field must be alphanumeric (letters/numbers/hyphens).")
        return v

@router.post("/api/shipments/create")
def create_shipment(
    shipment: ShipmentCreate = Body(...),
    current_user: dict = Depends(get_current_user)
):

    # Convert date → datetime
    shipment_dt = datetime.combine(shipment.expected_delivery_date, datetime.min.time())

    doc = shipment.dict()
    doc["expected_delivery_date"] = shipment_dt  # FIXED HERE

    # Add metadata
    doc.update({
        "created_by": current_user["username"],
        "created_at": datetime.utcnow()
    })

    shipments_collection.insert_one(doc)

    return {"message": "Shipment created successfully"}

@router.get("/api/shipments")
def get_all_shipments(current_user: dict = Depends(get_current_user)):
    records = list(shipments_collection.find().sort("created_at", -1))

    # Convert MongoDB objects to JSON-safe
    output = []
    for r in records:
        output.append({
            "shipment_number": r.get("shipment_number"),
            "container_number": r.get("container_number"),
            "route_from": r.get("route_from"),
            "route_to": r.get("route_to"),
            "goods_type": r.get("goods_type"),
            "expected_delivery_date": r.get("expected_delivery_date"),
            "created_at": r.get("created_at"),
        })

    return {"records": output}
@router.get("/api/shipments")
def list_shipments(current_user: dict = Depends(get_current_user)):
    records = list(shipments_collection.find({}, {"_id": 0}))
    return {"records": records}
