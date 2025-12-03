from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
# ==========================
# TOKEN RESPONSE MODEL
# ==========================

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


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

class Shipment(BaseModel):
  shipment_number: str
  container_number: str
  route_details: str
  goods_type: str
  expected_delivery_date: str
  po_number: str
  ndc_number: str
  serial_number_goods: str
  delivery_number: int
  batch_id: str
  shipment_description: str
  device: str
 # NEW FIELDS
  shipment_priority: str = Field(..., pattern="^(high|medium|low)$")
  health_score: str = Field(..., pattern="^(low|medium|high)$")

class DeviceData(BaseModel):
  device_id: str
  battery_level: int
  first_sensor_temperature: str
  route_from: str
  route_to: str
  timestamp: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())