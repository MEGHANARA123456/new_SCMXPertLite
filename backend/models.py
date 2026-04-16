from enum import Enum

from pydantic import BaseModel, Field, validator
import re
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date, datetime

from zmq import Enum
# ==========================
# TOKEN RESPONSE MODEL
# ==========================

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ============================================================
# Pydantic models for signup OTP flow
# ============================================================
class SignupOtpRequest(BaseModel):
    firstname: str
    lastname: str
    username: str
    email: str
    password: str

class SignupVerifyOtpRequest(BaseModel):
    email: str
    otp: str

class Signup(BaseModel):
  username: str
  email: EmailStr
  password: str
  confirm_password: str
  
class login(BaseModel):
  email: EmailStr
  password: str

class ForgotPass(BaseModel):
    email: str

class VerifyOTP(BaseModel):
    email: str
    otp: str

class ResetPassword(BaseModel):
    email: str
    new_password: str  

# =========================
# MODEL
# =========================
class ShipmentCreate(BaseModel):
    shipment_number: str = Field(..., pattern="^[0-9]{6}$")
    route_from: str = Field(..., min_length=2, max_length=50)
    route_to: str = Field(..., min_length=2, max_length=50)
    device: str = Field(..., min_length=1, max_length=80)
    device_id: str = Field(..., pattern="^115[0-8]$")
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

    # -------- VALIDATION --------
    @validator("route_from", "route_to")
    def validate_route(cls, v):
        if not re.match(r'^[A-Za-z\s,]+$', v):
            raise ValueError("Route must contain only letters, spaces, commas")
        return v

    @validator("expected_delivery_date")
    def validate_date(cls, v):
        if v < date.today():
            raise ValueError("Date cannot be in past")
        return v

    @validator("ndc_number")
    def ndc_format(cls, v):
        if not re.match(r"^[0-9\-]+$", v):
            raise ValueError("Invalid NDC format")
        return v

    @validator("po_number", "container_number", "delivery_number")
    def alphanumeric(cls, v):
        if not re.match(r"^[A-Za-z0-9\-]+$", v):
            raise ValueError("Must be alphanumeric")
        return v
class ModeOfTransport(str, Enum):
    road = "Road"
    air = "Air"
    sea = "Sea"
class ShipmentUpdate(BaseModel):
    shipment_priority: Optional[str] = Field(None, pattern="^(high|medium|low)$")
    shipment_health: Optional[str] = Field(None, pattern="^(high|medium|low)$")
    expected_delivery_date: Optional[date]
 

    # Status & Timing
    status: Optional[str] = "In Transit"
    dispatched_at: Optional[datetime] = None
    estimated_delivery_date: Optional[str] = None   # e.g. "2025-04-15"
    estimated_arrival_time: Optional[str] = None    # e.g. "14:30"
 
    # Tracking
    tracking_id: Optional[str] = None
    tracking_url: Optional[str] = None
    gps_device_id: Optional[str] = None
 
    # Route
    source: Optional[str] = None
    destination: Optional[str] = None
    current_location: Optional[str] = None
 
    # Vehicle & Driver
    vehicle_id: Optional[str] = None
    driver_name: Optional[str] = None
    driver_contact: Optional[str] = None
 
    # Carrier
    carrier: Optional[str] = None
    mode_of_transport: Optional[ModeOfTransport] = None
 
    # Meta (set server-side)
    updated_by: Optional[str] = "admin"
    updated_at: Optional[datetime] = None  
     
class DeviceData(BaseModel):
  device_id: str
  battery_level: int
  first_sensor_temperature: str
  route_from: str
  route_to: str
  timestamp: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())