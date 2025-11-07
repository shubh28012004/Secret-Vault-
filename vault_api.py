"""
Full HashiCorp Vault API Implementation
Provides complete Vault CLI compatibility for demo purposes
"""
import json
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status, Request
from models import VaultSecret, VaultMount, VaultToken, VaultPolicy, User
from encryption import encrypt_value, decrypt_value
from logger import get_logger

logger = get_logger("vault_api")

# Default mounts that should exist
DEFAULT_MOUNTS = {
    "secret/": {
        "type": "kv-v2",
        "description": "Key-value secret storage",
        "options": {"version": "2"}
    },
    "sys/": {
        "type": "system",
        "description": "System endpoints"
    }
}

def initialize_default_mounts(db: Session):
    """Initialize default secret engine mounts"""
    for mount_path, mount_config in DEFAULT_MOUNTS.items():
        existing = db.query(VaultMount).filter(VaultMount.path == mount_path.rstrip('/')).first()
        if not existing:
            mount = VaultMount(
                path=mount_path.rstrip('/'),
                type=mount_config["type"],
                description=mount_config.get("description", ""),
                options=json.dumps(mount_config.get("options", {}))
            )
            db.add(mount)
    db.commit()

def initialize_default_policies(db: Session):
    """Initialize default policies"""
    default_policies = {
        "default": """
path "secret/data/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/*" {
  capabilities = ["list", "read", "delete"]
}
""",
        "root": """
path "*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}
"""
    }
    
    for policy_name, policy_content in default_policies.items():
        existing = db.query(VaultPolicy).filter(VaultPolicy.name == policy_name).first()
        if not existing:
            policy = VaultPolicy(
                name=policy_name,
                policy=policy_content,
                description=f"Default {policy_name} policy"
            )
            db.add(policy)
    db.commit()

