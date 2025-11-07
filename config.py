"""
Configuration management for Secret Vault
"""
import os
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv
from typing import List

load_dotenv()

class Settings:
    """Application settings loaded from environment variables"""
    
    def __init__(self):
        # Application Settings
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "true").lower() == "true"
        self.secret_key = os.getenv("SECRET_KEY", "your-super-secret-key-change-this-in-production")
        self.admin_username = os.getenv("ADMIN_USERNAME", "admin")
        self.admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        
        # Database Settings
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./secret_vault.db")
        
        # Email Settings (supports SMTP_SERVER or legacy SMTP_HOST)
        self.smtp_server: str = os.getenv("SMTP_SERVER") or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username: str = os.getenv("SMTP_USERNAME", "")
        self.smtp_password: str = os.getenv("SMTP_PASSWORD", "")
        self.smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        
        # Email settings
        self.from_email: str = os.getenv("FROM_EMAIL", "secretvault81@gmail.com")
        self.from_name: str = os.getenv("FROM_NAME", "Secret Vault")
        # Optional default recipient for notifications
        self.email_to: str = os.getenv("EMAIL_TO", "")
        
        # OTP Configuration
        self.otp_expiry_minutes: int = int(os.getenv("OTP_EXPIRY_MINUTES", "10"))
        self.otp_max_attempts: int = int(os.getenv("OTP_MAX_ATTEMPTS", "3"))
        
        # Security Settings
        self.encryption_key_file = os.getenv("ENCRYPTION_KEY_FILE", "encryption_key.key")
        self.session_timeout = int(os.getenv("SESSION_TIMEOUT", "3600"))
        self.max_login_attempts = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        self.lockout_duration = int(os.getenv("LOCKOUT_DURATION", "900"))
        
        # Logging Settings
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "secret_vault.log")
        self.log_max_size = os.getenv("LOG_MAX_SIZE", "10MB")
        self.log_backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
        
        # Backup Settings
        self.backup_enabled = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
        self.backup_dir = os.getenv("BACKUP_DIR", "./backups")
        self.backup_retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
        self.auto_backup_interval = os.getenv("AUTO_BACKUP_INTERVAL", "24h")
        
        # Notification Settings
        self.email_notifications = os.getenv("EMAIL_NOTIFICATIONS", "true").lower() == "true"
        self.expiry_warning_days = int(os.getenv("EXPIRY_WARNING_DAYS", "30"))
        self.daily_digest = os.getenv("DAILY_DIGEST", "true").lower() == "true"
        self.digest_time = os.getenv("DIGEST_TIME", "09:00")

        # Vault Settings
        self.vault_enabled = os.getenv("VAULT_ENABLED", "false").lower() == "true"
        self.vault_addr = os.getenv("VAULT_ADDR")
        self.vault_token = os.getenv("VAULT_TOKEN")
        self.vault_namespace = os.getenv("VAULT_NAMESPACE")
        # KV v2 mount and path to store the encryption key
        self.vault_kv_mount = os.getenv("VAULT_KV_MOUNT", "secret")
        self.vault_key_path = os.getenv("VAULT_KEY_PATH", "secret-vault/encryption-key")
        
        # API Settings
        self.api_rate_limit = int(os.getenv("API_RATE_LIMIT", "100"))
        self.api_rate_limit_window = int(os.getenv("API_RATE_LIMIT_WINDOW", "3600"))
        self.cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000,http://127.0.0.1:3000")
        
        # Development Settings
        self.reload_on_change = os.getenv("RELOAD_ON_CHANGE", "true").lower() == "true"
        self.show_debug_info = os.getenv("SHOW_DEBUG_INFO", "true").lower() == "true"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() == "development"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    @property
    def email_from(self) -> str:
        """Alias for from_email for backwards compatibility"""
        return self.from_email
    
    @property
    def log_max_size_bytes(self) -> int:
        """Convert log max size string to bytes"""
        size_str = self.log_max_size.upper()
        if size_str.endswith("MB"):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith("KB"):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith("B"):
            return int(size_str[:-1])
        else:
            return int(size_str) * 1024 * 1024  # Default to MB
    
    def get_backup_path(self, filename: str) -> Path:
        """Get full backup file path"""
        backup_dir = Path(self.backup_dir)
        backup_dir.mkdir(exist_ok=True)
        return backup_dir / filename
    
    def validate_email_settings(self) -> bool:
        """Validate that email settings are complete"""
        required_fields = [
            self.smtp_server,
            self.smtp_username,
            self.smtp_password,
            self.from_email
        ]
        return all(field is not None and field.strip() for field in required_fields)

    def validate_vault_settings(self) -> bool:
        """Validate that Vault settings are complete when enabled"""
        if not self.vault_enabled:
            return False
        required_fields = [
            self.vault_addr,
            self.vault_token,
            self.vault_kv_mount,
            self.vault_key_path
        ]
        return all(field is not None and str(field).strip() for field in required_fields)


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


def create_env_file():
    """Create a .env file from the example if it doesn't exist"""
    env_file = Path(".env")
    if not env_file.exists():
        example_file = Path("env.example")
        if example_file.exists():
            import shutil
            shutil.copy(example_file, env_file)
            print(f"Created .env file from {example_file}")
        else:
            print("No env.example file found. Please create .env manually.")


def validate_configuration():
    """Validate the current configuration"""
    issues = []
    
    # Check for weak default password in production
    if settings.is_production and settings.admin_password == "admin123":
        issues.append("WARNING: Using default admin password in production!")
    
    # Check for weak secret key
    if settings.secret_key == "your-super-secret-key-change-this-in-production":
        issues.append("WARNING: Using default secret key!")
    
    # Check email configuration
    if settings.email_notifications and not settings.validate_email_settings():
        issues.append("WARNING: Email notifications enabled but email settings incomplete")
    
    # Check backup directory
    if settings.backup_enabled:
        backup_path = Path(settings.backup_dir)
        if not backup_path.exists():
            try:
                backup_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                issues.append(f"ERROR: Cannot create backup directory: {e}")
    
    # Check log directory
    log_path = Path(settings.log_file).parent
    if log_path != Path(".") and not log_path.exists():
        try:
            log_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            issues.append(f"ERROR: Cannot create log directory: {e}")

    # Validate Vault configuration if enabled
    if settings.vault_enabled and not settings.validate_vault_settings():
        issues.append("WARNING: VAULT_ENABLED=true but Vault settings are incomplete")
    
    return issues


if __name__ == "__main__":
    # Create .env file if it doesn't exist
    create_env_file()
    
    # Validate configuration
    issues = validate_configuration()
    
    if issues:
        print("Configuration Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Configuration validation passed!")
    
    # Print current settings (without sensitive data)
    print(f"\nCurrent Configuration:")
    print(f"  Environment: {settings.environment}")
    print(f"  Debug: {settings.debug}")
    print(f"  Database: {settings.database_url}")
    print(f"  Email Notifications: {settings.email_notifications}")
    print(f"  Backup Enabled: {settings.backup_enabled}")
    print(f"  CORS Origins: {settings.cors_origins_list}")