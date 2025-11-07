"""
Email notification system for Secret Vault
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
from config import settings
from logger import get_logger, log_email_notification
from crud import get_credentials, get_audit_logs
from database import get_db

logger = get_logger("notifications")

class EmailNotifier:
    """Email notification manager"""
    
    def __init__(self):
        # Support SMTP_SERVER/SMTP_HOST via settings.smtp_server
        self.smtp_host = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.email_from = settings.email_from
        self.email_to = settings.email_to 
        
        # Validate email settings
        if not self.validate_settings():
            logger.warning("Email notifications disabled - incomplete configuration")
    
    def validate_settings(self) -> bool:
        """Validate email configuration"""
        required_fields = [
            self.smtp_host,
            self.smtp_username,
            self.smtp_password,
            self.email_from
        ]
        # Note: email_to is now optional since we'll pass recipients dynamically
        return all(field and field.strip() for field in required_fields)
    
    def send_email(self, subject: str, body: str, html_body: Optional[str] = None, 
                   attachments: Optional[List[Dict[str, Any]]] = None,
                   to_email: Optional[str] = None) -> bool:
        """
        Send an email
        
        Args:
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            attachments: Optional list of attachments
            to_email: Recipient email address (if None, uses self.email_to)
        """
        if not self.validate_settings():
            logger.error("Cannot send email - incomplete configuration")
            return False
        
        # Use provided to_email or fallback to self.email_to
        recipient = to_email or self.email_to
        if not recipient or not recipient.strip():
            logger.error("No recipient email address provided")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_from
            msg['To'] = recipient
            msg['Subject'] = f"Secret Vault - {subject}"
            
            # Add text body
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Add HTML body if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    self._add_attachment(msg, attachment)
            
            # Send email
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            log_email_notification(logger, recipient, subject, True)
            logger.info(f"Email sent successfully to {recipient}: {subject}")
            return True
            
        except Exception as e:
            log_email_notification(logger, recipient, subject, False, str(e))
            logger.error(f"Failed to send email to {recipient} '{subject}': {e}")
            return False
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """Add an attachment to the email"""
        try:
            filename = attachment.get('filename', 'attachment')
            content = attachment.get('content', '')
            content_type = attachment.get('content_type', 'application/octet-stream')
            
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename= {filename}')
            
            msg.attach(part)
            
        except Exception as e:
            logger.error(f"Failed to add attachment {filename}: {e}")
    
    def send_expiry_warning(self, expiring_credentials: List[Dict[str, Any]]) -> bool:
        """Send expiry warning email"""
        if not expiring_credentials:
            return True
        
        subject = f"Credential Expiry Warning - {len(expiring_credentials)} credentials expiring soon"
        
        # Create text body
        text_body = f"""
Secret Vault - Credential Expiry Warning

{len(expiring_credentials)} credential(s) will expire within {settings.expiry_warning_days} days:

"""
        
        for cred in expiring_credentials:
            text_body += f"""
Title: {cred['title']}
Username: {cred['username']}
Category: {cred['category']}
Expires: {cred['expires_at']}
URL: {cred['url'] or 'N/A'}

"""
        
        text_body += f"""
Please review and update these credentials as needed.

