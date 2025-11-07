"""
Enhanced security module for Secret Vault
Includes input validation, rate limiting, and comprehensive logging
"""

import re
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import logging
from functools import wraps
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session
from models import User, AuditLog
from crud import create_audit_log

# Configure logging
logger = logging.getLogger("security")

# Rate limiting storage (in production, use Redis)
RATE_LIMIT_STORAGE = defaultdict(list)
BLOCKED_IPS = set()
SUSPICIOUS_ACTIVITY = defaultdict(list)

# Security configuration
MAX_LOGIN_ATTEMPTS = 5
RATE_LIMIT_WINDOW = 300  # 5 minutes
RATE_LIMIT_MAX_REQUESTS = 20
BRUTE_FORCE_WINDOW = 900  # 15 minutes
BLOCK_DURATION = 3600  # 1 hour

class SecurityError(Exception):
    """Custom security exception"""
    pass

class InputValidator:
    """Comprehensive input validation"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format and domain"""
        if not email or len(email) > 255:
            return False
        
        # Basic email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'\.{2,}',  # Multiple consecutive dots
            r'@.*@',    # Multiple @ symbols
            r'\.{2,}@', # Dots before @
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, email):
                return False
        
        return True
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """Comprehensive password validation"""
        result = {
            "valid": True,
            "score": 0,
            "issues": [],
            "strengths": [],
            "recommendations": []
        }
        
        if not password:
            result["valid"] = False
            result["issues"].append("Password is required")
            return result
        
        # Length validation
        if len(password) < 8:
            result["valid"] = False
            result["issues"].append("Password must be at least 8 characters long")
        elif len(password) >= 12:
            result["score"] += 2
            result["strengths"].append("Good length (12+ characters)")
        else:
            result["score"] += 1
            result["strengths"].append("Adequate length")
        
        # Character type validation
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        if not has_upper:
            result["valid"] = False
            result["issues"].append("Password must contain uppercase letters")
        else:
            result["score"] += 1
            result["strengths"].append("Contains uppercase letters")
        
        if not has_lower:
            result["valid"] = False
            result["issues"].append("Password must contain lowercase letters")
        else:
            result["score"] += 1
            result["strengths"].append("Contains lowercase letters")
        
        if not has_digit:
            result["valid"] = False
            result["issues"].append("Password must contain numbers")
        else:
            result["score"] += 1
            result["strengths"].append("Contains numbers")
        
        if has_special:
            result["score"] += 1
            result["strengths"].append("Contains special characters")
        else:
            result["recommendations"].append("Consider adding special characters")
        
        # Common password check
        common_passwords = [
            "password", "123456", "qwerty", "admin", "letmein",
            "password123", "admin123", "12345678", "qwerty123"
        ]
        
        if password.lower() in common_passwords:
            result["valid"] = False
            result["issues"].append("Password is too common")
        elif result["score"] < 3:
            result["recommendations"].append("Consider using a stronger password")
        
        # Entropy check
        unique_chars = len(set(password))
        if unique_chars >= len(password) * 0.7:
            result["score"] += 1
            result["strengths"].append("Good character variety")
        else:
            result["recommendations"].append("Use more varied characters")
        
        return result
    
    @staticmethod
    def validate_username(username: str) -> Dict[str, Any]:
        """Validate username"""
        result = {"valid": True, "issues": []}
        
        if not username:
            result["valid"] = False
            result["issues"].append("Username is required")
            return result
        
        if len(username) < 3:
            result["valid"] = False
            result["issues"].append("Username must be at least 3 characters")
        
        if len(username) > 20:
            result["valid"] = False
            result["issues"].append("Username must be less than 20 characters")
        
        # Only allow alphanumeric and underscore
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            result["valid"] = False
            result["issues"].append("Username can only contain letters, numbers, and underscores")
        
        # Check for reserved usernames
        reserved_usernames = ["admin", "root", "system", "api", "www", "mail", "ftp"]
        if username.lower() in reserved_usernames:
            result["valid"] = False
            result["issues"].append("Username is reserved")
        
        return result
    
    @staticmethod
    def validate_full_name(name: str) -> Dict[str, Any]:
        """Validate full name"""
        result = {"valid": True, "issues": []}
        
        if not name or not name.strip():
            result["valid"] = False
            result["issues"].append("Full name is required")
            return result
        
        name = name.strip()
        
        if len(name) < 2:
            result["valid"] = False
            result["issues"].append("Full name must be at least 2 characters")
        
        if len(name) > 100:
            result["valid"] = False
            result["issues"].append("Full name must be less than 100 characters")
        
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-']+$", name):
            result["valid"] = False
            result["issues"].append("Full name can only contain letters, spaces, hyphens, and apostrophes")
        
        return result
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format"""
        if not url:
            return True  # URL is optional
        
        url_pattern = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'
        return bool(re.match(url_pattern, url))
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 1000) -> str:
        """Sanitize user input"""
        if not text:
            return ""
        
        # Remove null bytes and control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Limit length
        text = text[:max_length]
        
        # Strip whitespace
        text = text.strip()
        
        return text

class RateLimiter:
    """Rate limiting functionality"""
    
    @staticmethod
    def is_rate_limited(ip: str, endpoint: str = "general") -> bool:
        """Check if IP is rate limited"""
        current_time = time.time()
        key = f"{ip}:{endpoint}"
        
        # Clean old entries
        RATE_LIMIT_STORAGE[key] = [
            timestamp for timestamp in RATE_LIMIT_STORAGE[key]
            if current_time - timestamp < RATE_LIMIT_WINDOW
        ]
        
        # Check if rate limit exceeded
        if len(RATE_LIMIT_STORAGE[key]) >= RATE_LIMIT_MAX_REQUESTS:
            return True
        
        # Add current request
        RATE_LIMIT_STORAGE[key].append(current_time)
        return False
    
    @staticmethod
    def check_brute_force(ip: str, user_email: str = None) -> bool:
        """Check for brute force attempts"""
        current_time = time.time()
        
        # Check IP-based brute force
        ip_key = f"ip:{ip}"
        SUSPICIOUS_ACTIVITY[ip_key] = [
            timestamp for timestamp in SUSPICIOUS_ACTIVITY[ip_key]
            if current_time - timestamp < BRUTE_FORCE_WINDOW
        ]
        
        if len(SUSPICIOUS_ACTIVITY[ip_key]) >= MAX_LOGIN_ATTEMPTS:
            BLOCKED_IPS.add(ip)
            return True
        
        # Check user-based brute force
        if user_email:
            user_key = f"user:{user_email}"
            SUSPICIOUS_ACTIVITY[user_key] = [
                timestamp for timestamp in SUSPICIOUS_ACTIVITY[user_key]
                if current_time - timestamp < BRUTE_FORCE_WINDOW
            ]
            
            if len(SUSPICIOUS_ACTIVITY[user_key]) >= MAX_LOGIN_ATTEMPTS:
                return True
        
        return False
    
    @staticmethod
    def record_failed_attempt(ip: str, user_email: str = None):
        """Record a failed authentication attempt"""
        current_time = time.time()
        
        # Record IP-based attempt
        ip_key = f"ip:{ip}"
        SUSPICIOUS_ACTIVITY[ip_key].append(current_time)
        
        # Record user-based attempt
        if user_email:
            user_key = f"user:{user_email}"
            SUSPICIOUS_ACTIVITY[user_key].append(current_time)
    
    @staticmethod
    def is_ip_blocked(ip: str) -> bool:
        """Check if IP is blocked"""
        return ip in BLOCKED_IPS
    
    @staticmethod
    def unblock_ip(ip: str):
        """Unblock an IP address"""
        BLOCKED_IPS.discard(ip)

class SecurityLogger:
    """Enhanced security logging"""
    
    @staticmethod
    def log_security_event(
        level: str,
        event_type: str,
        user_id: Optional[int],
        email: Optional[str],
        ip_address: str,
        user_agent: Optional[str],
        details: str,
        severity: str = "INFO"
    ):
        """Log security events with comprehensive details"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "event_type": event_type,
            "user_id": user_id,
            "email": email,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details,
            "severity": severity
        }
        
        # Log to application logger
        if severity == "CRITICAL":
            logger.critical(f"SECURITY_CRITICAL: {event_type} - {details}", extra=log_entry)
        elif severity == "ERROR":
            logger.error(f"SECURITY_ERROR: {event_type} - {details}", extra=log_entry)
        elif severity == "WARNING":
            logger.warning(f"SECURITY_WARNING: {event_type} - {details}", extra=log_entry)
        else:
            logger.info(f"SECURITY_INFO: {event_type} - {details}", extra=log_entry)
    
    @staticmethod
    def log_failed_login(email: str, ip_address: str, user_agent: str, reason: str):
        """Log failed login attempts"""
        SecurityLogger.log_security_event(
            level="WARNING",
            event_type="FAILED_LOGIN",
            user_id=None,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            details=f"Failed login attempt for {email}: {reason}",
            severity="WARNING"
        )
    
    @staticmethod
    def log_successful_login(user_id: int, email: str, ip_address: str, user_agent: str):
        """Log successful login"""
        SecurityLogger.log_security_event(
            level="INFO",
            event_type="SUCCESSFUL_LOGIN",
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            details=f"Successful login for {email}",
            severity="INFO"
        )
    
    @staticmethod
    def log_suspicious_activity(
        activity_type: str,
        ip_address: str,
        user_agent: str,
        details: str,
        user_id: Optional[int] = None,
        email: Optional[str] = None
    ):
        """Log suspicious activity"""
        SecurityLogger.log_security_event(
            level="WARNING",
            event_type="SUSPICIOUS_ACTIVITY",
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            details=f"{activity_type}: {details}",
            severity="WARNING"
        )
    
    @staticmethod
    def log_rate_limit_exceeded(ip_address: str, endpoint: str, user_agent: str):
        """Log rate limit exceeded"""
        SecurityLogger.log_security_event(
            level="WARNING",
            event_type="RATE_LIMIT_EXCEEDED",
            user_id=None,
            email=None,
            ip_address=ip_address,
            user_agent=user_agent,
            details=f"Rate limit exceeded for endpoint {endpoint}",
            severity="WARNING"
        )

