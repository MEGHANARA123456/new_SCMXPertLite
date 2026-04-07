from fastapi import APIRouter, Form, Depends, HTTPException, Body
from pymongo import MongoClient
from datetime import datetime,date
from bson import ObjectId
from auth_utils import get_current_user
from pydantic import BaseModel, Field, validator
import os,re
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB_APP")
client = MongoClient(MONGO_URI)
db = client[MONGO_DB] # type: ignore
shipments_collection = db["shipments"]

class ShipmentCreate(BaseModel):
    shipment_number: str = Field(..., pattern="^[0-9]{6}$")
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
    @validator("container_number")
    def alphanumeric(cls, v): # type: ignore
        """Allow alphanumeric + hyphens."""
        if not re.match(r"^[A-Za-z0-9\-]+$", v):
            raise ValueError("Container number must be alphanumeric (letters/numbers/hyphens).")
        return v
    @validator("route_from", "route_to")
    def letters_only(cls, v): # type: ignore
        """Ensure route locations contain only letters (basic validation)."""
        if not re.match(r"^[A-Za-z ]+$", v):
            raise ValueError("Route fields must contain only letters.")
        return v
    @validator("shipment_number")
    def validate_shipment_number(cls, v):
        if not re.match(r"^[0-9]{6}$", v):
            raise ValueError("Shipment number must be exactly 6 digits.")
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
def create_shipment( # type: ignore
    shipment: ShipmentCreate = Body(...),
    current_user: dict = Depends(get_current_user)
):
    doc = shipment.dict()

    #Correct way to convert date → datetime
    if isinstance(doc.get("expected_delivery_date"), date):
        doc["expected_delivery_date"] = datetime.combine(
            doc["expected_delivery_date"], datetime.min.time()
        )

    # Add metadata including user ownership
    doc.update({
        "created_by": current_user["username"],
        "user_email": current_user.get("email"),   # optional but useful
        "status": "active",                         # default status
        "created_at": datetime.utcnow()
    })

    result = shipments_collection.insert_one(doc)

    # Return the created shipment ID
    return {
        "message": "Shipment created successfully",
        "shipment_id": str(result.inserted_id)
    }

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

# ─────────────────────────────────────────
#  CREATE — any authenticated user
# ─────────────────────────────────────────
@router.post("/api/shipments/create")
def create_shipment(
    shipment: ShipmentCreate = Body(...),
    current_user: dict = Depends(get_current_user)
):
    doc = shipment.dict()
 
    # Convert date → datetime
    if isinstance(doc.get("expected_delivery_date"), date):
        doc["expected_delivery_date"] = datetime.combine(
            doc["expected_delivery_date"], datetime.min.time()
        )
 
    doc.update({
        "created_by": current_user["username"],
        "user_email": current_user.get("email"),
        "status": "active",
        "created_at": datetime.utcnow()
    })
 
    result = shipments_collection.insert_one(doc)
 
    return {
        "message": "Shipment created successfully",
        "shipment_id": str(result.inserted_id)
    }
 
 
# ─────────────────────────────────────────
#  READ — Role-based: user sees own, admin sees all
# ─────────────────────────────────────────
@router.get("/api/shipments")
def get_shipments(current_user: dict = Depends(get_current_user)):
    """
    Admin  → returns all shipments.
    User   → returns only shipments created by that user.
    """
    role = current_user.get("role", "user").lower()
 
    if role == "admin":
        records = list(shipments_collection.find().sort("created_at", -1))
    else:
        records = list(
            shipments_collection
            .find({"created_by": current_user["username"]})
            .sort("created_at", -1)
        )
 
    output = []
    for r in records:
        output.append({
            "shipment_number": r.get("shipment_number"),
            "container_number": r.get("container_number"),
            "route_from": r.get("route_from"),
            "route_to": r.get("route_to"),
            "goods_type": r.get("goods_type"),
            "expected_delivery_date": (
                r["expected_delivery_date"].strftime("%Y-%m-%d")
                if isinstance(r.get("expected_delivery_date"), datetime)
                else r.get("expected_delivery_date")
            ),
            "created_at": (
                r["created_at"].isoformat()
                if isinstance(r.get("created_at"), datetime)
                else r.get("created_at")
            ),
            "created_by": r.get("created_by"),
            "status": r.get("status", "active"),
            # Include editable fields so the frontend can populate the edit form
            "device": r.get("device"),
            "po_number": r.get("po_number"),
            "ndc_number": r.get("ndc_number"),
            "serial_number_goods": r.get("serial_number_goods"),
            "shipment_priority": r.get("shipment_priority"),
            "shipment_health": r.get("shipment_health"),
            "delivery_number": r.get("delivery_number"),
            "batch_id": r.get("batch_id"),
            "shipment_description": r.get("shipment_description"),
        })
 
    return {"records": output}
 
 
# ─────────────────────────────────────────
#  UPDATE — user can only edit own shipment; admin can edit any
# ─────────────────────────────────────────
@router.patch("/api/shipments/{shipment_number}")
def update_shipment(
    shipment_number: str,
    payload: ShipmentCreate = Body(...),
    current_user: dict = Depends(get_current_user)
):
    role = current_user.get("role", "user").lower()
 
    # Admins can update any shipment; users only their own
    query = {"shipment_number": shipment_number}
    if role != "admin":
        query["created_by"] = current_user["username"]
 
    existing = shipments_collection.find_one(query)
    if not existing:
        raise HTTPException(status_code=404, detail="Shipment not found or access denied")
 
    updates = {k: v for k, v in payload.dict().items() if v is not None}
 
    if "expected_delivery_date" in updates and isinstance(updates["expected_delivery_date"], date):
        updates["expected_delivery_date"] = datetime.combine(
            updates["expected_delivery_date"], datetime.min.time()
        )
 
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
 
    updates["updated_at"] = datetime.utcnow()
    shipments_collection.update_one(query, {"$set": updates})
 
    updated = shipments_collection.find_one({"shipment_number": shipment_number})
    return {"message": "Shipment updated successfully", "shipment": _serial(updated)}  # type: ignore
 
 
# ─────────────────────────────────────────
#  DELETE — user can only delete own; admin can delete any
# ─────────────────────────────────────────
@router.delete("/api/shipments/{shipment_number}")
def delete_shipment(
    shipment_number: str,
    current_user: dict = Depends(get_current_user)
):
    role = current_user.get("role", "user").lower()
 
    query = {"shipment_number": shipment_number}
    if role != "admin":
        query["created_by"] = current_user["username"]
 
    result = shipments_collection.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Shipment not found or access denied")
 
    return {"message": "Shipment deleted successfully"}