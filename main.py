from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from datetime import datetime, timedelta
import secrets
from typing import List, Optional, Dict, Any
import os
import time
import json
from sqlalchemy.orm import Session
from config import settings, validate_configuration
from logger import get_logger, log_startup, log_shutdown, log_api_request, log_security_event
from backup import DatabaseBackup
from notifications import send_system_alert_notification

from database import engine, get_db
from models import (
    Base, User, CredentialCreate, CredentialResponse, CredentialUpdate, 
    UserCreate, UserLogin, UserResponse, Token, PasswordReset, 
    PasswordResetConfirm, EmailVerification
)
from crud import (
    create_user, get_user_by_email, get_user_by_id, update_user,
    verify_user_email, set_password_reset_token, reset_password_with_token,
    create_credential, get_credentials, get_credentials_with_decrypted_passwords, get_credential_by_id,
    update_credential, delete_credential, create_audit_log, get_audit_logs,
    search_credentials, search_credentials_with_decrypted_passwords, 
    get_credentials_by_category, get_credentials_by_category_with_decrypted_passwords, 
    get_expiring_credentials,
    get_user_activity_summary, get_all_users, get_user_stats,
    deactivate_user, activate_user, promote_to_admin
)
from auth import (
    authenticate_user, get_current_user, get_current_active_user, 
    get_current_admin_user, create_access_token, create_refresh_token,
    verify_token, revoke_token, create_verification_token, hash_token,
    check_password_strength, validate_email_domain
)
from security import (
    InputValidator, RateLimiter, SecurityLogger, SecurityMiddleware,
    security_decorator, SecurityError
)
from encryption import decrypt_value, get_encryption_key_info
from config import settings
try:
    from vault_client import vault_status
except Exception:
    vault_status = None
from vault_api import (
    initialize_default_mounts, initialize_default_policies,
    get_kv_secret, put_kv_secret, delete_kv_secret, destroy_kv_secret,
    list_kv_secrets, get_kv_metadata,
    create_vault_token, get_vault_token, revoke_vault_token, renew_vault_token,
    list_mounts, get_mount, create_mount, delete_mount,
    list_policies, get_policy, create_or_update_policy, delete_policy,
    check_policy_access
)
from models import VaultToken

# Initialize logger
logger = get_logger("main")

# Create database tables
Base.metadata.create_all(bind=engine)

# Validate configuration on startup
config_issues = validate_configuration()
if config_issues:
    for issue in config_issues:
        logger.warning(issue)

app = FastAPI(
    title="Secret Vault API",
    description="Secure multi-user credential management system",
    version="2.0.0",
    docs_url="/docs" if settings.show_debug_info else None,
    redoc_url="/redoc" if settings.show_debug_info else None
)