This is an automated message from Secret Vault.
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Create HTML body
        html_body = self._create_expiry_html(expiring_credentials)
        
        return self.send_email(subject, text_body, html_body)
    
    def _create_expiry_html(self, expiring_credentials: List[Dict[str, Any]]) -> str:
        """Create HTML version of expiry warning"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; }}
        .credential {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
        .title {{ font-weight: bold; color: #721c24; }}
        .expires {{ color: #856404; font-weight: bold; }}
        .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>⚠️ Credential Expiry Warning</h2>
        <p>{len(expiring_credentials)} credential(s) will expire within {settings.expiry_warning_days} days.</p>
    </div>
"""
        
        for cred in expiring_credentials:
            html += f"""
    <div class="credential">
        <div class="title">{cred['title']}</div>
        <p><strong>Username:</strong> {cred['username']}</p>
        <p><strong>Category:</strong> {cred['category']}</p>
        <p><strong>URL:</strong> {cred['url'] or 'N/A'}</p>
        <p class="expires"><strong>Expires:</strong> {cred['expires_at']}</p>
    </div>
"""
        
        html += f"""
    <div class="footer">
        <p>Please review and update these credentials as needed.</p>
        <p>This is an automated message from Secret Vault.</p>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""
        return html
    
    def send_daily_digest(self) -> bool:
        """Send daily digest email"""
        try:
            # Get database session
            db = next(get_db())
            
            # Get today's statistics
            today = datetime.now().date()
            start_of_day = datetime.combine(today, datetime.min.time())
            end_of_day = datetime.combine(today, datetime.max.time())
            
            # Get credentials count
            all_credentials = get_credentials(db)
            total_credentials = len(all_credentials)
            
            # Get recent audit logs
            audit_logs = get_audit_logs(db)
            today_logs = [
                log for log in audit_logs 
                if start_of_day <= log.created_at <= end_of_day
            ]
            
            # Get expiring credentials
            warning_date = datetime.now() + timedelta(days=settings.expiry_warning_days)
            expiring_soon = [
                cred for cred in all_credentials
                if cred.expires_at and cred.expires_at <= warning_date
            ]
            
            subject = f"Daily Digest - {today.strftime('%Y-%m-%d')}"
            
            # Create text body
            text_body = f"""
Secret Vault - Daily Digest Report
Date: {today.strftime('%Y-%m-%d')}

SUMMARY:
- Total Credentials: {total_credentials}
- Activities Today: {len(today_logs)}
- Credentials Expiring Soon: {len(expiring_soon)}

RECENT ACTIVITIES:
"""
            
            for log in today_logs[:10]:  # Show last 10 activities
                text_body += f"- {log.created_at.strftime('%H:%M')} - {log.user}: {log.action} - {log.details}\n"
            
            if expiring_soon:
                text_body += f"\nEXPIRING CREDENTIALS:\n"
                for cred in expiring_soon:
                    text_body += f"- {cred.title} (expires: {cred.expires_at})\n"
            
            text_body += f"""
This is an automated daily digest from Secret Vault.
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            # Create HTML body
            html_body = self._create_digest_html(today, total_credentials, today_logs, expiring_soon)
            
            return self.send_email(subject, text_body, html_body)
            
        except Exception as e:
            logger.error(f"Failed to create daily digest: {e}")
            return False
    
    def _create_digest_html(self, today: datetime, total_credentials: int, 
                           today_logs: List, expiring_soon: List) -> str:
        """Create HTML version of daily digest"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; border-radius: 5px; }}
        .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .stat-box {{ text-align: center; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .stat-number {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .section {{ margin: 20px 0; }}
        .activity {{ border-left: 3px solid #007bff; padding: 5px 10px; margin: 5px 0; }}
        .expiring {{ color: #856404; }}
        .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>📊 Daily Digest Report</h2>
        <p>Date: {today.strftime('%Y-%m-%d')}</p>
    </div>
    
    <div class="stats">
        <div class="stat-box">
            <div class="stat-number">{total_credentials}</div>
            <div>Total Credentials</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{len(today_logs)}</div>
            <div>Activities Today</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{len(expiring_soon)}</div>
            <div>Expiring Soon</div>
        </div>
    </div>
"""
        
        if today_logs:
            html += """
    <div class="section">
        <h3>Recent Activities</h3>
"""
            for log in today_logs[:10]:
                html += f"""
        <div class="activity">
            <strong>{log.created_at.strftime('%H:%M')}</strong> - {log.user}: {log.action} - {log.details}
        </div>
"""
            html += "</div>"
        
        if expiring_soon:
            html += """
    <div class="section">
        <h3>Expiring Credentials</h3>
"""
            for cred in expiring_soon:
                html += f"""
        <div class="activity expiring">
            <strong>{cred.title}</strong> - expires on {cred.expires_at}
        </div>
"""
            html += "</div>"
        
        html += f"""
    <div class="footer">
        <p>This is an automated daily digest from Secret Vault.</p>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""
        return html
    
    def send_system_alert(self, alert_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """Send system alert email"""
        subject = f"System Alert - {alert_type}"
        
        text_body = f"""
