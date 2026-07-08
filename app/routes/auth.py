from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse, OTPResponse, TokenResponse
from app.services.auth_service import AuthService
from app.utils.email import send_otp_email


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=OTPResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user - sends OTP to registered email"""
    new_user = AuthService.register_user(
        db=db,
        mobile_number=user.mobile_number,
        email=user.email,
        password=user.password,
        role=user.role
    )

    send_otp_email(
        to_email=new_user.email,
        otp=new_user.otp,
        purpose="registration"
    )

    return OTPResponse(
        message="Registration successful. OTP sent to your email.",
        mobile_number=new_user.mobile_number
    )


@router.post("/login", response_model=OTPResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user - sends OTP to registered email"""
    user, otp = AuthService.login_user(
        db=db,
        mobile_number=credentials.mobile_number,
        password=credentials.password
    )

    send_otp_email(
        to_email=user.email,
        otp=otp,
        purpose="login"
    )

    return OTPResponse(
        message="Login successful. OTP sent to your email.",
        mobile_number=user.mobile_number
    )


@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(otp_data: dict = Body(...), db: Session = Depends(get_db)):
    """Verify OTP and get access token - accepts JSON body"""
    mobile_number = otp_data.get("mobile_number")
    otp = otp_data.get("otp")

    if not mobile_number or not otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="mobile_number and otp are required"
        )

    access_token, user = AuthService.verify_otp_and_generate_token(
        db=db,
        mobile_number=mobile_number,
        otp=otp
    )

    user_response = UserResponse.from_orm(user)

    return TokenResponse(
        access_token=access_token,
        user=user_response
    )


@router.post("/resend-otp", response_model=OTPResponse)
def resend_otp(resend_data: dict = Body(...), db: Session = Depends(get_db)):
    """Resend OTP to registered email"""
    mobile_number = resend_data.get("mobile_number")

    if not mobile_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="mobile_number is required"
        )

    from app.models.user import User
    from app.utils.security import generate_otp
    from datetime import datetime, timedelta

    user = db.query(User).filter(User.mobile_number == mobile_number).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Generate new OTP
    new_otp = generate_otp()
    user.otp = new_otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    db.commit()

    send_otp_email(
        to_email=user.email,
        otp=new_otp,
        purpose="verification"
    )

    return OTPResponse(
        message="OTP resent to your email.",
        mobile_number=user.mobile_number
    )
