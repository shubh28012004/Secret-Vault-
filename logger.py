"""
Logging configuration for Secret Vault
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import json
from config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry)


class ColoredFormatter(logging.Formatter):
    """Custom colored formatter for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to level name
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{level_color}{record.levelname}{self.COLORS['RESET']}"
        
        # Format the message
        formatted = super().format(record)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] {formatted}"


def setup_logger(name: str = "secret_vault", level: Optional[str] = None) -> logging.Logger:
    """Setup and configure the application logger"""
    
    # Get log level from settings or use default
    log_level = level or settings.log_level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatters
    console_formatter = ColoredFormatter(
        '%(levelname)s - %(name)s - %(message)s'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    json_formatter = JSONFormatter()
    
    # Console handler (for development)
    if settings.is_development:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path,
            maxBytes=settings.log_max_size_bytes,
            backupCount=settings.log_backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # JSON file handler for structured logging (production)
    if settings.is_production:
        json_log_path = Path(settings.log_file).with_suffix('.json')
        json_handler = logging.handlers.RotatingFileHandler(
            filename=json_log_path,
            maxBytes=settings.log_max_size_bytes,
            backupCount=settings.log_backup_count,
            encoding='utf-8'
        )
        json_handler.setLevel(numeric_level)
        json_handler.setFormatter(json_formatter)
        logger.addHandler(json_handler)
    
    return logger


def get_logger(name: str = "secret_vault") -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)


def log_security_event(logger: logging.Logger, event_type: str, user: str, details: str, ip_address: Optional[str] = None):
    """Log security-related events"""
    extra_fields = {
        "event_type": "security",
        "security_event": event_type,
        "user": user,
        "ip_address": ip_address
    }
    
    logger.warning(f"Security Event: {event_type} - {details}", extra={"extra_fields": extra_fields})


def log_api_request(logger: logging.Logger, method: str, path: str, user: str, status_code: int, response_time: float, ip_address: Optional[str] = None):
    """Log API requests"""
    extra_fields = {
        "event_type": "api_request",
        "method": method,
        "path": path,
        "user": user,
        "status_code": status_code,
        "response_time": response_time,
        "ip_address": ip_address
    }
    
    level = logging.ERROR if status_code >= 400 else logging.INFO
    logger.log(level, f"API Request: {method} {path} - {status_code} ({response_time:.3f}s)", extra={"extra_fields": extra_fields})


def log_database_operation(logger: logging.Logger, operation: str, table: str, user: str, details: str):
    """Log database operations"""
    extra_fields = {
        "event_type": "database",
        "operation": operation,
        "table": table,
        "user": user
    }
    
    logger.info(f"Database {operation} on {table}: {details}", extra={"extra_fields": extra_fields})


def log_backup_operation(logger: logging.Logger, operation: str, filename: str, size: Optional[int] = None, success: bool = True):
    """Log backup operations"""
    extra_fields = {
        "event_type": "backup",
        "operation": operation,
        "filename": filename,
        "size_bytes": size,
        "success": success
    }
    
    level = logging.ERROR if not success else logging.INFO
    message = f"Backup {operation}: {filename}"
    if size:
        message += f" ({size} bytes)"
    
    logger.log(level, message, extra={"extra_fields": extra_fields})


def log_email_notification(logger: logging.Logger, recipient: str, subject: str, success: bool, error: Optional[str] = None):
    """Log email notifications"""
    extra_fields = {
        "event_type": "email",
        "recipient": recipient,
        "subject": subject,
        "success": success,
        "error": error
    }
    
    level = logging.ERROR if not success else logging.INFO
    message = f"Email notification to {recipient}: {subject}"
    if error:
        message += f" - Error: {error}"
    
    logger.log(level, message, extra={"extra_fields": extra_fields})


def log_credential_operation(logger: logging.Logger, operation: str, credential_id: int, user: str, title: str):
    """Log credential operations"""
    extra_fields = {
        "event_type": "credential",
        "operation": operation,
        "credential_id": credential_id,
        "user": user,
        "title": title
    }
    
    logger.info(f"Credential {operation}: {title} (ID: {credential_id})", extra={"extra_fields": extra_fields})


def log_system_event(logger: logging.Logger, event: str, details: str, level: str = "INFO"):
    """Log system events"""
    extra_fields = {
        "event_type": "system",
        "system_event": event
    }
    
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.log(numeric_level, f"System Event: {event} - {details}", extra={"extra_fields": extra_fields})


# Create default logger
default_logger = setup_logger()


def log_startup():
    """Log application startup information"""
    default_logger.info("Secret Vault application starting up")
    default_logger.info(f"Environment: {settings.environment}")
    default_logger.info(f"Debug mode: {settings.debug}")
    default_logger.info(f"Database: {settings.database_url}")
    default_logger.info(f"Email notifications: {settings.email_notifications}")
    default_logger.info(f"Backup enabled: {settings.backup_enabled}")


def log_shutdown():
    """Log application shutdown information"""
    default_logger.info("Secret Vault application shutting down")


if __name__ == "__main__":
    # Test the logging system
    logger = get_logger("test")
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test structured logging
    log_security_event(logger, "login_attempt", "admin", "Successful login", "192.168.1.1")
    log_api_request(logger, "GET", "/credentials", "admin", 200, 0.125, "192.168.1.1")
    log_database_operation(logger, "SELECT", "credentials", "admin", "Retrieved 5 credentials")
    log_credential_operation(logger, "CREATE", 1, "admin", "GitHub Account")
    
    print("Logging system test completed. Check the log files.")
