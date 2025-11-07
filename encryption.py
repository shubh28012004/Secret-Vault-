"""
Encryption utilities for Secret Vault
"""
from cryptography.fernet import Fernet
import base64
import os
from pathlib import Path
from config import settings
from logger import get_logger
from typing import Optional

try:
    from vault_client import VaultClient
except Exception:
    VaultClient = None

logger = get_logger("encryption")

# Global encryption key
_encryption_key = None
_cipher_suite = None

def get_or_create_encryption_key():
    """Get existing encryption key or create a new one"""
    global _encryption_key, _cipher_suite
    
    # If a key is already loaded but cipher isn't initialized yet, initialize it
    if _encryption_key is not None:
        if _cipher_suite is None:
            _cipher_suite = Fernet(_encryption_key)
        return _encryption_key
    
    # If Vault is enabled and configured, try to retrieve the key from Vault first
    if settings.vault_enabled and VaultClient is not None and settings.validate_vault_settings():
        try:
            vault = VaultClient()
            key_from_vault = vault.get_encryption_key()
            if key_from_vault:
                _encryption_key = key_from_vault
                logger.info("Encryption key loaded from HashiCorp Vault")
            else:
                # Not present in Vault: generate, store in Vault, and also write a local fallback file
                _encryption_key = Fernet.generate_key()
                vault.set_encryption_key(_encryption_key)
                logger.info("New encryption key generated and stored in HashiCorp Vault")
        except Exception as e:
            logger.warning(f"Vault unavailable, falling back to file-based key storage: {e}")
            _encryption_key = None
    
    # Fallback to local key file if not set by Vault branch
    if _encryption_key is None:
        key_file = Path(settings.encryption_key_file)
        if key_file.exists():
            try:
                with open(key_file, "rb") as f:
                    _encryption_key = f.read()
                logger.info("Encryption key loaded from file")
            except Exception as e:
                logger.error(f"Failed to load encryption key: {e}")
                raise
        else:
            # Generate new key
            _encryption_key = Fernet.generate_key()
            try:
                # Ensure directory exists
                key_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Save key with restricted permissions
                with open(key_file, "wb") as f:
                    f.write(_encryption_key)
                
                # Set restrictive permissions (Unix-like systems)
                try:
                    os.chmod(key_file, 0o600)  # Owner read/write only
                except:
                    pass  # Windows doesn't support chmod
                
                logger.info("New encryption key generated and saved")
            except Exception as e:
                logger.error(f"Failed to save encryption key: {e}")
                raise
    
    # Initialize cipher suite
    _cipher_suite = Fernet(_encryption_key)
    return _encryption_key

def get_cipher_suite():
    """Get the initialized cipher suite"""
    if _cipher_suite is None:
        # Ensure key and cipher are initialized
        get_or_create_encryption_key()
    return _cipher_suite

def encrypt_value(value: str) -> str:
    """Encrypt a string value"""
    if not value:
        return ""
    
    try:
        cipher = get_cipher_suite()
        encrypted = cipher.encrypt(value.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8')
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise ValueError("Failed to encrypt value")

def decrypt_value(encrypted_value: str) -> str:
    """Decrypt an encrypted string value"""
    if not encrypted_value:
        return ""
    
    try:
        cipher = get_cipher_suite()
        encrypted_bytes = base64.b64decode(encrypted_value.encode('utf-8'))
        decrypted = cipher.decrypt(encrypted_bytes)
        return decrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise ValueError("Failed to decrypt value")

def rotate_encryption_key():
    """Rotate the encryption key (for security maintenance)"""
    # This is a complex operation that would require re-encrypting all data
    # In production, this should be done carefully with proper backup
    logger.warning("Key rotation requested - this is a complex operation")
    # Implementation would require:
    # 1. Backup all data
    # 2. Generate new key
    # 3. Re-encrypt all credentials
    # 4. Update key file
    # 5. Verify all data is accessible
    pass

def verify_encryption_key():
    """Verify that the encryption key is working properly"""
    try:
        test_value = "test_encryption_key"
        encrypted = encrypt_value(test_value)
        decrypted = decrypt_value(encrypted)
        
        if decrypted == test_value:
            logger.info("Encryption key verification successful")
            return True
        else:
            logger.error("Encryption key verification failed")
            return False
    except Exception as e:
        logger.error(f"Encryption key verification error: {e}")
        return False

def get_encryption_key_info():
    """Get information about the encryption key (for admin purposes)"""
    try:
        key = get_or_create_encryption_key()
        key_file = Path(settings.encryption_key_file)
        vault_info = None
        if settings.vault_enabled and VaultClient is not None and settings.validate_vault_settings():
            try:
                vault = VaultClient()
                present = vault.get_encryption_key() is not None
                vault_info = {
                    "enabled": True,
                    "status": "connected",
                    "addr": settings.vault_addr,
                    "kv_mount": settings.vault_kv_mount,
                    "key_present": present
                }
            except Exception as e:
                vault_info = {
                    "enabled": True, 
                    "status": "error",
                    "error": str(e)
                }
        else:
            vault_info = {"enabled": False, "status": "disabled"}

        return {
            "key_exists": True,
            "key_length": len(key),
            "key_file_path": str(key_file),
            "key_file_exists": key_file.exists(),
            "key_file_size": key_file.stat().st_size if key_file.exists() else 0,
            "verification_status": verify_encryption_key(),
            "vault": vault_info
        }
    except Exception as e:
        return {
            "key_exists": False,
            "error": str(e)
        }
