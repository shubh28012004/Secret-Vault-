import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional
import logging
from config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.smtp_use_tls = settings.smtp_use_tls
        self.from_email = settings.from_email
        self.from_name = settings.from_name
    
    def send_email(self, to_email: str, subject: str, text_body: str, html_body: str = None) -> bool:
        """Send email via SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add text part
            text_part = MIMEText(text_body, 'plain')
            msg.attach(text_part)
            
            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_otp_email(self, to_email: str, otp: str, user_name: str = "User") -> bool:
        """Send OTP verification email"""
        subject = "Verify Your Email - Secret Vault"
        
        text_body = f"""
Dear {user_name},

Welcome to Secret Vault! To complete your registration, please verify your email address.

Your verification code is: {otp}

This code will expire in {settings.otp_expiry_minutes} minutes.

If you didn't request this verification, please ignore this email.

Best regards,
Secret Vault Team
        """
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .otp-code {{ font-family: monospace; font-size: 32px; font-weight: bold; color: #1e3c72; background: white; padding: 15px; border-radius: 8px; border: 2px dashed #1e3c72; text-align: center; margin: 20px 0; letter-spacing: 0.3em; }}
        .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Secret Vault</h1>
            <p>Email Verification Required</p>
        </div>
        <div class="content">
            <h2>Welcome, {user_name}!</h2>
            <p>Thank you for registering with Secret Vault. To complete your registration, please verify your email address using the code below:</p>
            
            <div class="otp-code">{otp}</div>
            
            <div class="warning">
                <strong>⏰ Important:</strong> This verification code will expire in {settings.otp_expiry_minutes} minutes.
            </div>
            
            <p>If you didn't request this verification, please ignore this email.</p>
            
            <p>Best regards,<br>The Secret Vault Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return self.send_email(to_email, subject, text_body, html_body)
    
    def send_approval_notification(self, to_email: str, user_name: str = "User") -> bool:
        """Send account approval pending notification"""
        subject = "Registration Under Review - Secret Vault"
        
        text_body = f"""
Dear {user_name},

Thank you for verifying your email address!

Your registration request has been submitted and is currently under review by our administrators. You will receive another email notification once your account has been approved and you can start using Secret Vault.

This process typically takes 1-2 business days.

Best regards,
Secret Vault Team
        """
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(90deg, #28a745 0%, #20c997 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .success {{ background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .pending {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Email Verified!</h1>
            <p>Registration Under Review</p>
        </div>
        <div class="content">
            <h2>Thank you, {user_name}!</h2>
            
            <div class="success">
                <strong>✅ Email Verification Complete</strong><br>
                Your email address has been successfully verified.
            </div>
            
            <div class="pending">
                <strong>⏳ Pending Admin Approval</strong><br>
                Your registration is now under review by our administrators.
            </div>
            
            <p><strong>What happens next?</strong></p>
            <ul>
                <li>Our administrators will review your registration request</li>
                <li>You'll receive an email notification once approved (typically 1-2 business days)</li>
                <li>Once approved, you can login and start using Secret Vault</li>
            </ul>
            
            <p>Thank you for your patience!</p>
            
            <p>Best regards,<br>The Secret Vault Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return self.send_email(to_email, subject, text_body, html_body)

# Initialize email service
email_service = EmailService()

def generate_otp(length: int = 6) -> str:
    """Generate a random OTP"""
    return ''.join(random.choices(string.digits, k=length))
