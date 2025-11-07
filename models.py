from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime
import re

Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=False)  # Email verification required
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    email_verification_token = Column(String(255), unique=True, nullable=True)
    password_reset_token = Column(String(255), unique=True, nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    credentials = relationship("Credential", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_username', 'username'),
        Index('idx_user_verification_token', 'email_verification_token'),
        Index('idx_user_reset_token', 'password_reset_token'),
    )

class Credential(Base):
    __tablename__ = "credentials"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(100), nullable=False)
    username = Column(String(100), nullable=False)
    encrypted_password = Column(Text, nullable=False)
    category = Column(String(50), default="General")
    url = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationship
    user = relationship("User", back_populates="credentials")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_credential_user_id', 'user_id'),
        Index('idx_credential_category', 'category'),
        Index('idx_credential_expires', 'expires_at'),
    )

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)  # LOGIN, LOGOUT, CREATE, UPDATE, DELETE, VIEW
    details = Column(Text, nullable=False)
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationship
    user = relationship("User", back_populates="audit_logs")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_audit_user_id', 'user_id'),
        Index('idx_audit_action', 'action'),
        Index('idx_audit_created_at', 'created_at'),
    )

# Pydantic Models for API
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', v):
            raise ValueError('Username must be 3-20 characters, alphanumeric and underscore only')
        return v.lower()
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters')
        return v.strip()

class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if v is not None:
            if len(v) < 8:
                raise ValueError('Password must be at least 8 characters')
            if not re.search(r'[A-Z]', v):
                raise ValueError('Password must contain at least one uppercase letter')
            if not re.search(r'[a-z]', v):
                raise ValueError('Password must contain at least one lowercase letter')
            if not re.search(r'\d', v):
                raise ValueError('Password must contain at least one digit')
        return v

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    is_active: bool
    is_verified: bool
    is_admin: bool
    last_login: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: str
    password: str

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v

class EmailVerification(BaseModel):
    token: str

class CredentialBase(BaseModel):
    title: str
    username: str
    password: str
    category: str = "General"
    url: Optional[str] = None
    notes: Optional[str] = None
    expires_at: Optional[datetime] = None

class CredentialCreate(CredentialBase):
    pass

class CredentialUpdate(BaseModel):
    title: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    category: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None

class CredentialResponse(BaseModel):
    id: int
    user_id: int
    title: str
    username: str
    password: str  # Will be populated with decrypted password
    category: str
    url: Optional[str]
    notes: Optional[str]
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    details: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None

class OTPRequest(BaseModel):
    email: str

class OTPVerification(BaseModel):
    email: str
    otp: str

class UserRegistrationWithOTP(BaseModel):
    email: str
    username: str
    full_name: str
    password: str
    otp: str

# Vault-specific Models
class VaultSecret(Base):
    """Store Vault KV secrets"""
    __tablename__ = "vault_secrets"
    
    id = Column(Integer, primary_key=True, index=True)
    mount_path = Column(String(100), nullable=False, index=True)  # e.g., "secret"
    secret_path = Column(String(500), nullable=False, index=True)  # e.g., "myapp/database"
    version = Column(Integer, default=1, nullable=False)
    data = Column(Text, nullable=False)  # JSON-encoded secret data
    secret_metadata = Column(Text, nullable=True)  # JSON-encoded metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    created_time = Column(DateTime, default=func.now(), nullable=False)
    deleted_time = Column(DateTime, nullable=True)
    destroyed = Column(Boolean, default=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_vault_secret_path', 'mount_path', 'secret_path', 'version'),
        Index('idx_vault_secret_mount', 'mount_path'),
    )

class VaultMount(Base):
    """Store Vault secret engine mounts"""
    __tablename__ = "vault_mounts"
    
    id = Column(Integer, primary_key=True, index=True)
    path = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "secret"
    type = Column(String(50), nullable=False)  # e.g., "kv", "kv-v2"
    description = Column(String(500), nullable=True)
    config = Column(Text, nullable=True)  # JSON-encoded config
    options = Column(Text, nullable=True)  # JSON-encoded options
    created_time = Column(DateTime, default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_vault_mount_path', 'path'),
    )

class VaultToken(Base):
    """Store Vault tokens (separate from JWT tokens)"""
    __tablename__ = "vault_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    policies = Column(Text, nullable=False)  # JSON array of policy names
    token_metadata = Column(Text, nullable=True)  # JSON-encoded metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    ttl = Column(Integer, nullable=True)  # Time to live in seconds
    creation_time = Column(DateTime, default=func.now(), nullable=False)
    expire_time = Column(DateTime, nullable=True)
    last_renewal_time = Column(DateTime, nullable=True)
    num_uses = Column(Integer, default=0)
    max_uses = Column(Integer, nullable=True)  # None = unlimited
    renewable = Column(Boolean, default=True)
    revoked = Column(Boolean, default=False)
    parent_token_id = Column(String(255), nullable=True)
    
    __table_args__ = (
        Index('idx_vault_token_id', 'token_id'),
        Index('idx_vault_token_user', 'user_id'),
        Index('idx_vault_token_expire', 'expire_time'),
    )

class VaultPolicy(Base):
    """Store Vault policies"""
    __tablename__ = "vault_policies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    policy = Column(Text, nullable=False)  # HCL policy content
    description = Column(String(500), nullable=True)
    created_time = Column(DateTime, default=func.now(), nullable=False)
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_vault_policy_name', 'name'),
    )