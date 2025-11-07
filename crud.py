"""
CRUD operations for Secret Vault with multi-user support
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Optional
from datetime import datetime, timedelta
from models import User, Credential, AuditLog, UserCreate, UserUpdate
from auth import get_password_hash, hash_token
from logger import get_logger

logger = get_logger("crud")

# User CRUD operations
def create_user(db: Session, user: UserCreate) -> User:
    """Create a new user"""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email.lower()).first()
    if existing_user:
        raise ValueError("Email already registered")
    
    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user.username.lower()).first()
    if existing_username:
        raise ValueError("Username already taken")
    
    # Create user with hashed password
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email.lower(),
        username=user.username.lower(),
        hashed_password=hashed_password,
        full_name=user.full_name,
        is_active=False,  # Requires email verification
        is_verified=False
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"New user created: {user.email}")
    return db_user

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email.lower()).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username.lower()).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()

def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
    """Update user information"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    
    # Hash password if provided
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"User updated: {db_user.email}")
    return db_user

def verify_user_email(db: Session, token: str) -> bool:
    """Verify user email with token"""
    hashed_token = hash_token(token)
    user = db.query(User).filter(User.email_verification_token == hashed_token).first()
    
    if not user:
        return False
    
    user.is_verified = True
    user.is_active = True
    user.email_verification_token = None
    user.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Email verified for user: {user.email}")
    return True

def set_password_reset_token(db: Session, email: str) -> Optional[str]:
    """Set password reset token for user"""
    user = get_user_by_email(db, email)
    if not user:
        return None
    
    # Generate new token
    from auth import create_password_reset_token
    token = create_password_reset_token()
    hashed_token = hash_token(token)
    
    user.password_reset_token = hashed_token
    user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
    user.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Password reset token set for user: {email}")
    return token

