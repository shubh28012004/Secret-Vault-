"""
Authentication and security system for Secret Vault
"""
import jwt
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Union
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from database import get_db
from models import User, TokenData
from config import settings
from logger import get_logger, log_security_event

logger = get_logger("auth")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token security
SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Security settings
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
TOKEN_BLACKLIST = set()  # In production, use Redis or database

security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """Verify and decode a JWT token"""
    try:
        # Check if token is blacklisted
        if token in TOKEN_BLACKLIST:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify token type
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id: int = payload.get("user_id")
        email: str = payload.get("email")
        
        if user_id is None or email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return TokenData(user_id=user_id, email=email)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    token_data = verify_token(token)
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated"
        )
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified"
        )
    
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current admin user"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

def authenticate_user(db: Session, email: str, password: str, request: Request) -> Optional[User]:
    """Authenticate a user with email and password"""
    user = db.query(User).filter(User.email == email.lower()).first()
    
    if not user:
        log_security_event(logger, "login_failed", email, "User not found", request.client.host)
        return None
    
    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining_time = user.locked_until - datetime.utcnow()
        log_security_event(logger, "login_failed", email, f"Account locked for {remaining_time.seconds//60} minutes", request.client.host)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account is locked. Try again in {remaining_time.seconds//60} minutes."
        )
    
    if not verify_password(password, user.hashed_password):
        # Increment failed login attempts
        user.failed_login_attempts += 1
        
        # Lock account if too many failed attempts
        if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            log_security_event(logger, "account_locked", email, f"Account locked after {MAX_LOGIN_ATTEMPTS} failed attempts", request.client.host)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked due to {MAX_LOGIN_ATTEMPTS} failed login attempts. Try again in {LOCKOUT_DURATION_MINUTES} minutes."
            )
        
        db.commit()
        log_security_event(logger, "login_failed", email, f"Invalid password (attempt {user.failed_login_attempts})", request.client.host)
        return None
    
    # Reset failed login attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    db.commit()
    
    log_security_event(logger, "login_success", email, "Successful authentication", request.client.host)
    return user

def create_verification_token() -> str:
    """Create a secure verification token"""
    return secrets.token_urlsafe(32)

def create_password_reset_token() -> str:
    """Create a secure password reset token"""
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    """Hash a token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()

def verify_stored_token(stored_token: str, provided_token: str) -> bool:
    """Verify a provided token against stored hash"""
    return stored_token == hash_token(provided_token)

def revoke_token(token: str):
    """Add token to blacklist"""
    TOKEN_BLACKLIST.add(token)

def check_password_strength(password: str) -> dict:
    """Check password strength and return detailed feedback"""
    feedback = {
        "score": 0,
        "issues": [],
        "strengths": []
    }
    
    # Length check
    if len(password) >= 8:
        feedback["score"] += 1
        feedback["strengths"].append("Good length")
    else:
        feedback["issues"].append("Password must be at least 8 characters")
    
    # Uppercase check
    if any(c.isupper() for c in password):
        feedback["score"] += 1
        feedback["strengths"].append("Contains uppercase letters")
    else:
        feedback["issues"].append("Password must contain uppercase letters")
    
    # Lowercase check
    if any(c.islower() for c in password):
        feedback["score"] += 1
        feedback["strengths"].append("Contains lowercase letters")
    else:
        feedback["issues"].append("Password must contain lowercase letters")
    
    # Digit check
    if any(c.isdigit() for c in password):
        feedback["score"] += 1
        feedback["strengths"].append("Contains numbers")
    else:
        feedback["issues"].append("Password must contain numbers")
    
    # Special character check
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if any(c in special_chars for c in password):
        feedback["score"] += 1
        feedback["strengths"].append("Contains special characters")
    else:
        feedback["issues"].append("Consider adding special characters")
    
    # Entropy check (basic)
    unique_chars = len(set(password))
    if unique_chars >= len(password) * 0.7:
        feedback["score"] += 1
        feedback["strengths"].append("Good character variety")
    else:
        feedback["issues"].append("Consider using more varied characters")
    
    # Common password check (basic)
    common_passwords = ["password", "123456", "qwerty", "admin", "letmein"]
    if password.lower() not in common_passwords:
        feedback["score"] += 1
        feedback["strengths"].append("Not a common password")
    else:
        feedback["issues"].append("Avoid common passwords")
    
    return feedback

def validate_email_domain(email: str) -> bool:
    """Basic email domain validation"""
    # Add your domain validation logic here
    # For now, just check if it's a valid email format
    return "@" in email and "." in email.split("@")[1]

def rate_limit_check(request: Request, key: str, limit: int, window: int) -> bool:
    """Basic rate limiting check"""
    # In production, use Redis or a proper rate limiting library
    # This is a simplified version
    client_ip = request.client.host
    current_time = datetime.utcnow()
    
    # This would normally be stored in Redis or similar
    # For now, we'll just return True (no rate limiting)
    return True