# Add CORS middleware with configurable origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")
    # Mount full frontend app at /app (serves index.html by default)
    app.mount("/app", StaticFiles(directory="frontend", html=True), name="app")

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Process request
    response = await call_next(request)
    
    # Calculate response time
    response_time = time.time() - start_time
    
    # Get user from request if available
    user = "anonymous"
    try:
        if "authorization" in request.headers:
            auth_header = request.headers["authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                token_data = verify_token(token)
                if token_data:
                    user = token_data.email
    except:
        pass
    
    # Log the request
    log_api_request(
        logger, 
        request.method, 
        request.url.path, 
        user, 
        response.status_code, 
        response_time, 
        client_ip
    )
    
    return response

# Web Interface Routes
@app.get("/")
async def root():
    """Redirect to main web app"""
    return RedirectResponse(url="/app/", status_code=302)

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve the login page"""
    if os.path.exists("frontend/login.html"):
        return FileResponse("frontend/login.html")
    else:
        return """
        <html>
            <head>
                <title>Secret Vault - Login</title>
            </head>
            <body>
                <h1>Login</h1>
                <p>Login page not found. Please check if frontend files are available.</p>
            </body>
        </html>
        """

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """Serve the dashboard page"""
    if os.path.exists("frontend/index.html"):
        return FileResponse("frontend/index.html")
    else:
        return """
        <html>
            <head>
                <title>Secret Vault - Dashboard</title>
            </head>
            <body>
                <h1>Dashboard</h1>
                <p>Dashboard page not found. Please check if frontend files are available.</p>
            </body>
        </html>
        """

@app.get("/logout", response_class=HTMLResponse)
async def logout_page():
    """Serve the logout page"""
    if os.path.exists("frontend/logout.html"):
        return FileResponse("frontend/logout.html")
    else:
        return """
        <html>
            <head>
                <title>Logging Out...</title>
            </head>
            <body>
                <h1>Logging Out...</h1>
                <script>
                    localStorage.clear();
                    sessionStorage.clear();
                    window.location.href = '/login';
                </script>
            </body>
        </html>
        """

@app.get("/signup", response_class=HTMLResponse)
async def signup_page():
    """Serve the signup page"""
    if os.path.exists("frontend/signup.html"):
        return FileResponse("frontend/signup.html")
    else:
        return """
        <html>
            <head>
                <title>Secret Vault - Sign Up</title>
            </head>
            <body>
                <h1>Sign Up</h1>
                <p>Signup page not found. Please check if frontend files are available.</p>
            </body>
        </html>
        """

# Health Check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Authentication Routes
@app.post("/auth/signup", response_model=Dict[str, Any])
async def signup(user_data: UserCreate, request: Request, db = Depends(get_db)):
    """Create a new user account"""
    try:
        logger.info(f"Signup attempt for email: {user_data.email}")
        
        # Validate email domain
        if not validate_email_domain(user_data.email):
            logger.warning(f"Invalid email domain for: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email domain"
            )
        
        # Check password strength
        strength = check_password_strength(user_data.password)
        if strength["score"] < 3:
            logger.warning(f"Weak password for email: {user_data.email}, score: {strength['score']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is too weak. Please choose a stronger password."
            )
        
        logger.info(f"Password strength check passed for: {user_data.email}")
        
        # Create user
        logger.info(f"Creating user: {user_data.email}")
        user = create_user(db, user_data)
        logger.info(f"User created successfully: {user.email}")
        
        # Generate verification token
        verification_token = create_verification_token()
        user.email_verification_token = hash_token(verification_token)
        db.commit()
        logger.info(f"Verification token generated for: {user.email}")
        
        # Send verification email (if email is configured)
        if settings.email_notifications and settings.validate_email_settings():
            try:
                from notifications import EmailNotifier
                notifier = EmailNotifier()
                verification_url = f"http://localhost:8000/auth/verify-email?token={verification_token}"
                
                notifier.send_email(
                "Verify Your Email",
                f"Please verify your email by clicking this link: {verification_url}",
                f"""
                <h2>Welcome to Secret Vault!</h2>
                <p>Please verify your email address by clicking the button below:</p>
                <a href="{verification_url}" style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">
                    Verify Email
                </a>
                <p>If the button doesn't work, copy and paste this link: {verification_url}</p>
                <p>This link will expire in 24 hours.</p>
                """,
                to_email=user.email  # <-- ADD THIS PARAMETER
            )
            except Exception as e:
                logger.error(f"Failed to send verification email: {e}")
        
        # Log the signup
        try:
            create_audit_log(
                db, user.id, "SIGNUP", 
                f"New user registered: {user.email}", 
                request.client.host if request.client else "unknown", 
                request.headers.get("user-agent", "unknown")
            )
            logger.info(f"Audit log created for signup: {user.email}")
        except Exception as audit_error:
            logger.error(f"Failed to create audit log: {audit_error}")
            # Don't fail the signup if audit logging fails
        
        logger.info(f"Signup successful for: {user.email}")
        
        return {
            "message": "Account created successfully! Please check your email to verify your account.",
            "user_id": user.id
        }
        
    except ValueError as e:
        logger.warning(f"Validation error during signup: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.post("/auth/resend-verification")
async def resend_verification(data: Dict[str, Any]):
    """Resend email verification link to a user who is not yet verified"""
    try:
        email = (data.get("email") or "").strip().lower()
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        db = next(get_db())
        user = get_user_by_email(db, email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.is_verified:
            return {"message": "Email is already verified"}

        # Generate a new verification token and store its hash
        verification_token = create_verification_token()
        user.email_verification_token = hash_token(verification_token)
        db.commit()

        # Attempt to send email if configured
        sent = False
        if settings.email_notifications and settings.validate_email_settings():
            try:
                from notifications import EmailNotifier
                notifier = EmailNotifier()
                verification_url = f"http://localhost:8000/auth/verify-email?token={verification_token}"
                notifier.send_email(
                    "Verify Your Email",
                    f"Please verify your email by clicking this link: {verification_url}",
                    f"""
                    <h2>Verify your Secret Vault account</h2>
                    <p>Click the button below to verify your email address:</p>
                    <a href="{verification_url}" style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">Verify Email</a>
                    <p>If the button doesn't work, copy and paste this link: {verification_url}</p>
                    <p>This link will expire in 24 hours.</p>
                    """,
                    to_email=user.email  # <-- ADD THIS PARAMETER
                )

                sent = True
            except Exception as e:
                logger.error(f"Failed to send verification email: {e}")
        return {"message": "Verification link generated" + (" and sent" if sent else "")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resend verification: {e}")
        raise HTTPException(status_code=500, detail="Failed to resend verification")
    except Exception as e:
        logger.error(f"Signup error: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account"
        )

@app.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin, request: Request, db = Depends(get_db)):
    """User login with JWT token and enhanced security"""
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    
    try:
        logger.info(f"Login attempt for email: {user_credentials.email} from IP: {ip_address}")
        
        # Security validation
        security_check = SecurityMiddleware.validate_request_security(request)
        if not security_check["valid"]:
            if security_check["blocked"]:
                SecurityLogger.log_suspicious_activity(
                    "BLOCKED_REQUEST",
                    ip_address,
                    user_agent,
                    f"Blocked request: {security_check['reason']}"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=security_check["reason"]
                )
        
        # Enhanced input validation
        if not InputValidator.validate_email(user_credentials.email):
            SecurityLogger.log_failed_login(
                user_credentials.email, ip_address, user_agent, "Invalid email format"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        # Sanitize input
        email = InputValidator.sanitize_input(user_credentials.email, 255)
        
        # Check for brute force attempts
        if RateLimiter.check_brute_force(ip_address, email):
            SecurityLogger.log_suspicious_activity(
                "BRUTE_FORCE_ATTEMPT",
                ip_address,
                user_agent,
                f"Multiple failed attempts for {email}",
                email=email
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Please try again later."
            )
        
        user = authenticate_user(db, email, user_credentials.password, request)
        if not user:
            # Record failed attempt
            RateLimiter.record_failed_attempt(ip_address, email)
            SecurityLogger.log_failed_login(
                email, ip_address, user_agent, "Invalid credentials"
            )
            logger.warning(f"Authentication failed for email: {email} from IP: {ip_address}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        logger.info(f"User authenticated successfully: {user.email}")
        
        if not user.is_verified:
            SecurityLogger.log_failed_login(
                user.email, ip_address, user_agent, "Unverified email"
            )
            logger.warning(f"Unverified user attempt to login: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please verify your email before logging in"
            )
        
        logger.info(f"Creating tokens for user: {user.email}")
        
        # Create access token
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"user_id": user.id, "email": user.email},
            expires_delta=access_token_expires
        )
        
        # Create refresh token
        refresh_token = create_refresh_token(
            data={"user_id": user.id, "email": user.email}
        )
        
        logger.info(f"Tokens created successfully for user: {user.email}")
        
        # Enhanced security logging
        SecurityLogger.log_successful_login(user.id, user.email, ip_address, user_agent)
        
        # Log the login
        try:
            create_audit_log(
                db, user.id, "LOGIN", 
                "User logged in successfully", 
                ip_address, 
                user_agent
            )
            logger.info(f"Audit log created for user: {user.email}")
        except Exception as audit_error:
            logger.error(f"Failed to create audit log: {audit_error}")
            # Don't fail the login if audit logging fails
        
        logger.info(f"Login successful for user: {user.email}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "is_admin": user.is_admin,
                "last_login": user.last_login,
                "created_at": user.created_at
            }
        }
        
    except HTTPException:
        raise
    except SecurityError as e:
        logger.error(f"Security error during login: {e}")
        SecurityLogger.log_suspicious_activity(
            "LOGIN_SECURITY_ERROR",
            ip_address,
            user_agent,
            f"Security error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Login error: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {str(e)}")
        SecurityLogger.log_suspicious_activity(
            "LOGIN_ERROR",
            ip_address,
            user_agent,
            f"Unexpected error during login: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

# Replace your existing verify_email endpoint with this:

@app.get("/auth/verify-email")
async def verify_email(token: str, db = Depends(get_db)):
    """Verify user email with token (GET request from email link)"""
    try:
        success = verify_user_email(db, token)
        if success:
            # Return an HTML page for better user experience
            return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>Email Verified - Secret Vault</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 500px;
        }
        .success-icon {
            font-size: 64px;
            color: #28a745;
            margin-bottom: 20px;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        p {
            color: #666;
            margin-bottom: 30px;
            line-height: 1.6;
        }
        .btn {
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">✅</div>
        <h1>Email Verified Successfully!</h1>
        <p>Your email has been verified. You can now log in to your Secret Vault account.</p>
        <a href="/login" class="btn">Go to Login</a>
    </div>
</body>
</html>
            """)
        else:
            return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>Verification Failed - Secret Vault</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 500px;
        }
        .error-icon {
            font-size: 64px;
            color: #dc3545;
            margin-bottom: 20px;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        p {
            color: #666;
            margin-bottom: 30px;
            line-height: 1.6;
        }
        .btn {
            display: inline-block;
            padding: 12px 30px;
            background: #6c757d;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            margin: 5px;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="error-icon">❌</div>
        <h1>Verification Failed</h1>
        <p>The verification link is invalid or has expired. Please request a new verification email.</p>
        <a href="/signup" class="btn btn-primary">Back to Sign Up</a>
        <a href="/login" class="btn">Go to Login</a>
    </div>
</body>
</html>
            """, status_code=400)
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>Error - Secret Vault</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 500px;
        }
        .error-icon {
            font-size: 64px;
            color: #ffc107;
            margin-bottom: 20px;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        p {
            color: #666;
            margin-bottom: 30px;
        }
        .btn {
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="error-icon">⚠️</div>
        <h1>Something Went Wrong</h1>
        <p>An error occurred while verifying your email. Please try again or contact support.</p>
        <a href="/signup" class="btn">Back to Sign Up</a>
    </div>
</body>
</html>
        """, status_code=500)
@app.post("/auth/forgot-password")
async def forgot_password(reset_request: PasswordReset, db = Depends(get_db)):
    """Request password reset"""
    try:
        token = set_password_reset_token(db, reset_request.email)
        if token:
            # Send password reset email
            if settings.email_notifications and settings.validate_email_settings():
                try:
                    from notifications import EmailNotifier
                    notifier = EmailNotifier()
                    reset_url = f"http://localhost:8000/reset-password?token={token}"
                    
                    notifier.send_email(
                        "Password Reset Request",
                        f"Click this link to reset your password: {reset_url}",
                        f"""
                        <h2>Password Reset Request</h2>
                        <p>You requested a password reset. Click the button below to reset your password:</p>
                        <a href="{reset_url}" style="background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">
                            Reset Password
                        </a>
                        <p>If you didn't request this, please ignore this email.</p>
                        <p>This link will expire in 1 hour.</p>
                        """,
                        to_email=reset_request.email  # <-- ADD THIS PARAMETER
                    )
                except Exception as e:
                    logger.error(f"Failed to send password reset email: {e}")
            
            return {"message": "Password reset email sent if the email exists in our system"}
        else:
            # Don't reveal if email exists or not
            return {"message": "Password reset email sent if the email exists in our system"}
            
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset request"
        )