def reset_password_with_token(db: Session, token: str, new_password: str) -> bool:
    """Reset password using token"""
    hashed_token = hash_token(token)
    user = db.query(User).filter(
        and_(
            User.password_reset_token == hashed_token,
            User.password_reset_expires > datetime.utcnow()
        )
    ).first()
    
    if not user:
        return False
    
    # Update password and clear token
    user.hashed_password = get_password_hash(new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    user.failed_login_attempts = 0  # Reset failed attempts
    user.locked_until = None
    user.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Password reset for user: {user.email}")
    return True

# Credential CRUD operations (user-specific)
def create_credential(db: Session, credential: dict, user_id: int) -> Credential:
    """Create a new credential for a specific user"""
    from encryption import encrypt_value
    
    # Encrypt the password
    encrypted_password = encrypt_value(credential["password"])
    
    db_credential = Credential(
        user_id=user_id,
        title=credential["title"],
        username=credential["username"],
        encrypted_password=encrypted_password,
        category=credential.get("category", "General"),
        url=credential.get("url"),
        notes=credential.get("notes"),
        expires_at=credential.get("expires_at")
    )
    
    db.add(db_credential)
    db.commit()
    db.refresh(db_credential)
    
    logger.info(f"Credential created for user {user_id}: {credential['title']}")
    return db_credential

def get_credentials(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Credential]:
    """Get all credentials for a specific user"""
    return db.query(Credential).filter(
        Credential.user_id == user_id
    ).offset(skip).limit(limit).all()

def get_credentials_with_decrypted_passwords(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[dict]:
    """Get all credentials for a specific user with decrypted passwords"""
    from encryption import decrypt_value
    
    credentials = db.query(Credential).filter(
        Credential.user_id == user_id
    ).offset(skip).limit(limit).all()
    
    result = []
    for cred in credentials:
        try:
            decrypted_password = decrypt_value(cred.encrypted_password)
            cred_dict = {
                "id": cred.id,
                "user_id": cred.user_id,
                "title": cred.title,
                "username": cred.username,
                "password": decrypted_password,
                "category": cred.category,
                "url": cred.url,
                "notes": cred.notes,
                "is_active": cred.is_active,
                "expires_at": cred.expires_at,
                "created_at": cred.created_at,
                "updated_at": cred.updated_at
            }
            result.append(cred_dict)
        except Exception as e:
            logger.error(f"Failed to decrypt password for credential {cred.id}: {e}")
            # Include credential with error message for password
            cred_dict = {
                "id": cred.id,
                "user_id": cred.user_id,
                "title": cred.title,
                "username": cred.username,
                "password": "*** DECRYPTION ERROR ***",
                "category": cred.category,
                "url": cred.url,
                "notes": cred.notes,
                "is_active": cred.is_active,
                "expires_at": cred.expires_at,
                "created_at": cred.created_at,
                "updated_at": cred.updated_at
            }
            result.append(cred_dict)
    
    return result

def get_credential_by_id(db: Session, credential_id: int, user_id: int) -> Optional[Credential]:
    """Get a specific credential by ID for a specific user"""
    return db.query(Credential).filter(
        and_(
            Credential.id == credential_id,
            Credential.user_id == user_id
        )
    ).first()

def update_credential(db: Session, credential_id: int, user_id: int, credential_update: dict) -> Optional[Credential]:
    """Update a credential for a specific user"""
    db_credential = get_credential_by_id(db, credential_id, user_id)
    if not db_credential:
        return None
    
    update_data = credential_update.copy()
    
    # Encrypt password if provided
    if "password" in update_data:
        from encryption import encrypt_value
        update_data["encrypted_password"] = encrypt_value(update_data.pop("password"))
    
    for field, value in update_data.items():
        if hasattr(db_credential, field):
            setattr(db_credential, field, value)
    
    db_credential.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_credential)
    
    logger.info(f"Credential updated for user {user_id}: {db_credential.title}")
    return db_credential

def delete_credential(db: Session, credential_id: int, user_id: int) -> bool:
    """Delete a credential for a specific user"""
    db_credential = get_credential_by_id(db, credential_id, user_id)
    if not db_credential:
        return False
    
    title = db_credential.title
    db.delete(db_credential)
    db.commit()
    
    logger.info(f"Credential deleted for user {user_id}: {title}")
    return True

def search_credentials(db: Session, user_id: int, query: str) -> List[Credential]:
    """Search credentials for a specific user"""
    return db.query(Credential).filter(
        and_(
            Credential.user_id == user_id,
            or_(
                Credential.title.ilike(f"%{query}%"),
                Credential.username.ilike(f"%{query}%"),
                Credential.category.ilike(f"%{query}%"),
                Credential.notes.ilike(f"%{query}%")
            )
        )
    ).all()

def search_credentials_with_decrypted_passwords(db: Session, user_id: int, query: str) -> List[dict]:
    """Search credentials for a specific user with decrypted passwords"""
    from encryption import decrypt_value
    
    credentials = db.query(Credential).filter(
        and_(
            Credential.user_id == user_id,
            or_(
                Credential.title.ilike(f"%{query}%"),
                Credential.username.ilike(f"%{query}%"),
                Credential.category.ilike(f"%{query}%"),
                Credential.notes.ilike(f"%{query}%")
            )
        )
    ).all()
    
    result = []
    for cred in credentials:
        try:
            decrypted_password = decrypt_value(cred.encrypted_password)
            cred_dict = {
                "id": cred.id,
                "user_id": cred.user_id,
                "title": cred.title,
                "username": cred.username,
                "password": decrypted_password,
                "category": cred.category,
                "url": cred.url,
                "notes": cred.notes,
                "is_active": cred.is_active,
                "expires_at": cred.expires_at,
                "created_at": cred.created_at,
                "updated_at": cred.updated_at
            }
            result.append(cred_dict)
        except Exception as e:
            logger.error(f"Failed to decrypt password for credential {cred.id}: {e}")
            # Include credential with error message for password
            cred_dict = {
                "id": cred.id,
                "user_id": cred.user_id,
                "title": cred.title,
                "username": cred.username,
                "password": "*** DECRYPTION ERROR ***",
                "category": cred.category,
                "url": cred.url,
                "notes": cred.notes,
                "is_active": cred.is_active,
                "expires_at": cred.expires_at,
                "created_at": cred.created_at,
                "updated_at": cred.updated_at
            }
            result.append(cred_dict)
    
    return result

def get_credentials_by_category(db: Session, user_id: int, category: str) -> List[Credential]:
    """Get credentials by category for a specific user"""
    return db.query(Credential).filter(
        and_(
            Credential.user_id == user_id,
            Credential.category == category
        )
    ).all()

def get_credentials_by_category_with_decrypted_passwords(db: Session, user_id: int, category: str) -> List[dict]:
    """Get credentials by category for a specific user with decrypted passwords"""
    from encryption import decrypt_value
    
    credentials = db.query(Credential).filter(
        and_(
            Credential.user_id == user_id,
            Credential.category == category
        )
    ).all()
    
    result = []
    for cred in credentials:
        try:
            decrypted_password = decrypt_value(cred.encrypted_password)
            cred_dict = {
                "id": cred.id,
                "user_id": cred.user_id,
                "title": cred.title,
                "username": cred.username,
                "password": decrypted_password,
                "category": cred.category,
                "url": cred.url,
                "notes": cred.notes,
                "is_active": cred.is_active,
                "expires_at": cred.expires_at,
                "created_at": cred.created_at,
                "updated_at": cred.updated_at
            }
            result.append(cred_dict)
        except Exception as e:
            logger.error(f"Failed to decrypt password for credential {cred.id}: {e}")
            # Include credential with error message for password
            cred_dict = {
                "id": cred.id,
                "user_id": cred.user_id,
                "title": cred.title,
                "username": cred.username,
                "password": "*** DECRYPTION ERROR ***",
                "category": cred.category,
                "url": cred.url,
                "notes": cred.notes,
                "is_active": cred.is_active,
                "expires_at": cred.expires_at,
                "created_at": cred.created_at,
                "updated_at": cred.updated_at
            }
            result.append(cred_dict)
    
    return result

def get_expiring_credentials(db: Session, user_id: int, days: int = 30) -> List[Credential]:
    """Get credentials expiring within specified days for a specific user"""
    expiry_date = datetime.utcnow() + timedelta(days=days)
    return db.query(Credential).filter(
        and_(
            Credential.user_id == user_id,
            Credential.expires_at <= expiry_date,
            Credential.expires_at >= datetime.utcnow(),
            Credential.is_active == True
        )
    ).all()

# Audit Log CRUD operations
def create_audit_log(db: Session, user_id: int, action: str, details: str, 
                    ip_address: str = None, user_agent: str = None) -> AuditLog:
    """Create an audit log entry"""
    db_audit = AuditLog(
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    db.add(db_audit)
    db.commit()
    db.refresh(db_audit)
    
    return db_audit

def get_audit_logs(db: Session, user_id: int = None, skip: int = 0, limit: int = 100) -> List[AuditLog]:
    """Get audit logs, optionally filtered by user"""
    query = db.query(AuditLog)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    return query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit).all()

def get_audit_logs_by_action(db: Session, action: str, user_id: int = None) -> List[AuditLog]:
    """Get audit logs by action, optionally filtered by user"""
    query = db.query(AuditLog).filter(AuditLog.action == action)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    return query.order_by(desc(AuditLog.created_at)).all()

def get_user_activity_summary(db: Session, user_id: int, days: int = 30) -> dict:
    """Get user activity summary for the last N days"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get total activities
    total_activities = db.query(AuditLog).filter(
        and_(
            AuditLog.user_id == user_id,
            AuditLog.created_at >= start_date
        )
    ).count()
    
    # Get activities by type
    activities_by_type = db.query(AuditLog.action, db.func.count(AuditLog.id)).filter(
        and_(
            AuditLog.user_id == user_id,
            AuditLog.created_at >= start_date
        )
    ).group_by(AuditLog.action).all()
    
    # Get recent activities
    recent_activities = db.query(AuditLog).filter(
        and_(
            AuditLog.user_id == user_id,
            AuditLog.created_at >= start_date
        )
    ).order_by(desc(AuditLog.created_at)).limit(10).all()
    
    return {
        "total_activities": total_activities,
        "activities_by_type": dict(activities_by_type),
        "recent_activities": recent_activities,
        "period_days": days
    }

# Admin operations
def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Get all users (admin only)"""
    return db.query(User).offset(skip).limit(limit).all()

def get_user_stats(db: Session) -> dict:
    """Get user statistics (admin only)"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    verified_users = db.query(User).filter(User.is_verified == True).count()
    admin_users = db.query(User).filter(User.is_admin == True).count()
    
    # Recent registrations
    recent_users = db.query(User).filter(
        User.created_at >= datetime.utcnow() - timedelta(days=7)
    ).count()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "verified_users": verified_users,
        "admin_users": admin_users,
        "recent_registrations": recent_users
    }

def deactivate_user(db: Session, user_id: int) -> bool:
    """Deactivate a user (admin only)"""
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    
    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"User deactivated: {user.email}")
    return True

def activate_user(db: Session, user_id: int) -> bool:
    """Activate a user (admin only)"""
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    
    user.is_active = True
    user.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"User activated: {user.email}")
    return True

def promote_to_admin(db: Session, user_id: int) -> bool:
    """Promote user to admin (admin only)"""
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    
    user.is_admin = True
    user.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"User promoted to admin: {user.email}")
    return True