Secret Vault - System Alert

Alert Type: {alert_type}
Message: {message}

"""
        
        if details:
            text_body += "Details:\n"
            for key, value in details.items():
                text_body += f"- {key}: {value}\n"
        
        text_body += f"""

This is an automated system alert from Secret Vault.
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Create HTML body
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .alert {{ background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; }}
        .alert-type {{ color: #721c24; font-weight: bold; }}
        .details {{ margin-top: 15px; }}
        .detail-item {{ margin: 5px 0; }}
        .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="alert">
        <h2>🚨 System Alert</h2>
        <p class="alert-type">Alert Type: {alert_type}</p>
        <p><strong>Message:</strong> {message}</p>
"""
        
        if details:
            html_body += """
        <div class="details">
            <h4>Details:</h4>
"""
            for key, value in details.items():
                html_body += f"""
            <div class="detail-item">
                <strong>{key}:</strong> {value}
            </div>
"""
            html_body += "</div>"
        
        html_body += f"""
    </div>
    <div class="footer">
        <p>This is an automated system alert from Secret Vault.</p>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""
        
        return self.send_email(subject, text_body, html_body)


def check_expiring_credentials() -> List[Dict[str, Any]]:
    """Check for credentials expiring soon"""
    try:
        db = next(get_db())
        all_credentials = get_credentials(db)
        
        warning_date = datetime.now() + timedelta(days=settings.expiry_warning_days)
        expiring_credentials = []
        
        for cred in all_credentials:
            if cred.expires_at and cred.expires_at <= warning_date:
                expiring_credentials.append({
                    'title': cred.title,
                    'username': cred.username,
                    'category': cred.category,
                    'expires_at': cred.expires_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'url': cred.url
                })
        
        return expiring_credentials
        
    except Exception as e:
        logger.error(f"Failed to check expiring credentials: {e}")
        return []


def send_expiry_notifications():
    """Send expiry notifications for credentials expiring soon"""
    if not settings.email_notifications:
        logger.info("Email notifications disabled")
        return False
    
    expiring_credentials = check_expiring_credentials()
    
    if expiring_credentials:
        notifier = EmailNotifier()
        return notifier.send_expiry_warning(expiring_credentials)
    
    return True


def send_daily_digest_notification():
    """Send daily digest notification"""
    if not settings.email_notifications or not settings.daily_digest:
        logger.info("Daily digest notifications disabled")
        return False
    
    notifier = EmailNotifier()
    return notifier.send_daily_digest()


def send_system_alert_notification(alert_type: str, message: str, details: Optional[Dict[str, Any]] = None):
    """Send system alert notification"""
    if not settings.email_notifications:
        logger.info("Email notifications disabled")
        return False
    
    notifier = EmailNotifier()
    return notifier.send_system_alert(alert_type, message, details)


if __name__ == "__main__":
    # Test the notification system
    print("=== Secret Vault Notification System Test ===")
    
    notifier = EmailNotifier()
    
    if not notifier.validate_settings():
        print("✗ Email configuration incomplete")
        print("Please set up SMTP settings in your .env file")
    else:
        print("✓ Email configuration valid")
        
        # Test basic email
        print("\n1. Testing basic email...")
        success = notifier.send_email(
            "Test Email",
            "This is a test email from Secret Vault notification system.",
            "<h1>Test Email</h1><p>This is a test email from Secret Vault notification system.</p>"
        )
        print("✓ Email sent successfully" if success else "✗ Email failed")
        
        # Test expiry warning
        print("\n2. Testing expiry warning...")
        test_credentials = [
            {
                'title': 'Test GitHub Account',
                'username': 'testuser',
                'category': 'Development',
                'expires_at': '2024-01-15 12:00:00',
                'url': 'https://github.com'
            }
        ]
        success = notifier.send_expiry_warning(test_credentials)
        print("✓ Expiry warning sent" if success else "✗ Expiry warning failed")
        
        # Test daily digest
        print("\n3. Testing daily digest...")
        success = notifier.send_daily_digest()
        print("✓ Daily digest sent" if success else "✗ Daily digest failed")
    
    print("\n=== Notification system test completed ===")
