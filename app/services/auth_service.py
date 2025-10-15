from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from app.models.user import User
from app.utils.security import verify_password, get_password_hash, create_access_token, generate_otp

class AuthService:
    
    @staticmethod
    def register_user(db: Session, mobile_number: str, email: str, password: str, role: str) -> User:
        """Register a new user"""
        # Check if user exists
        existing_user = db.query(User).filter(User.mobile_number == mobile_number).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mobile number already registered"
            )
        
        if email:
            existing_email = db.query(User).filter(User.email == email).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Generate OTP
        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        
        # Create user
        new_user = User(
            mobile_number=mobile_number,
            email=email,
            password_hash=get_password_hash(password),
            role=role,
            otp=otp,
            otp_expiry=otp_expiry
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user
    
    @staticmethod
    def login_user(db: Session, mobile_number: str, password: str):
        """Login user and generate token"""
        user = db.query(User).filter(User.mobile_number == mobile_number).first()
        
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Generate OTP for login
        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        user.otp = otp
        user.otp_expiry = otp_expiry
        db.commit()
        
        return user, otp
    
    @staticmethod
    def verify_otp_and_generate_token(db: Session, mobile_number: str, otp: str):
        """Verify OTP and generate access token"""
        user = db.query(User).filter(User.mobile_number == mobile_number).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.otp != otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP"
            )
        
        if user.otp_expiry < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP expired"
            )
        
        # Mark as verified
        user.is_verified = True
        user.otp = None
        user.otp_expiry = None
        db.commit()
        
        # Generate token
        access_token = create_access_token(data={"sub": user.id, "role": user.role})
        
        return access_token, user
