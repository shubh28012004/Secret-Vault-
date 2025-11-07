"""
Lightweight HashiCorp Vault client wrapper for Secret Vault
"""
import os
from typing import Optional, Tuple

import hvac

from config import settings
from logger import get_logger


logger = get_logger("vault")


class VaultClient:
    """Simple wrapper around hvac.Client for KV v2 operations"""

    def __init__(self):
        if not settings.vault_enabled:
            raise RuntimeError("Vault is not enabled")

        if not settings.validate_vault_settings():
            raise RuntimeError("Vault settings are incomplete")

        self.addr = settings.vault_addr
        self.token = settings.vault_token
        self.namespace = settings.vault_namespace
        self.kv_mount = settings.vault_kv_mount
        self.key_path = settings.vault_key_path

        self.client = hvac.Client(url=self.addr, token=self.token, namespace=self.namespace)

        if not self.client.is_authenticated():
            raise RuntimeError("Failed to authenticate to Vault")

    def get_secret(self, path: Optional[str] = None) -> Optional[dict]:
        """Read a secret dict from KV v2"""
        try:
            secret_path = path or self.key_path
            result = self.client.secrets.kv.v2.read_secret_version(mount_point=self.kv_mount, path=secret_path)
            return result.get("data", {}).get("data")
        except hvac.exceptions.InvalidPath:
            return None
        except Exception as e:
            logger.error(f"Vault read error: {e}")
            raise

    def put_secret(self, data: dict, path: Optional[str] = None) -> bool:
        """Write a secret dict to KV v2"""
        try:
            secret_path = path or self.key_path
            self.client.secrets.kv.v2.create_or_update_secret(
                mount_point=self.kv_mount,
                path=secret_path,
                secret=data,
            )
            return True
        except Exception as e:
            logger.error(f"Vault write error: {e}")
            raise

    def get_encryption_key(self) -> Optional[bytes]:
        """Fetch the application's encryption key from Vault (stored base64)"""
        secret = self.get_secret()
        if not secret:
            return None
        key_b64 = secret.get("fernet_key")
        if not key_b64:
            return None
        try:
            return key_b64.encode("utf-8")
        except Exception:
            return None

    def set_encryption_key(self, key: bytes) -> bool:
        """Store the application's encryption key under fernet_key in Vault"""
        return self.put_secret({"fernet_key": key.decode("utf-8")})


def vault_status() -> dict:
    """Return a small status dict for health endpoints"""
    if not settings.vault_enabled:
        return {"enabled": False, "status": "disabled"}
    
    try:
        # Check if vault settings are valid
        if not settings.validate_vault_settings():
            return {"enabled": False, "status": "misconfigured", "error": "Invalid vault settings"}
        
        # Try to create client and test connection
        client = hvac.Client(url=settings.vault_addr, token=settings.vault_token)
        
        # Test authentication
        if not client.is_authenticated():
            return {"enabled": True, "status": "auth_failed", "error": "Authentication failed"}
        
        # Try a simple read operation
        try:
            _ = client.secrets.kv.v2.read_secret_version(
                mount_point=settings.vault_kv_mount, 
                path=settings.vault_key_path
            )
            return {
                "enabled": True, 
                "status": "connected", 
                "addr": settings.vault_addr, 
                "kv_mount": settings.vault_kv_mount
            }
        except hvac.exceptions.InvalidPath:
            # Path doesn't exist, but connection is working
            return {
                "enabled": True, 
                "status": "connected", 
                "addr": settings.vault_addr, 
                "kv_mount": settings.vault_kv_mount,
                "note": "Key path does not exist yet"
            }
            
    except hvac.exceptions.ConnectionError as e:
        return {"enabled": True, "status": "connection_failed", "error": "Cannot connect to Vault server"}
    except hvac.exceptions.AuthenticationError as e:
        return {"enabled": True, "status": "auth_failed", "error": "Authentication failed"}
    except Exception as e:
        return {"enabled": True, "status": "error", "error": str(e)}