class SecurityMiddleware:
    """Security middleware for request validation"""
    
    @staticmethod
    def validate_request_security(request: Request) -> Dict[str, Any]:
        """Validate request security"""
        result = {
            "valid": True,
            "warnings": [],
            "blocked": False,
            "reason": None
        }
        
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        
        # Check if IP is blocked
        if RateLimiter.is_ip_blocked(ip_address):
            result["valid"] = False
            result["blocked"] = True
            result["reason"] = "IP address is blocked"
            SecurityLogger.log_suspicious_activity(
                "BLOCKED_IP_ACCESS",
                ip_address,
                user_agent,
                "Attempted access from blocked IP"
            )
            return result
        
        # Check rate limiting
        endpoint = request.url.path
        if RateLimiter.is_rate_limited(ip_address, endpoint):
            result["valid"] = False
            result["blocked"] = True
            result["reason"] = "Rate limit exceeded"
            SecurityLogger.log_rate_limit_exceeded(ip_address, endpoint, user_agent)
            return result
        
        # Check for suspicious headers
        suspicious_headers = ["x-forwarded-for", "x-real-ip", "x-cluster-client-ip"]
        for header in suspicious_headers:
            if header in request.headers:
                result["warnings"].append(f"Suspicious header detected: {header}")
        
        # Check for SQL injection patterns in query parameters
        for param_name, param_value in request.query_params.items():
            if SecurityMiddleware._contains_sql_injection(param_value):
                result["warnings"].append(f"Potential SQL injection in parameter {param_name}")
        
        return result
    
    @staticmethod
    def _contains_sql_injection(value: str) -> bool:
        """Check for SQL injection patterns"""
        sql_patterns = [
            r"(\bunion\b.*\bselect\b)",
            r"(\bselect\b.*\bfrom\b)",
            r"(\binsert\b.*\binto\b)",
            r"(\bupdate\b.*\bset\b)",
            r"(\bdelete\b.*\bfrom\b)",
            r"(\bdrop\b.*\btable\b)",
            r"(--|\#|/\*|\*/)",
            r"(\bor\b.*\b1\s*=\s*1)",
            r"(\band\b.*\b1\s*=\s*1)"
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False

def security_decorator(event_type: str, severity: str = "INFO"):
    """Decorator for security logging"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and user info if available
            request = None
            user = None
            
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                elif hasattr(arg, 'id') and hasattr(arg, 'email'):  # User object
                    user = arg
            
            # Log function execution
            if request:
                ip_address = request.client.host if request.client else "unknown"
                user_agent = request.headers.get("user-agent", "")
                
                SecurityLogger.log_security_event(
                    level=severity,
                    event_type=event_type,
                    user_id=user.id if user else None,
                    email=user.email if user else None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details=f"Function {func.__name__} executed",
                    severity=severity
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Export main classes and functions
__all__ = [
    'InputValidator',
    'RateLimiter', 
    'SecurityLogger',
    'SecurityMiddleware',
    'security_decorator',
    'SecurityError'
]
