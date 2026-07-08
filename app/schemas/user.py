from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.user import UserRole

class UserBase(BaseModel):
    mobile_number: str = Field(..., min_length=10, max_length=15)
    email: EmailStr  # Required — used for OTP delivery

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    role: UserRole

class UserLogin(BaseModel):
    mobile_number: str
    password: str

class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class OTPResponse(BaseModel):
    message: str
    mobile_number: str
    # otp is intentionally excluded — delivered via email

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
