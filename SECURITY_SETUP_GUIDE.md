# 🔒 Secret Vault Security Setup & Testing Guide

This guide covers the comprehensive security features implemented in Secret Vault and how to test them.

## 🚀 Quick Start

### 1. Create Dummy Users for Testing
```bash
python create_dummy_user.py
```

This creates three test users:
- **Admin User**: `testadmin@example.com` / `TestAdmin123!`
- **Regular User**: `testuser@example.com` / `TestUser123!`
- **Demo User**: `demo@example.com` / `DemoPass123!`

### 2. Start the Application
```bash
# Terminal 1: Start Backend API
python main.py

# Terminal 2: Start Frontend Dashboard
streamlit run app1.py
```

### 3. Test Security Features
```bash
# Run comprehensive security tests
python test_security_features.py

# Test Google OAuth integration
python test_google_oauth.py
```

## 🔐 Security Features Implemented

### 1. **Enhanced Input Validation**

#### Email Validation
- ✅ Proper email format validation
- ✅ Length limits (max 255 characters)
- ✅ Suspicious pattern detection
- ✅ Domain validation

#### Password Security
- ✅ Minimum 8 characters
- ✅ Uppercase, lowercase, numbers required
- ✅ Special character recommendations
- ✅ Common password detection
- ✅ Entropy scoring (1-7 scale)
- ✅ Real-time strength feedback

#### Username Validation
- ✅ Length limits (3-20 characters)
- ✅ Alphanumeric and underscore only
- ✅ Reserved username protection
- ✅ Case-insensitive uniqueness

#### Full Name Validation
- ✅ Length limits (2-100 characters)
- ✅ Letters, spaces, hyphens, apostrophes only
- ✅ Trim whitespace

#### URL Validation
- ✅ Proper URL format validation
- ✅ Protocol validation (http/https)
- ✅ Optional field handling

### 2. **Rate Limiting & Brute Force Protection**

#### Rate Limiting
- ✅ 20 requests per 5 minutes per IP
- ✅ Endpoint-specific rate limiting
- ✅ Automatic IP blocking for violations

#### Brute Force Protection
- ✅ 5 failed attempts per IP/user
- ✅ 15-minute lockout period
- ✅ Progressive delays
- ✅ Account lockout after max attempts

#### Security Monitoring
- ✅ Failed login attempt tracking
- ✅ Suspicious activity detection
- ✅ IP-based threat detection

### 3. **Enhanced Security Logging**

#### Comprehensive Audit Trail
- ✅ All authentication events logged
- ✅ Input validation failures logged
- ✅ Security violations tracked
- ✅ IP address and user agent logging
- ✅ Timestamp and severity levels

#### Security Event Types
- `FAILED_LOGIN` - Invalid credentials
- `SUCCESSFUL_LOGIN` - Valid authentication
- `SUSPICIOUS_ACTIVITY` - Potential threats
- `RATE_LIMIT_EXCEEDED` - Rate limiting violations
- `BRUTE_FORCE_ATTEMPT` - Multiple failed attempts
- `INPUT_VALIDATION_ERROR` - Invalid input detected

### 4. **SQL Injection Protection**

#### Input Sanitization
- ✅ SQL pattern detection
- ✅ Special character filtering
- ✅ Parameterized queries
- ✅ Input length limits

#### Common Attack Patterns Blocked
- `UNION SELECT` attacks
- `DROP TABLE` attempts
- `OR 1=1` bypasses
- Comment-based injections (`--`, `#`)

### 5. **XSS Protection**

#### Input Sanitization
- ✅ Script tag removal
- ✅ JavaScript protocol blocking
- ✅ HTML entity encoding
- ✅ Malicious payload detection

### 6. **Authentication Security**

#### JWT Token Security
- ✅ 30-minute expiration
- ✅ Secure token generation
- ✅ Token blacklisting on logout
- ✅ Refresh token rotation

#### Session Management
- ✅ Secure session storage
- ✅ Session timeout handling
- ✅ Cross-session protection

### 7. **Google OAuth Security**

#### OAuth Validation
- ✅ State token verification
- ✅ Google token validation
- ✅ User data sanitization
- ✅ Automatic account creation
- ✅ Email verification bypass for Google users

## 🧪 Testing the Security Features

### 1. **Input Validation Testing**

#### Test Invalid Emails
```bash
# These should all be rejected:
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "invalid-email", "password": "TestPass123!"}'
```