@app.post("/auth/reset-password")
async def reset_password(reset_data: PasswordResetConfirm, db = Depends(get_db)):
    """Reset password with token"""
    try:
        success = reset_password_with_token(db, reset_data.token, reset_data.new_password)
        if success:
            return {"message": "Password reset successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )

@app.post("/auth/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Logout user and revoke token"""
    try:
        # Get token from request
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            revoke_token(token)
        
        # Log the logout
        create_audit_log(
            db, current_user.id, "LOGOUT", 
            "User logged out", 
            request.client.host, 
            request.headers.get("user-agent")
        )
        
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

# Google OAuth Routes
@app.post("/auth/google")
async def google_oauth_register(
    request: Request,
    db = Depends(get_db)
):
    """Register or login with Google OAuth"""
    try:
        data = await request.json()
        google_token = data.get("google_token")
        email = data.get("email")
        name = data.get("name")
        google_id = data.get("google_id")
        profile_picture = data.get("profile_picture")
        
        if not all([google_token, email, name, google_id]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required Google OAuth data"
            )
        
        # Check if user already exists
        existing_user = get_user_by_email(db, email)
        
        if existing_user:
            # User exists, log them in
            if not existing_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is deactivated"
                )
            
            # Update last login
            existing_user.last_login = datetime.utcnow()
            db.commit()
            
            # Create tokens
            access_token = create_access_token(
                data={"user_id": existing_user.id, "email": existing_user.email}
            )
            refresh_token = create_refresh_token(
                data={"user_id": existing_user.id, "email": existing_user.email}
            )
            
            # Log the login
            create_audit_log(
                db, existing_user.id, "LOGIN", 
                "Google OAuth login", 
                request.client.host, 
                request.headers.get("user-agent")
            )
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": existing_user.id,
                    "email": existing_user.email,
                    "username": existing_user.username,
                    "full_name": existing_user.full_name,
                    "is_admin": existing_user.is_admin,
                    "is_active": existing_user.is_active,
                    "is_verified": existing_user.is_verified,
                    "created_at": existing_user.created_at,
                    "last_login": existing_user.last_login
                }
            }
        else:
            # Create new user with Google OAuth
            # Generate a temporary password (will be changed on first login)
            temp_password = secrets.token_urlsafe(32)
            
            user_data = UserCreate(
                email=email,
                username=email.split("@")[0],  # Use email prefix as username
                full_name=name,
                password=temp_password
            )
            
            new_user = create_user(db, user_data)
            
            # Mark as verified since Google verified the email
            new_user.is_verified = True
            new_user.is_active = True  # Auto-activate Google OAuth users
            new_user.last_login = datetime.utcnow()
            db.commit()
            
            # Create tokens
            access_token = create_access_token(
                data={"user_id": new_user.id, "email": new_user.email}
            )
            refresh_token = create_refresh_token(
                data={"user_id": new_user.id, "email": new_user.email}
            )
            
            # Log the registration
            create_audit_log(
                db, new_user.id, "REGISTER", 
                "Google OAuth registration", 
                request.client.host, 
                request.headers.get("user-agent")
            )
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": new_user.id,
                    "email": new_user.email,
                    "username": new_user.username,
                    "full_name": new_user.full_name,
                    "is_admin": new_user.is_admin,
                    "is_active": new_user.is_active,
                    "is_verified": new_user.is_verified,
                    "created_at": new_user.created_at,
                    "last_login": new_user.last_login
                },
                "message": "Account created successfully via Google OAuth"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth authentication failed"
        )

