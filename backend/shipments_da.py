from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Body
from pymongo import MongoClient
from datetime import datetime, date, timezone
from auth_utils import get_current_user, require_role
from pydantic import BaseModel, Field, validator
import os, re
from dotenv import load_dotenv

from backend.models import ShipmentCreate, ShipmentUpdate
from backend.db import get_db
load_dotenv()

router = APIRouter()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB_APP")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB] # type: ignore
shipments_collection = db["shipments"]

def serialize_shipment(doc: dict) -> dict:
    """Convert MongoDB doc to API-friendly JSON-serializable dict."""
    doc["id"] = str(doc.pop("_id"))
    return doc
# =========================
# CREATE
# =========================
@router.post("/api/shipments/create")
def create_shipment( # type: ignore
    shipment: ShipmentCreate = Body(...),
    current_user: dict = Depends(get_current_user)
):
    doc = shipment.dict()

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
        "message": "Shipment created",
        "shipment_id": str(result.inserted_id)
    }


# =========================
# READ (GET ALL)
# =========================
@router.get("/api/shipments")
def get_shipments(current_user: dict = Depends(get_current_user)):

    role = current_user.get("role", "user").lower()

    if role == "admin":
        records = list(shipments_collection.find().sort("created_at", -1))
    else:
        records = list(
            shipments_collection.find(
                {"created_by": current_user["username"]}
            ).sort("created_at", -1)
        )

    output = []

    for r in records:
        output.append({
            "shipment_number": r.get("shipment_number"),
            "container_number": r.get("container_number"),
            "route_from": r.get("route_from"),
            "route_to": r.get("route_to"),
            "goods_type": r.get("goods_type"),
            "shipment_priority": r.get("shipment_priority"),
            "shipment_health":   r.get("shipment_health"),
            "device":            r.get("device"),
            "po_number":         r.get("po_number"),
            "ndc_number":        r.get("ndc_number"),
            "serial_number_goods": r.get("serial_number_goods"),
            "delivery_number":   r.get("delivery_number"),
            "batch_id":          r.get("batch_id"),
            "shipment_description": r.get("shipment_description"),
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
            "status": r.get("status"),
        })

    return {"records": output}

# =========================
# update shipment dispatch info 
# =========================
@router.patch("/{shipment_id}/dispatch")
async def update_dispatch(
    shipment_id: str,
    payload: ShipmentUpdate,
    db=Depends(get_db)  # type: ignore
):
    if not ObjectId.is_valid(shipment_id):
        raise HTTPException(status_code=400, detail="Invalid shipment ID")
 
    existing = await db["shipments"].find_one({"_id": ObjectId(shipment_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Shipment not found")
 
    # Build update dict — only fields that were actually sent
    update_data = payload.model_dump(exclude_none=True)
 
    # Always stamp server-side fields
    update_data["updated_by"] = "admin"
    update_data["updated_at"] = datetime.now(timezone.utc)
 
    # If dispatching for the first time, set dispatched_at if not provided
    if "dispatched_at" not in update_data and existing.get("dispatched_at") is None:
        update_data["dispatched_at"] = datetime.now(timezone.utc)
 
    # Set current_location to source on first dispatch if not provided
    if (
        "current_location" not in update_data
        and existing.get("current_location") is None
        and "source" in update_data
    ):
        update_data["current_location"] = update_data["source"]
 
    result = await db["shipments"].update_one(
        {"_id": ObjectId(shipment_id)},
        {"$set": update_data}
    )
 
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="No changes applied")
 
    updated = await db["shipments"].find_one({"_id": ObjectId(shipment_id)})
    return {
        "message": "Shipment dispatch info updated successfully",
        "shipment": serialize_shipment(updated)
    }
 
# =========================
# create shipment with validation[admin]
# =========================
@router.post("/", status_code=201)
async def create_shipment(payload: ShipmentCreate, db=Depends(get_db)): # type: ignore
    data = payload.model_dump(exclude_none=True)
    data["created_at"] = datetime.now(timezone.utc)
    data["updated_at"] = datetime.now(timezone.utc)
    data["updated_by"] = "admin"
    data.setdefault("status", "Pending")
 
    result = await db["shipments"].insert_one(data)
    created = await db["shipments"].find_one({"_id": result.inserted_id})
    return {
        "message": "Shipment created successfully",
        "shipment": serialize_shipment(created)
    }

# =========================
# DELETE
# =========================
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
        raise HTTPException(404, "Not found")

    return {"message": "Deleted"}
# ======================================================
#  ADMIN — PATCH SHIPMENT (status + priority+expected_delivery_date)
# ======================================================
@router.patch("/admin/shipments/{shipment_id}")
def patch_shipment(shipment_id: str, data: dict,
                   current_user=Depends(get_current_user)):
    require_role(current_user, ["admin","super_admin"])
 
    doc = find_shipment(shipment_id) # type: ignore
    if not doc:
        raise HTTPException(404, f"Shipment '{shipment_id}' not found")
 
    update_fields = {}
    if "status" in data:
        update_fields["status"] = data["status"]
    if "shipment_priority" in data:
        update_fields["shipment_priority"] = data["shipment_priority"]
    if "priority" in data:
        update_fields["priority"] = data["priority"]
    if "expected_delivery_date" in data:
        try:
            update_fields["expected_delivery_date"] = datetime.strptime(
                data["expected_delivery_date"], "%Y-%m-%d"
            )
        except ValueError:
            raise HTTPException(400, "Invalid date format for expected_delivery_date. Use YYYY-MM-DD.")
    if not update_fields:
        raise HTTPException(400, "No valid fields to update")
 
    shipments_da.update_one({"_id": doc["_id"]}, {"$set": update_fields}) # type: ignore
 
    return {"success": True, "updated": update_fields}
# ======================================================
#  ADMIN — PUT SHIPMENT (full update / same as PATCH)
# ======================================================
@router.put("/admin/shipments/{shipment_id}")
def put_shipment(shipment_id: str, data: dict,
                 current_user=Depends(get_current_user)):
    return patch_shipment(shipment_id, data, current_user)
 