# KV v2 Secret Engine Functions
def get_kv_secret(db: Session, mount_path: str, secret_path: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Get a KV v2 secret"""
    query = db.query(VaultSecret).filter(
        and_(
            VaultSecret.mount_path == mount_path,
            VaultSecret.secret_path == secret_path,
            VaultSecret.destroyed == False
        )
    )
    
    if version:
        query = query.filter(VaultSecret.version == version)
    else:
        # Get latest version
        query = query.order_by(VaultSecret.version.desc())
    
    secret = query.first()
    if not secret or secret.deleted_time:
        return None
    
    try:
        data = json.loads(secret.data)
        metadata = json.loads(secret.secret_metadata) if secret.secret_metadata else {}
        return {
            "data": data,
            "metadata": {
                "version": secret.version,
                "created_time": secret.created_time.isoformat(),
                "deletion_time": secret.deleted_time.isoformat() if secret.deleted_time else "",
                "destroyed": secret.destroyed,
                **metadata
            }
        }
    except Exception as e:
        logger.error(f"Error parsing secret data: {e}")
        return None

def put_kv_secret(db: Session, mount_path: str, secret_path: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Store a KV v2 secret"""
    # Get current max version
    max_version = db.query(VaultSecret.version).filter(
        and_(
            VaultSecret.mount_path == mount_path,
            VaultSecret.secret_path == secret_path,
            VaultSecret.destroyed == False
        )
    ).order_by(VaultSecret.version.desc()).first()
    
    new_version = (max_version[0] + 1) if max_version else 1
    
    # Mark old versions as deleted if they exist
    db.query(VaultSecret).filter(
        and_(
            VaultSecret.mount_path == mount_path,
            VaultSecret.secret_path == secret_path,
            VaultSecret.deleted_time.is_(None)
        )
    ).update({"deleted_time": datetime.utcnow()})
    
    # Create new version
    secret = VaultSecret(
        mount_path=mount_path,
        secret_path=secret_path,
        version=new_version,
        data=json.dumps(data),
        secret_metadata=json.dumps(metadata or {}),
        created_time=datetime.utcnow()
    )
    db.add(secret)
    db.commit()
    db.refresh(secret)
    
    return {
        "version": new_version,
        "created_time": secret.created_time.isoformat()
    }

def delete_kv_secret(db: Session, mount_path: str, secret_path: str, versions: Optional[List[int]] = None) -> bool:
    """Delete KV v2 secret versions"""
    query = db.query(VaultSecret).filter(
        and_(
            VaultSecret.mount_path == mount_path,
            VaultSecret.secret_path == secret_path,
            VaultSecret.destroyed == False
        )
    )
    
    if versions:
        query = query.filter(VaultSecret.version.in_(versions))
    else:
        # Delete all versions
        query = query.filter(VaultSecret.deleted_time.is_(None))
    
    query.update({"deleted_time": datetime.utcnow()})
    db.commit()
    return True

def destroy_kv_secret(db: Session, mount_path: str, secret_path: str, versions: List[int]) -> bool:
    """Permanently destroy KV v2 secret versions"""
    db.query(VaultSecret).filter(
        and_(
            VaultSecret.mount_path == mount_path,
            VaultSecret.secret_path == secret_path,
            VaultSecret.version.in_(versions)
        )
    ).update({"destroyed": True})
    db.commit()
    return True

def list_kv_secrets(db: Session, mount_path: str, prefix: str = "") -> List[str]:
    """List KV v2 secrets under a path"""
    # Get all non-deleted, non-destroyed secrets for this mount
    query = db.query(VaultSecret.secret_path).filter(
        and_(
            VaultSecret.mount_path == mount_path,
            VaultSecret.destroyed == False,
            VaultSecret.deleted_time.is_(None)
        )
    ).distinct()
    
    if prefix:
        query = query.filter(VaultSecret.secret_path.like(f"{prefix}%"))
    
    paths = [row[0] for row in query.all()]
    
    if not paths:
        return []
    
    # Extract unique prefixes (directories) and files
    result = set()
    prefix_len = len(prefix) if prefix else 0
    
    for path in paths:
        if prefix and not path.startswith(prefix):
            continue
        
        # Remove prefix to get relative path
        if prefix_len > 0:
            relative_path = path[prefix_len:].lstrip('/')
        else:
            relative_path = path.lstrip('/')
        
        if not relative_path:
            continue
        
        if '/' in relative_path:
            # It's in a subdirectory - add the directory name
            dir_name = relative_path.split('/')[0]
            result.add(f"{dir_name}/")
        else:
            # It's a direct file
            result.add(relative_path)
    
    return sorted(list(result))

def get_kv_metadata(db: Session, mount_path: str, secret_path: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a KV v2 secret"""
    secrets_list = db.query(VaultSecret).filter(
        and_(
            VaultSecret.mount_path == mount_path,
            VaultSecret.secret_path == secret_path,
            VaultSecret.destroyed == False
        )
    ).order_by(VaultSecret.version.desc()).all()
    
    if not secrets_list:
        return None
    
    versions = {}
    current_version = None
    
    for secret in secrets_list:
        versions[str(secret.version)] = {
            "created_time": secret.created_time.isoformat(),
            "deletion_time": secret.deleted_time.isoformat() if secret.deleted_time else "",
            "destroyed": secret.destroyed
        }
        if not secret.deleted_time and not current_version:
            current_version = secret.version
    
    return {
        "versions": versions,
        "current_version": current_version
    }

# Token Management Functions
def create_vault_token(
    db: Session,
    policies: List[str] = None,
    ttl: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
    parent_token_id: Optional[str] = None,
    renewable: bool = True,
    num_uses: Optional[int] = None
) -> VaultToken:
    """Create a new Vault token"""
    token_id = secrets.token_urlsafe(32)
    
    if policies is None:
        policies = ["default"]
    
    expire_time = None
    if ttl:
        expire_time = datetime.utcnow() + timedelta(seconds=ttl)
    
    token = VaultToken(
        token_id=token_id,
        user_id=user_id,
        policies=json.dumps(policies),
        token_metadata=json.dumps(metadata or {}),
        ttl=ttl,
        creation_time=datetime.utcnow(),
        expire_time=expire_time,
        renewable=renewable,
        num_uses=num_uses,
        max_uses=num_uses,
        parent_token_id=parent_token_id
    )
    
    db.add(token)
    db.commit()
    db.refresh(token)
    
    return token

def get_vault_token(db: Session, token_id: str) -> Optional[VaultToken]:
    """Get a Vault token by ID"""
    token = db.query(VaultToken).filter(
        and_(
            VaultToken.token_id == token_id,
            VaultToken.revoked == False
        )
    ).first()
    
    if not token:
        return None
    
    # Check expiration
    if token.expire_time and token.expire_time < datetime.utcnow():
        return None
    
    # Check max uses
    if token.max_uses and token.num_uses >= token.max_uses:
        return None
    
    return token

def revoke_vault_token(db: Session, token_id: str) -> bool:
    """Revoke a Vault token"""
    token = db.query(VaultToken).filter(VaultToken.token_id == token_id).first()
    if not token:
        return False
    
    token.revoked = True
    db.commit()
    return True

def renew_vault_token(db: Session, token_id: str, increment: Optional[int] = None) -> Optional[VaultToken]:
    """Renew a Vault token"""
    token = get_vault_token(db, token_id)
    if not token or not token.renewable:
        return None
    
    if increment:
        new_expire_time = datetime.utcnow() + timedelta(seconds=increment)
    elif token.ttl:
        new_expire_time = datetime.utcnow() + timedelta(seconds=token.ttl)
    else:
        return token  # No expiration
    
    token.expire_time = new_expire_time
    token.last_renewal_time = datetime.utcnow()
    token.num_uses += 1
    db.commit()
    db.refresh(token)
    
    return token

# Mount Management Functions
def list_mounts(db: Session) -> Dict[str, Dict[str, Any]]:
    """List all secret engine mounts"""
    mounts = db.query(VaultMount).all()
    result = {}
    
    for mount in mounts:
        options = json.loads(mount.options) if mount.options else {}
        mount_info = {
            "type": mount.type,
            "description": mount.description or "",
            "options": options,
            "config": json.loads(mount.config) if mount.config else {}
        }
        # For KV v2, add accessor and version info
        if mount.type == "kv-v2":
            mount_info["accessor"] = f"kv_{mount.path.replace('/', '_')}"
            mount_info["options"]["version"] = "2"
        result[f"{mount.path}/"] = mount_info
    
    return result

def get_mount(db: Session, path: str) -> Optional[VaultMount]:
    """Get a mount by path"""
    return db.query(VaultMount).filter(VaultMount.path == path.rstrip('/')).first()

def create_mount(
    db: Session,
    path: str,
    mount_type: str,
    description: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    options: Optional[Dict[str, Any]] = None
) -> VaultMount:
    """Create a new secret engine mount"""
    mount = VaultMount(
        path=path.rstrip('/'),
        type=mount_type,
        description=description or "",
        config=json.dumps(config or {}),
        options=json.dumps(options or {})
    )
    db.add(mount)
    db.commit()
    db.refresh(mount)
    return mount

def delete_mount(db: Session, path: str) -> bool:
    """Delete a secret engine mount"""
    mount = get_mount(db, path)
    if not mount:
        return False
    
    db.delete(mount)
    db.commit()
    return True

# Policy Management Functions
def list_policies(db: Session) -> List[str]:
    """List all policy names"""
    policies = db.query(VaultPolicy.name).all()
    return [p[0] for p in policies]

def get_policy(db: Session, name: str) -> Optional[VaultPolicy]:
    """Get a policy by name"""
    return db.query(VaultPolicy).filter(VaultPolicy.name == name).first()

def create_or_update_policy(db: Session, name: str, policy: str, description: Optional[str] = None) -> VaultPolicy:
    """Create or update a policy"""
    existing = get_policy(db, name)
    if existing:
        existing.policy = policy
        existing.description = description or existing.description
        existing.updated_time = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_policy = VaultPolicy(
            name=name,
            policy=policy,
            description=description or ""
        )
        db.add(new_policy)
        db.commit()
        db.refresh(new_policy)
        return new_policy

def delete_policy(db: Session, name: str) -> bool:
    """Delete a policy"""
    policy = get_policy(db, name)
    if not policy:
        return False
    
    db.delete(policy)
    db.commit()
    return True

# Helper function to check policies (simplified)
def check_policy_access(policies: List[str], path: str, capability: str) -> bool:
    """Check if token policies allow access to a path with a capability"""
    # For demo purposes, we'll use simplified policy checking
    # In a real implementation, you'd parse HCL policies
    if "root" in policies:
        return True
    
    if "default" in policies:
        # Default policy allows read/list on secret/data/*
        if path.startswith("secret/data/") and capability in ["read", "list"]:
            return True
        if path.startswith("secret/metadata/") and capability in ["list", "read", "delete"]:
            return True
    
    return False