# Credential Routes (User-specific)
@app.get("/credentials", response_model=List[CredentialResponse])
async def list_credentials(
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """List all credentials for the current user"""
    credentials_data = get_credentials_with_decrypted_passwords(db, current_user.id)
    create_audit_log(db, current_user.id, "VIEW", "Listed all credentials")
    return credentials_data

@app.post("/credentials", response_model=CredentialResponse)
async def add_credential(
    credential: CredentialCreate,
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """Add a new credential for the current user"""
    try:
        db_credential = create_credential(db, credential.dict(), current_user.id)
        create_audit_log(db, current_user.id, "CREATE", f"Created credential: {db_credential.title}")
        
        # Convert to response format with decrypted password
        from encryption import decrypt_value
        try:
            decrypted_password = decrypt_value(db_credential.encrypted_password)
        except Exception as e:
            logger.error(f"Failed to decrypt password for new credential: {e}")
            decrypted_password = "*** DECRYPTION ERROR ***"
        
        response_data = {
            "id": db_credential.id,
            "user_id": db_credential.user_id,
            "title": db_credential.title,
            "username": db_credential.username,
            "password": decrypted_password,
            "category": db_credential.category,
            "url": db_credential.url,
            "notes": db_credential.notes,
            "is_active": db_credential.is_active,
            "expires_at": db_credential.expires_at,
            "created_at": db_credential.created_at,
            "updated_at": db_credential.updated_at
        }
        
        return response_data
    except Exception as e:
        logger.error(f"Credential creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create credential"
        )

@app.get("/credentials/{credential_id}", response_model=CredentialResponse)
async def get_credential(
    credential_id: int,
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """Get a specific credential by ID for the current user"""
    credential = get_credential_by_id(db, credential_id, current_user.id)
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    # Convert to response format with decrypted password
    from encryption import decrypt_value
    try:
        decrypted_password = decrypt_value(credential.encrypted_password)
    except Exception as e:
        logger.error(f"Failed to decrypt password for credential {credential_id}: {e}")
        decrypted_password = "*** DECRYPTION ERROR ***"
    
    response_data = {
        "id": credential.id,
        "user_id": credential.user_id,
        "title": credential.title,
        "username": credential.username,
        "password": decrypted_password,
        "category": credential.category,
        "url": credential.url,
        "notes": credential.notes,
        "is_active": credential.is_active,
        "expires_at": credential.expires_at,
        "created_at": credential.created_at,
        "updated_at": credential.updated_at
    }
    
    create_audit_log(db, current_user.id, "VIEW", f"Viewed credential: {credential.title}")
    return response_data

@app.get("/credentials/{credential_id}/password")
async def get_credential_password(
    credential_id: int,
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """Get decrypted password for a specific credential"""
    credential = get_credential_by_id(db, credential_id, current_user.id)
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    try:
        decrypted_password = decrypt_value(credential.encrypted_password)
        create_audit_log(db, current_user.id, "VIEW_PASSWORD", f"Viewed password for: {credential.title}")
        return {"password": decrypted_password}
    except Exception as e:
        logger.error(f"Password decryption error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt password"
        )

@app.put("/credentials/{credential_id}", response_model=CredentialResponse)
async def update_user_credential(
    credential_id: int,
    credential_update: CredentialUpdate,
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """Update a credential for the current user"""
    db_credential = get_credential_by_id(db, credential_id, current_user.id)
    if not db_credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    updated_credential = update_credential(db, credential_id, current_user.id, credential_update.dict(exclude_unset=True))
    
    # Convert to response format with decrypted password
    from encryption import decrypt_value
    try:
        decrypted_password = decrypt_value(updated_credential.encrypted_password)
    except Exception as e:
        logger.error(f"Failed to decrypt password for updated credential {credential_id}: {e}")
        decrypted_password = "*** DECRYPTION ERROR ***"
    
    response_data = {
        "id": updated_credential.id,
        "user_id": updated_credential.user_id,
        "title": updated_credential.title,
        "username": updated_credential.username,
        "password": decrypted_password,
        "category": updated_credential.category,
        "url": updated_credential.url,
        "notes": updated_credential.notes,
        "is_active": updated_credential.is_active,
        "expires_at": updated_credential.expires_at,
        "created_at": updated_credential.created_at,
        "updated_at": updated_credential.updated_at
    }
    
    create_audit_log(db, current_user.id, "UPDATE", f"Updated credential: {updated_credential.title}")
    return response_data

@app.delete("/credentials/{credential_id}")
async def delete_user_credential(
    credential_id: int,
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """Delete a credential for the current user"""
    db_credential = get_credential_by_id(db, credential_id, current_user.id)
    if not db_credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    delete_credential(db, credential_id, current_user.id)
    create_audit_log(db, current_user.id, "DELETE", f"Deleted credential: {db_credential.title}")
    return {"message": "Credential deleted successfully"}

@app.get("/credentials/search/{query}")
async def search_user_credentials(
    query: str,
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """Search credentials for the current user"""
    credentials = search_credentials_with_decrypted_passwords(db, current_user.id, query)
    create_audit_log(db, current_user.id, "SEARCH", f"Searched for: {query}")
    return credentials

@app.get("/credentials/category/{category}")
async def get_user_credentials_by_category(
    category: str,
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """Get credentials by category for the current user"""
    credentials = get_credentials_by_category_with_decrypted_passwords(db, current_user.id, category)
    create_audit_log(db, current_user.id, "VIEW", f"Viewed credentials in category: {category}")
    return credentials

@app.get("/credentials/expiring")
async def get_user_expiring_credentials(
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """Get credentials expiring within specified days for the current user"""
    credentials = get_expiring_credentials(db, current_user.id, days)
    create_audit_log(db, current_user.id, "VIEW", f"Viewed expiring credentials (within {days} days)")
    return credentials

# Audit Log Routes
@app.get("/audit")
async def get_user_audit_logs(
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """Get audit logs for the current user"""
    logs = get_audit_logs(db, current_user.id)
    return logs

@app.get("/audit/activity")
async def get_user_activity(
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """Get user activity summary"""
    activity = get_user_activity_summary(db, current_user.id, days)
    return activity

# Admin Routes
@app.get("/admin/users", response_model=List[UserResponse])
async def admin_get_users(
    current_user: User = Depends(get_current_admin_user),
    db = Depends(get_db)
):
    """Get all users (admin only)"""
    users = get_all_users(db)
    return users

@app.get("/admin/stats")
async def admin_get_stats(
    current_user: User = Depends(get_current_admin_user),
    db = Depends(get_db)
):
    """Get system statistics (admin only)"""
    stats = get_user_stats(db)
    return stats

@app.post("/admin/users/{user_id}/deactivate")
async def admin_deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db = Depends(get_db)
):
    """Deactivate a user (admin only)"""
    success = deactivate_user(db, user_id)
    if success:
        return {"message": "User deactivated successfully"}
    else:
        raise HTTPException(status_code=404, detail="User not found")

@app.post("/admin/users/{user_id}/activate")
async def admin_activate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db = Depends(get_db)
):
    """Activate a user (admin only)"""
    success = activate_user(db, user_id)
    if success:
        return {"message": "User activated successfully"}
    else:
        raise HTTPException(status_code=404, detail="User not found")

@app.post("/admin/users/{user_id}/promote")
async def admin_promote_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db = Depends(get_db)
):
    """Promote user to admin (admin only)"""
    success = promote_to_admin(db, user_id)
    if success:
        return {"message": "User promoted to admin successfully"}
    else:
        raise HTTPException(status_code=404, detail="User not found")

# Backup endpoints (admin only)
@app.post("/backup")
async def create_backup(
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new database backup"""
    try:
        backup_manager = DatabaseBackup()
        backup_path = backup_manager.create_backup()
        
        if backup_path:
            return {"message": "Backup created successfully", "backup_path": backup_path}
        else:
            raise HTTPException(status_code=500, detail="Failed to create backup")
    except Exception as e:
        logger.error(f"Backup creation failed: {e}")
        raise HTTPException(status_code=500, detail="Backup creation failed")

@app.get("/backup/list")
async def list_backups(
    current_user: User = Depends(get_current_admin_user)
):
    """List all available backups"""
    try:
        backup_manager = DatabaseBackup()
        backups = backup_manager.list_backups()
        return {"backups": backups}
    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        raise HTTPException(status_code=500, detail="Failed to list backups")

@app.get("/backup/stats")
async def get_backup_stats(
    current_user: User = Depends(get_current_admin_user)
):
    """Get backup statistics"""
    try:
        backup_manager = DatabaseBackup()
        stats = backup_manager.get_backup_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get backup stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get backup statistics")

@app.post("/backup/cleanup")
async def cleanup_backups(
    current_user: User = Depends(get_current_admin_user)
):
    """Clean up old backups"""
    try:
        backup_manager = DatabaseBackup()
        deleted_count = backup_manager.cleanup_old_backups()
        return {"message": f"Cleanup completed", "deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"Backup cleanup failed: {e}")
        raise HTTPException(status_code=500, detail="Backup cleanup failed")

# System endpoints
@app.get("/system/info")
async def get_system_info(
    current_user: User = Depends(get_current_admin_user)
):
    """Get system information"""
    try:
        import psutil
        import platform
        
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage('/')._asdict(),
            "uptime": time.time() - psutil.boot_time(),
            "environment": settings.environment,
            "debug_mode": settings.debug,
            "encryption_info": get_encryption_key_info(),
            "vault": vault_status() if vault_status else {"enabled": getattr(settings, "vault_enabled", False), "error": "vault client not available"}
        }
        return system_info
    except ImportError:
        return {"message": "System monitoring not available (psutil not installed)"}
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system information")

@app.get("/system/health")
async def system_health_check():
    """Comprehensive system health check"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "backup_system": "available",
            "email_notifications": settings.email_notifications,
            "environment": settings.environment,
            "encryption": "available"
        }
        
        # Check database connection
        try:
            db = next(get_db())
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            health_status["database"] = "connected"
        except Exception as e:
            health_status["database"] = "error"
            health_status["database_error"] = str(e)
            health_status["status"] = "unhealthy"
        
        # Check backup system
        try:
            backup_manager = DatabaseBackup()
            backup_manager.get_backup_stats()
            health_status["backup_system"] = "available"
        except Exception as e:
            health_status["backup_system"] = "error"
            health_status["backup_error"] = str(e)
        
        # Check encryption
        try:
            encryption_info = get_encryption_key_info()
            if encryption_info.get("verification_status"):
                health_status["encryption"] = "available"
            else:
                health_status["encryption"] = "error"
                health_status["encryption_error"] = "Key verification failed"
        except Exception as e:
            health_status["encryption"] = "error"
            health_status["encryption_error"] = str(e)
        
        # Check built-in Vault API (always available)
        try:
            # Test that Vault API endpoints are working
            db = next(get_db())
            from vault_api import list_mounts
            mounts = list_mounts(db)
            health_status["vault"] = {
                "enabled": True,
                "status": "available",
                "type": "built-in",
                "mounts": list(mounts.keys()),
                "note": "Built-in Vault API is available"
            }
        except Exception as e:
            # Even if there's an error, the Vault API is still available
            health_status["vault"] = {
                "enabled": True,
                "status": "available",
                "type": "built-in",
                "note": "Built-in Vault API is available"
            }
        
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

# HashiCorp Vault API - Full Implementation
# Dependency to get Vault token from request
def get_vault_token_from_request(request: Request, db: Session = Depends(get_db)) -> VaultToken:
    """Get and validate Vault token from request"""
    token_id = None
    if "X-Vault-Token" in request.headers:
        token_id = request.headers["X-Vault-Token"]
    else:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token_id = auth_header[7:]
    
    if not token_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )
    
    # Try to get Vault token first
    vault_token = get_vault_token(db, token_id)
    if vault_token:
        return vault_token
    
    # Fallback to JWT token for backward compatibility
    try:
        token_data = verify_token(token_id)
        if token_data:
            user = get_user_by_id(db, token_data.user_id)
            if user:
                # Create a temporary Vault token from JWT
                policies = ["default"]
                if user.is_admin:
                    policies.append("root")
                vault_token = create_vault_token(
                    db, policies=policies, user_id=user.id,
                    metadata={"email": user.email, "username": user.username}
                )
                return vault_token
    except:
        pass
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token"
    )

# Authentication Endpoints
@app.post("/v1/auth/jwt/login")
async def vault_jwt_login(request: Request, db = Depends(get_db)):
    """Vault-compatible JWT login endpoint"""
    try:
        data = await request.json()
        email = data.get("email") or data.get("username")
        password = data.get("password")
        
        if not email or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required"
            )
        
        user = authenticate_user(db, email, password, request)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Create Vault token
        policies = ["default"]
        if user.is_admin:
            policies.append("root")
        
        vault_token = create_vault_token(
            db,
            policies=policies,
            user_id=user.id,
            metadata={"email": user.email, "username": user.username},
            ttl=1800  # 30 minutes
        )
        
        return {
            "auth": {
                "client_token": vault_token.token_id,
                "policies": json.loads(vault_token.policies),
                "metadata": json.loads(vault_token.token_metadata) if vault_token.token_metadata else {},
                "lease_duration": vault_token.ttl or 1800,
                "renewable": vault_token.renewable
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vault JWT login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@app.get("/v1/auth/token/lookup-self")
async def vault_token_lookup_self(
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Look up information about the current token"""
    policies = json.loads(vault_token.policies)
    metadata = json.loads(vault_token.token_metadata) if vault_token.token_metadata else {}
    
    return {
        "data": {
            "id": vault_token.token_id,
            "policies": policies,
            "path": "auth/jwt/login",
            "meta": metadata,
            "display_name": metadata.get("email", "unknown"),
            "num_uses": vault_token.num_uses,
            "ttl": vault_token.ttl or 0,
            "creation_time": int(vault_token.creation_time.timestamp()),
            "creation_ttl": vault_token.ttl or 0,
            "expire_time": vault_token.expire_time.isoformat() + "Z" if vault_token.expire_time else None,
            "entity_id": str(vault_token.user_id) if vault_token.user_id else None,
            "renewable": vault_token.renewable
        }
    }

@app.post("/v1/auth/token/create")
async def vault_token_create(
    request: Request,
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Create a new token"""
    try:
        data = await request.json() if request.method == "POST" else {}
        policies = data.get("policies", json.loads(vault_token.policies))
        ttl_str = data.get("ttl")
        
        # Parse TTL string (e.g., "1h", "30m", "1d") to seconds
        ttl_seconds = None
        if ttl_str:
            if isinstance(ttl_str, int):
                ttl_seconds = ttl_str
            elif isinstance(ttl_str, str):
                # Parse Vault TTL format: "1h", "30m", "1d", etc.
                import re
                match = re.match(r'^(\d+)([smhd])$', ttl_str.lower())
                if match:
                    value = int(match.group(1))
                    unit = match.group(2)
                    multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
                    ttl_seconds = value * multipliers.get(unit, 1)
                else:
                    # Try to parse as integer
                    try:
                        ttl_seconds = int(ttl_str)
                    except ValueError:
                        ttl_seconds = None
        
        metadata = data.get("metadata", {})
        renewable = data.get("renewable", True)
        num_uses = data.get("num_uses")
        
        new_token = create_vault_token(
            db,
            policies=policies,
            ttl=ttl_seconds,
            metadata=metadata,
            user_id=vault_token.user_id,
            parent_token_id=vault_token.token_id,
            renewable=renewable,
            num_uses=num_uses
        )
        
        return {
            "auth": {
                "client_token": new_token.token_id,
                "policies": json.loads(new_token.policies),
                "metadata": json.loads(new_token.token_metadata) if new_token.token_metadata else {},
                "lease_duration": new_token.ttl or 0,
                "renewable": new_token.renewable
            }
        }
    except Exception as e:
        logger.error(f"Token creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token creation failed"
        )

@app.post("/v1/auth/token/renew")
@app.put("/v1/auth/token/renew")
async def vault_token_renew(
    request: Request,
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Renew a token"""
    try:
        data = await request.json() if request.method in ["POST", "PUT"] else {}
        increment = data.get("increment")
        
        renewed_token = renew_vault_token(db, vault_token.token_id, increment)
        if not renewed_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token cannot be renewed"
            )
        
        return {
            "auth": {
                "client_token": renewed_token.token_id,
                "policies": json.loads(renewed_token.policies),
                "lease_duration": renewed_token.ttl or 0,
                "renewable": renewed_token.renewable
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token renewal error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token renewal failed"
        )

@app.post("/v1/auth/token/renew-self")
@app.put("/v1/auth/token/renew-self")
async def vault_token_renew_self(
    request: Request,
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Renew the current token (alias for renew)"""
    try:
        data = await request.json() if request.method in ["POST", "PUT"] else {}
        increment = data.get("increment")
        
        renewed_token = renew_vault_token(db, vault_token.token_id, increment)
        if not renewed_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token cannot be renewed"
            )
        
        return {
            "auth": {
                "client_token": renewed_token.token_id,
                "policies": json.loads(renewed_token.policies),
                "lease_duration": renewed_token.ttl or 0,
                "renewable": renewed_token.renewable
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token renewal error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token renewal failed"
        )

@app.post("/v1/auth/token/revoke")
async def vault_token_revoke(
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Revoke a token"""
    revoke_vault_token(db, vault_token.token_id)
    return {}

# KV v2 Secret Engine Endpoints
@app.get("/v1/{mount_path}/data/{secret_path:path}")
async def vault_kv_get(
    mount_path: str,
    secret_path: str,
    version: Optional[int] = None,
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Get a secret from KV v2"""
    policies = json.loads(vault_token.policies)
    if not check_policy_access(policies, f"{mount_path}/data/{secret_path}", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    secret = get_kv_secret(db, mount_path, secret_path, version)
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Secret not found"
        )
    
    # Return in KV v2 format: {data: {data: {...}, metadata: {...}}}
    return {
        "data": {
            "data": secret.get("data", {}),
            "metadata": secret.get("metadata", {})
        }
    }

@app.post("/v1/{mount_path}/data/{secret_path:path}")
@app.put("/v1/{mount_path}/data/{secret_path:path}")
async def vault_kv_put(
    mount_path: str,
    secret_path: str,
    request: Request,
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Store a secret in KV v2 (supports both POST and PUT)"""
    policies = json.loads(vault_token.policies)
    if not check_policy_access(policies, f"{mount_path}/data/{secret_path}", "create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    data = await request.json()
    secret_data = data.get("data", {})
    metadata = data.get("options", {}).get("metadata", {})
    
    result = put_kv_secret(db, mount_path, secret_path, secret_data, metadata)
    return {"data": result}

# Handle KV v2 paths with /data/ prefix swapped (Vault CLI format: /v1/data/{mount}/{path})
@app.put("/v1/data/{mount_path}/{secret_path:path}")
@app.get("/v1/data/{mount_path}/{secret_path:path}")
async def vault_kv_data_swapped(
    mount_path: str,
    secret_path: str,
    request: Request,
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Handle KV v2 requests with swapped path format (/v1/data/{mount}/{path})"""
    # Check if this is a KV v2 mount
    mount = get_mount(db, mount_path)
    if mount and mount.type == "kv-v2":
        if request.method == "PUT":
            # PUT request - write secret
            policies = json.loads(vault_token.policies)
            if not check_policy_access(policies, f"{mount_path}/data/{secret_path}", "create"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied"
                )
            
            data = await request.json()
            secret_data = data.get("data", {}) if "data" in data else data
            metadata = data.get("options", {}).get("metadata", {}) if "options" in data else {}
            
            result = put_kv_secret(db, mount_path, secret_path, secret_data, metadata)
            return {"data": result}
        else:
            # GET request - read secret
            version = request.query_params.get("version")
            version_int = int(version) if version else None
            
            policies = json.loads(vault_token.policies)
            if not check_policy_access(policies, f"{mount_path}/data/{secret_path}", "read"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied"
                )
            
            secret = get_kv_secret(db, mount_path, secret_path, version_int)
            if not secret:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Secret not found"
                )
            
            # Return in KV v2 format: {data: {data: {...}, metadata: {...}}}
            return {
                "data": {
                    "data": secret.get("data", {}),
                    "metadata": secret.get("metadata", {})
                }
            }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Mount not found or not a KV v2 mount"
    )

# Handle metadata paths with swapped format (/v1/metadata/{mount}/{path})
@app.get("/v1/metadata/{mount_path}/{secret_path:path}")
@app.get("/v1/metadata/{mount_path}")
async def vault_kv_metadata_swapped(
    request: Request,
    mount_path: str,
    secret_path: str = "",
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Handle KV v2 metadata requests with swapped path format (/v1/metadata/{mount}/{path})"""
    # Check if this is a list request
    if request.query_params.get("list") == "true":
        # List request
        list_prefix = request.query_params.get("list", "")
        policies = json.loads(vault_token.policies)
        if not check_policy_access(policies, f"{mount_path}/data/{list_prefix}", "list"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        
        secrets = list_kv_secrets(db, mount_path, list_prefix)
        return {"data": {"keys": secrets}}
    
    # Check if this is a KV v2 mount
    mount = get_mount(db, mount_path)
    if mount and mount.type == "kv-v2":
        if not secret_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Path required"
            )
        
        policies = json.loads(vault_token.policies)
        if not check_policy_access(policies, f"{mount_path}/metadata/{secret_path}", "read"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        
        metadata = get_kv_metadata(db, mount_path, secret_path)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Secret not found"
            )
        
        return {"data": metadata}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Mount not found or not a KV v2 mount"
    )

@app.delete("/v1/{mount_path}/data/{secret_path:path}")
async def vault_kv_delete(
    mount_path: str,
    secret_path: str,
    versions: Optional[str] = None,
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Delete a secret from KV v2"""
    policies = json.loads(vault_token.policies)
    if not check_policy_access(policies, f"{mount_path}/metadata/{secret_path}", "delete"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    version_list = None
    if versions:
        version_list = [int(v) for v in versions.split(',')]
    
    delete_kv_secret(db, mount_path, secret_path, version_list)
    return {}

@app.delete("/v1/{mount_path}/destroy/{secret_path:path}")
async def vault_kv_destroy(
    mount_path: str,
    secret_path: str,
    versions: str,
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Permanently destroy secret versions"""
    policies = json.loads(vault_token.policies)
    if not check_policy_access(policies, f"{mount_path}/metadata/{secret_path}", "delete"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    version_list = [int(v) for v in versions.split(',')]
    destroy_kv_secret(db, mount_path, secret_path, version_list)
    return {}

@app.get("/v1/{mount_path}/metadata/{secret_path:path}")
async def vault_kv_metadata(
    mount_path: str,
    secret_path: str,
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Get metadata for a secret"""
    policies = json.loads(vault_token.policies)
    if not check_policy_access(policies, f"{mount_path}/metadata/{secret_path}", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    metadata = get_kv_metadata(db, mount_path, secret_path)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Secret not found"
        )
    
    return {"data": metadata}

@app.get("/v1/{mount_path}/metadata")
async def vault_kv_list(
    mount_path: str,
    request: Request,
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """List secrets in a path"""
    # Get list parameter from query string
    list_prefix = request.query_params.get("list", "")
    
    policies = json.loads(vault_token.policies)
    if not check_policy_access(policies, f"{mount_path}/data/{list_prefix}", "list"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    secrets = list_kv_secrets(db, mount_path, list_prefix)
    return {"data": {"keys": secrets}}

# Secret Engine Mount Endpoints
@app.get("/v1/sys/mounts")
async def vault_sys_mounts(
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """List all secret engine mounts"""
    policies = json.loads(vault_token.policies)
    if "root" not in policies:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    mounts = list_mounts(db)
    return {"data": mounts}

@app.post("/v1/sys/mounts/{path:path}")
async def vault_sys_mount(
    path: str,
    request: Request,
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Mount a secret engine"""
    policies = json.loads(vault_token.policies)
    if "root" not in policies:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    data = await request.json()
    mount_type = data.get("type", "kv-v2")
    description = data.get("description", "")
    config = data.get("config", {})
    options = data.get("options", {})
    
    create_mount(db, path, mount_type, description, config, options)
    return {}

@app.delete("/v1/sys/mounts/{path:path}")
async def vault_sys_unmount(
    path: str,
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Unmount a secret engine"""
    policies = json.loads(vault_token.policies)
    if "root" not in policies:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    delete_mount(db, path)
    return {}

# Policy Endpoints
@app.get("/v1/sys/policies/acl")
async def vault_sys_policies_list(
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """List all policies"""
    policies = json.loads(vault_token.policies)
    if "root" not in policies:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    policy_names = list_policies(db)
    return {"policies": policy_names}

@app.get("/v1/sys/policies/acl/{name}")
async def vault_sys_policy_get(
    name: str,
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Get a policy"""
    policies = json.loads(vault_token.policies)
    if "root" not in policies:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    policy = get_policy(db, name)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found"
        )
    
    return {"name": policy.name, "policy": policy.policy}

@app.put("/v1/sys/policies/acl/{name}")
async def vault_sys_policy_put(
    name: str,
    request: Request,
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Create or update a policy"""
    policies = json.loads(vault_token.policies)
    if "root" not in policies:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    data = await request.json()
    policy_content = data.get("policy", "")
    description = data.get("description", "")
    
    create_or_update_policy(db, name, policy_content, description)
    return {}

@app.delete("/v1/sys/policies/acl/{name}")
async def vault_sys_policy_delete(
    name: str,
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Delete a policy"""
    policies = json.loads(vault_token.policies)
    if "root" not in policies:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    delete_policy(db, name)
    return {}

# System Endpoints
@app.get("/v1/sys/health")
async def vault_sys_health():
    """Vault health check"""
    try:
        db = next(get_db())
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        
        return {
            "initialized": True,
            "sealed": False,
            "standby": False,
            "performance_standby": False,
            "replication_performance_mode": "disabled",
            "replication_dr_mode": "disabled",
            "server_time_utc": int(datetime.utcnow().timestamp()),
            "version": "1.0.0",
            "cluster_name": "secret-vault",
            "cluster_id": "secret-vault-cluster"
        }
    except Exception as e:
        logger.error(f"Vault health check error: {e}")
        return {
            "initialized": False,
            "sealed": True,
            "standby": False,
            "server_time_utc": int(datetime.utcnow().timestamp())
        }

@app.get("/v1/sys/seal-status")
async def vault_sys_seal_status():
    """Vault seal status endpoint (used by 'vault status' command)"""
    try:
        db = next(get_db())
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        
        return {
            "type": "shamir",
            "initialized": True,
            "sealed": False,
            "t": 1,
            "n": 1,
            "progress": 0,
            "nonce": "",
            "version": "1.0.0",
            "migration": False,
            "recovery_seal": False,
            "storage_type": "file"
        }
    except Exception as e:
        logger.error(f"Vault seal status error: {e}")
        return {
            "type": "shamir",
            "initialized": False,
            "sealed": True,
            "t": 0,
            "n": 0,
            "progress": 0,
            "nonce": "",
            "version": "1.0.0"
        }

@app.get("/v1/sys/leader")
async def vault_sys_leader():
    """Vault leader status endpoint (used by 'vault status' command)"""
    return {
        "ha_enabled": False,
        "is_self": True,
        "leader_address": "",
        "leader_cluster_address": ""
    }

@app.get("/v1/sys/internal/ui/mounts/{path:path}")
async def vault_sys_internal_ui_mounts(
    path: str,
    vault_token: VaultToken = Depends(get_vault_token_from_request),
    db: Session = Depends(get_db)
):
    """Internal UI endpoint for mount information (used by Vault CLI)"""
    # Extract mount path from the full path
    # Path format: secret/production/database -> mount is "secret"
    parts = path.split('/')
    mount_path = parts[0] if parts else path
    
    mount = get_mount(db, mount_path)
    if not mount:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mount not found"
        )
    
    options = json.loads(mount.options) if mount.options else {}
    return {
        "type": mount.type,
        "description": mount.description or "",
        "options": options,
        "config": json.loads(mount.config) if mount.config else {},
        "accessor": f"kv_{mount.path.replace('/', '_')}" if mount.type == "kv-v2" else None
    }

@app.get("/v1/sys/capabilities-self")
async def vault_sys_capabilities_self(
    request: Request,
    vault_token: VaultToken = Depends(get_vault_token_from_request)
):
    """Get capabilities for current token"""
    policies = json.loads(vault_token.policies)
    path = request.query_params.get("path", "")
    
    capabilities = []
    if "root" in policies:
        capabilities = ["create", "read", "update", "delete", "list", "sudo"]
    elif check_policy_access(policies, path, "read"):
        capabilities.append("read")
    if check_policy_access(policies, path, "list"):
        capabilities.append("list")
    if check_policy_access(policies, path, "create"):
        capabilities.append("create")
    if check_policy_access(policies, path, "update"):
        capabilities.append("update")
    if check_policy_access(policies, path, "delete"):
        capabilities.append("delete")
    
    return {"capabilities": capabilities}

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    log_startup()
    
    # Initialize Vault default mounts and policies
    try:
        db = next(get_db())
        initialize_default_mounts(db)
        initialize_default_policies(db)
        logger.info("Vault mounts and policies initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Vault defaults: {e}")
    
    logger.info("Secret Vault application started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    log_shutdown()
    logger.info("Secret Vault application shutting down")

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000,
        reload=settings.reload_on_change
    )
