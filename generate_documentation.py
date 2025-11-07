#!/usr/bin/env python3
"""
Generate comprehensive PDF documentation for Secret Vault
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime
import os

def create_pdf():
    """Create the PDF documentation"""
    
    # Create PDF document
    filename = "Secret_Vault_Documentation.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4,
                            rightMargin=0.75*inch,
                            leftMargin=0.75*inch,
                            topMargin=0.75*inch,
                            bottomMargin=0.75*inch)
    
    # Container for the 'Flowable' objects
    story = []
    
    # Define custom styles
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Subtitle style
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#283593'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    # Section style
    section_style = ParagraphStyle(
        'CustomSection',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#3949ab'),
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    # Subsection style
    subsection_style = ParagraphStyle(
        'CustomSubsection',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.HexColor('#5c6bc0'),
        spaceAfter=8,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )
    
    # Body style with justified text
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=11,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=6
    )
    
    # Code style
    code_style = ParagraphStyle(
        'CustomCode',
        parent=styles['Code'],
        fontSize=9,
        leading=12,
        fontName='Courier',
        textColor=colors.HexColor('#424242'),
        backColor=colors.HexColor('#f5f5f5'),
        leftIndent=12,
        rightIndent=12
    )
    
    # ========================================
    # COVER PAGE
    # ========================================
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("Secret Vault 7.0", title_style))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Secure Credential Management System", styles['Title']))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("Comprehensive Documentation", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
    story.append(PageBreak())
    
    # ========================================
    # TABLE OF CONTENTS
    # ========================================
    story.append(Paragraph("Table of Contents", subtitle_style))
    story.append(Spacer(1, 0.2*inch))
    
    toc_items = [
        "1. Introduction",
        "2. Features Overview",
        "3. System Architecture",
        "4. Installation & Setup",
        "5. HashiCorp Vault Integration",
        "6. Security Features",
        "7. API Documentation",
        "8. User Guide",
        "9. Admin Guide",
        "10. Testing",
        "11. Troubleshooting",
        "12. Project Structure",
        "13. Database Schema",
        "14. Configuration Reference"
    ]
    
    for item in toc_items:
        story.append(Paragraph(item, body_style))
    story.append(PageBreak())
    
    # ========================================
    # 1. INTRODUCTION
    # ========================================
    story.append(Paragraph("1. Introduction", subtitle_style))
    story.append(Spacer(1, 0.1*inch))
    
    intro_text = """
    Secret Vault 7.0 is a secure, multi-user credential management system built with FastAPI, 
    SQLite, and advanced encryption. It provides a robust platform for storing, managing, and 
    protecting sensitive credentials with features like email verification, multi-factor 
    authentication, and HashiCorp Vault integration.
    
    This system is designed for organizations and individuals who need a secure way to manage 
    passwords, API keys, and other sensitive information with proper access controls, audit 
    trails, and encryption at rest.
    """
    story.append(Paragraph(intro_text, body_style))
    story.append(PageBreak())
    
    # ========================================
    # 2. FEATURES OVERVIEW
    # ========================================
    story.append(Paragraph("2. Features Overview", subtitle_style))
    story.append(Spacer(1, 0.1*inch))
    
    features = [
        "Secure Password Storage: AES-256 encryption with Fernet",
        "Multi-User Support: Isolated credential storage per user",
        "Email Verification: Secure account activation via email",
        "Google OAuth Integration: Quick login with Google accounts",
        "HashiCorp Vault Integration: Centralized encryption key management",
        "Audit Logging: Complete audit trail of all actions",
        "Rate Limiting: Protection against brute force attacks",
        "Input Validation: SQL injection and XSS protection",
        "Automatic Backups: Scheduled database backups",
        "Email Notifications: Credential expiry warnings",
        "Admin Dashboard: User management and system monitoring",
        "RESTful API: Complete CRUD operations"
    ]
    
    story.append(Paragraph("Core Features:", section_style))
    for feature in features:
        story.append(Paragraph(f"• {feature}", body_style))
    story.append(PageBreak())
    
    # ========================================
    # 3. SYSTEM ARCHITECTURE
    # ========================================
    story.append(Paragraph("3. System Architecture", subtitle_style))
    story.append(Spacer(1, 0.1*inch))
    
    arch_text = """
    Secret Vault follows a three-tier architecture:
    
    <b>Frontend Layer:</b> HTML5/CSS3/JavaScript static files served directly by FastAPI.
    
    <b>Backend Layer:</b> FastAPI REST API with endpoint-based routing and middleware.
    
    <b>Data Layer:</b> SQLite database with encryption at rest, optional HashiCorp Vault integration.
    
    <b>Security Layer:</b> JWT authentication, bcrypt password hashing, Fernet encryption for credentials.
    """
    story.append(Paragraph(arch_text, body_style))
    story.append(PageBreak())
    
    # ========================================
    # 4. INSTALLATION & SETUP
    # ========================================
    story.append(Paragraph("4. Installation & Setup", subtitle_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("4.1 Prerequisites", section_style))
    prereq_text = """
    • Python 3.11 or higher
    • pip (Python package installer)
    • HashiCorp Vault (optional, for key management)
    • SMTP server credentials (optional, for email notifications)
    """
    story.append(Paragraph(prereq_text, body_style))
    
    story.append(Paragraph("4.2 Installation Steps", section_style))
    
    steps = [
        ("Step 1: Create Virtual Environment", "python3.11 -m venv venv"),
        ("Step 2: Activate Virtual Environment", "source venv/bin/activate  # macOS/Linux"),
        ("Step 3: Install Dependencies", "pip install -r requirements.txt"),
        ("Step 4: Configure Environment", "Copy .env.example to .env and edit"),
        ("Step 5: Run Database Migrations", "Database created automatically on first run"),
        ("Step 6: Start Server", "uvicorn main:app --host 0.0.0.0 --port 8000")
    ]
    
    for title, cmd in steps:
        story.append(Paragraph(f"<b>{title}</b>", subsection_style))
        story.append(Paragraph(cmd, code_style))
        story.append(Spacer(1, 0.1*inch))
    
    story.append(PageBreak())
    
    # ========================================
    # 5. HASHICORP VAULT INTEGRATION
    # ========================================
    story.append(Paragraph("5. HashiCorp Vault Integration", subtitle_style))
    story.append(Spacer(1, 0.1*inch))
    
    vault_text = """
    HashiCorp Vault provides centralized, secure storage for the master Fernet encryption key.
    This separation of concerns ensures that even if the database is compromised, credentials 
    remain unreadable without access to Vault.
    
    <b>Key Benefits:</b>
    • Centralized key management
    • Access control and audit trails
    • Easy key rotation
    • Separation of secrets from data
    
    <b>Setup Process:</b>
    """
    story.append(Paragraph(vault_text, body_style))
    
    vault_steps = [
        "1. Install Vault: brew tap hashicorp/tap && brew install hashicorp/tap/vault",
        "2. Start Vault: vault server -dev -dev-root-token-id=root",
        "3. Enable KV v2: vault secrets enable -path=secret kv-v2",
        "4. Configure .env: Set VAULT_ENABLED=true",
        "5. Restart application"
    ]
    
    for step in vault_steps:
        story.append(Paragraph(step, body_style))
    
    story.append(PageBreak())
    
    # ========================================
    # 6. SECURITY FEATURES
    # ========================================
    story.append(Paragraph("6. Security Features", subtitle_style))
    story.append(Spacer(1, 0.1*inch))
    
    security_features = {
        "Password Encryption": "bcrypt hashing for user passwords, Fernet encryption for credentials",
        "Input Validation": "SQL injection and XSS protection with comprehensive validation",
        "Rate Limiting": "20 requests per 5 minutes per IP, prevents brute force attacks",
        "Brute Force Protection": "5 failed attempts trigger 15-minute lockout",
        "JWT Authentication": "30-minute expiry with secure token generation",
        "Email Verification": "Required for account activation",
        "Audit Logging": "Complete trail of all user actions",
        "HTTPS Ready": "TLS/SSL encryption support for production"
    }
    
    for feature, description in security_features.items():
        story.append(Paragraph(f"<b>{feature}:</b>", subsection_style))
        story.append(Paragraph(description, body_style))
        story.append(Spacer(1, 0.05*inch))
    
    story.append(PageBreak())
    
    # ========================================
    # 7. API DOCUMENTATION
    # ========================================
    story.append(Paragraph("7. API Documentation", subtitle_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("7.1 Authentication Endpoints", section_style))
    
    auth_endpoints = [
        ("POST /auth/login", "Login with email/password"),
        ("POST /auth/signup", "Register new user"),
        ("POST /auth/google", "Login/Register with Google"),
        ("POST /auth/logout", "Logout and revoke token"),
        ("POST /auth/resend-verification", "Resend verification email"),
        ("GET /auth/verify-email?token={token}", "Verify email address")
    ]
    
    for endpoint, desc in auth_endpoints:
        story.append(Paragraph(f"<b>{endpoint}</b> - {desc}", body_style))
    
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("7.2 Credential Endpoints", section_style))
    
    cred_endpoints = [
        ("GET /credentials", "List all credentials (owner only)"),
        ("POST /credentials", "Create new credential"),
        ("GET /credentials/{id}", "Get specific credential"),
        ("PUT /credentials/{id}", "Update credential"),
        ("DELETE /credentials/{id}", "Delete credential")
    ]
    
    for endpoint, desc in cred_endpoints:
        story.append(Paragraph(f"<b>{endpoint}</b> - {desc}", body_style))
    
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("7.3 System Endpoints", section_style))
    
    system_endpoints = [
        ("GET /system/health", "Health check (encryption status, Vault status)"),
        ("GET /system/info", "System information (admin only)"),
        ("GET /audit", "View audit logs (admin only)")
    ]
    
    for endpoint, desc in system_endpoints:
        story.append(Paragraph(f"<b>{endpoint}</b> - {desc}", body_style))
    
    story.append(PageBreak())
    
    # ========================================
    # 8. USER GUIDE
    # ========================================
    story.append(Paragraph("8. User Guide", subtitle_style))
    story.append(Spacer(1, 0.1*inch))
    
    user_steps = [
        ("Step 1: Sign Up", "Create account at /app/ with email, username, and password"),
        ("Step 2: Verify Email", "Click verification link sent to your email"),
        ("Step 3: Login", "Access dashboard at /app/ after verification"),
        ("Step 4: Add Credentials", "Click 'Add Credential' and fill in details"),
        ("Step 5: Manage Credentials", "View, edit, or delete credentials as needed"),
        ("Step 6: Use Search/Filter", "Find credentials by title, category, or username"),
        ("Step 7: Logout", "Click logout to revoke session token")
    ]
    
    for step, description in user_steps:
        story.append(Paragraph(f"<b>{step}</b>", subsection_style))
        story.append(Paragraph(description, body_style))
        story.append(Spacer(1, 0.05*inch))
    
    story.append(PageBreak())
    
    # ========================================
    # 9. ADMIN GUIDE
    # ========================================
    story.append(Paragraph("9. Admin Guide", subtitle_style))
    story.append(Spacer(1, 0.1*inch))
    
    admin_text = """
    Admin users have elevated privileges and can access additional features. A user is 
    considered admin if the <b>is_admin</b> flag is set to True in the database.
    
    <b>Admin Capabilities:</b>
    • View all system information via /system/info endpoint
    • Access all audit logs
    • Monitor system health and Vault status
    • Manage user accounts (activate/deactivate, promote to admin)
    """
    story.append(Paragraph(admin_text, body_style))
    
    story.append(Paragraph("Setting Up Admin Account:", section_style))
    story.append(Paragraph("Run: python setup_admin.py", code_style))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Or manually set is_admin=1 in the users table", body_style))
    story.append(PageBreak())
    
    # ========================================
    # 10. TESTING
    # ========================================
    story.append(Paragraph("10. Testing", subtitle_style))
    story.append(Spacer(1, 0.1*inch))
    
    test_text = """
    The project includes comprehensive test suites for various aspects of the system.
    """
    story.append(Paragraph(test_text, body_style))
    
    test_files = [
        "test_security_features.py - Security feature testing",
        "test_google_oauth.py - OAuth integration testing",
        "test_crud_operations.py - Database operation testing",
        "test_auth.py - Authentication flow testing",
        "quick_test.py - Quick backend connectivity test"
    ]
    
    story.append(Paragraph("Available Test Files:", section_style))
    for test_file in test_files:
        story.append(Paragraph(f"• {test_file}", body_style))
    
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Running Tests:", section_style))
    story.append(Paragraph("pytest test_security_features.py", code_style))
    story.append(PageBreak())
    
    # ========================================
    # 11. TROUBLESHOOTING
    # ========================================
    story.append(Paragraph("11. Troubleshooting", subtitle_style))
    story.append(Spacer(1, 0.1*inch))
    
    issues = {
        "Port Already in Use": "lsof -i :8000 to find process, kill -9 <PID> to terminate",
        "Database Errors": "Remove secret_vault.db and restart (creates new DB)",
        "Encryption Key Issues": "Remove encryption_key.key to regenerate",
        "Python 3.13 Build Failures": "Use Python 3.11 (recommended)",
        "Vault Connection Issues": "Check VAULT_ADDR and VAULT_TOKEN in .env",
        "Email Not Sending": "Verify SMTP credentials and check logs"
    }
    
    for issue, solution in issues.items():
        story.append(Paragraph(f"<b>{issue}:</b>", subsection_style))
        story.append(Paragraph(solution, code_style))
        story.append(Spacer(1, 0.05*inch))
    
    story.append(PageBreak())
    
    # ========================================
    # 12. PROJECT STRUCTURE
    # ========================================
    story.append(Paragraph("12. Project Structure", subtitle_style))
    story.append(Spacer(1, 0.1*inch))
    
    structure_text = """
    <b>Core Files:</b>
    • main.py - FastAPI application and routing
    • models.py - Database models and Pydantic schemas
    • crud.py - Database operations
    • auth.py - Authentication and authorization
    • security.py - Security features and validation
    • encryption.py - Fernet encryption utilities
    • vault_client.py - HashiCorp Vault integration
    • config.py - Configuration management
    
    <b>Supporting Files:</b>
    • database.py - Database connection
    • logger.py - Logging configuration
    • notifications.py - Email notifications
    • backup.py - Database backup system
    
    <b>Frontend:</b>
    • frontend/ - Static HTML/CSS/JS files
    
    <b>Configuration:</b>
    • .env - Environment variables
    • requirements.txt - Python dependencies
    """
    story.append(Paragraph(structure_text, body_style))
    story.append(PageBreak())
    
    # ========================================
    # 13. DATABASE SCHEMA
    # ========================================
    story.append(Paragraph("13. Database Schema", subtitle_style))
    story.append(Spacer(1, 0.1*inch))
    
    schema_text = """
    <b>Users Table:</b> User accounts with authentication and verification
    <b>Credentials Table:</b> Encrypted credentials with user isolation
    <b>Audit Logs Table:</b> Complete action history for auditing
    
    All sensitive data (passwords, verification tokens) are hashed or encrypted.
    Credentials are stored with encrypted passwords using Fernet encryption.
    """
    story.append(Paragraph(schema_text, body_style))
    story.append(PageBreak())
    
    # ========================================
    # 14. CONFIGURATION REFERENCE
    # ========================================
    story.append(Paragraph("14. Configuration Reference", subtitle_style))
    story.append(Spacer(1, 0.1*inch))
    
    config_items = [
        ("SECRET_KEY", "JWT signing key"),
        ("DATABASE_URL", "SQLite database path"),
        ("VAULT_ENABLED", "Enable HashiCorp Vault"),
        ("VAULT_ADDR", "Vault server address"),
        ("VAULT_TOKEN", "Vault authentication token"),
        ("SMTP_SERVER", "Email server address"),
        ("SMTP_USERNAME", "Email username"),
        ("SMTP_PASSWORD", "Email password"),
        ("FROM_EMAIL", "Sender email address")
    ]
    
    story.append(Paragraph("Environment Variables:", section_style))
    for var, desc in config_items:
        story.append(Paragraph(f"<b>{var}</b> - {desc}", body_style))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("--- End of Documentation ---", styles['Normal']))
    
    # Build PDF
    doc.build(story)
    print(f"PDF documentation created: {filename}")

if __name__ == "__main__":
    create_pdf()

