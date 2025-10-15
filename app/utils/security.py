from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from app.config import settings
import random
import string
import uuid

# Use bcrypt with explicit configuration
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

def verify_password(plain_password, hashed_password):
    # Truncate password if longer than 72 bytes
    if len(plain_password) > 72:
        plain_password = plain_password[:72]
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    # Truncate password if longer than 72 bytes
    if len(password) > 72:
        password = password[:72]
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

def verify_token(token: str):
    """Alias for decode_access_token for backward compatibility"""
    return decode_access_token(token)

def generate_otp(length: int = 6) -> str:
    """Generate a random OTP"""
    return ''.join(random.choices(string.digits, k=length))

def generate_unique_id(prefix: str = "", length: int = 8) -> str:
    """
    Generate a unique ID with optional prefix
    Example: DOC12345678, PAT12345678, LAB12345678
    """
    unique_part = ''.join(random.choices(string.digits, k=length))
    return f"{prefix}{unique_part}" if prefix else unique_part

def generate_uuid() -> str:
    """Generate a UUID string"""
    return str(uuid.uuid4())