#### Test Weak Passwords
```bash
# These should all be rejected:
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "username": "testuser", "full_name": "Test User", "password": "123456"}'
```

### 2. **Rate Limiting Testing**

#### Test Rapid Requests
```bash
# Run this multiple times quickly - should get rate limited:
for i in {1..10}; do
  curl -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "test@example.com", "password": "wrongpassword"}' &
done
```

### 3. **SQL Injection Testing**

#### Test SQL Injection Attempts
```bash
# These should all be safely handled:
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin'\''; DROP TABLE users; --", "password": "test"}'
```

### 4. **XSS Testing**

#### Test XSS Payloads
```bash
# These should be sanitized:
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "username": "<script>alert('\''xss'\'')</script>", "full_name": "Test User", "password": "TestPass123!"}'
```

## 📊 Security Monitoring

### 1. **Log Files**
- `secret_vault.log` - Application logs with security events
- Security events are marked with `SECURITY_` prefix

### 2. **Audit Database**
- All security events stored in `audit_logs` table
- Query for security events:
```sql
SELECT * FROM audit_logs WHERE action LIKE '%LOGIN%' OR action LIKE '%SECURITY%';
```

### 3. **Real-time Monitoring**
- Failed login attempts tracked per IP
- Suspicious activity alerts
- Rate limiting violations logged

## 🔧 Configuration

### Security Settings (config.py)
```python
# Rate limiting
MAX_LOGIN_ATTEMPTS = 5
RATE_LIMIT_WINDOW = 300  # 5 minutes
RATE_LIMIT_MAX_REQUESTS = 20

# Session security
SESSION_TIMEOUT = 3600  # 1 hour
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password requirements
MIN_PASSWORD_LENGTH = 8
REQUIRE_SPECIAL_CHARS = False  # Recommended only
```

### Environment Variables
```bash
# Security settings
DEBUG=false
LOG_LEVEL=INFO
MAX_LOGIN_ATTEMPTS=5
RATE_LIMIT_WINDOW=300
```

## 🚨 Security Best Practices

### 1. **Production Deployment**
- ✅ Change default admin credentials
- ✅ Use strong SECRET_KEY
- ✅ Enable HTTPS
- ✅ Configure proper CORS origins
- ✅ Set up proper logging rotation
- ✅ Use environment variables for secrets

### 2. **Monitoring**
- ✅ Monitor failed login attempts
- ✅ Watch for unusual access patterns
- ✅ Regular security log reviews
- ✅ Automated alerts for critical events

### 3. **Maintenance**
- ✅ Regular password updates
- ✅ Security patch updates
- ✅ Backup and recovery testing
- ✅ Security audit reviews

## 🎯 Test Scenarios

### 1. **Normal User Flow**
1. Register with valid credentials
2. Verify email (if email service configured)
3. Login with valid credentials
4. Access dashboard
5. Create/manage credentials
6. Logout

### 2. **Security Violation Scenarios**
1. Attempt login with invalid credentials (5 times)
2. Try SQL injection in login form
3. Submit XSS payload in registration
4. Make rapid API requests
5. Use weak passwords

### 3. **Admin Functions**
1. Login as admin user
2. View user management
3. Check audit logs
4. Manage system settings
5. Create backups

## 📈 Performance Testing

### Load Testing
```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test concurrent logins
ab -n 100 -c 10 -T application/json -p login_data.json http://localhost:8000/auth/login
```

### Stress Testing
```bash
# Test rate limiting under load
for i in {1..50}; do
  curl -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "test@example.com", "password": "wrong"}' &
done
```

## 🔍 Troubleshooting

### Common Issues

1. **Rate Limiting Too Aggressive**
   - Adjust `RATE_LIMIT_MAX_REQUESTS` in config
   - Check IP blocking status

2. **Password Validation Too Strict**
   - Modify `validate_password` function
   - Adjust minimum requirements

3. **Security Logs Too Verbose**
   - Change `LOG_LEVEL` to `WARNING`
   - Filter security events

4. **Google OAuth Issues**
   - Verify client credentials
   - Check redirect URIs
   - Ensure HTTPS in production

## 📞 Support

For security issues or questions:
1. Check the logs in `secret_vault.log`
2. Run security tests: `python test_security_features.py`
3. Review audit logs in database
4. Check configuration in `config.py`

---

**Remember**: Security is an ongoing process. Regularly review logs, update dependencies, and test security features to maintain a secure environment.
