"""
Email manager with attachment support
Sends emails via Gmail SMTP
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path


class EmailManager:
    """Manages email sending with attachment support."""
    
    def __init__(self, gmail_user=None, gmail_password=None):
        """Initialize email manager."""
        self.gmail_user = gmail_user or os.getenv('GMAIL_USER')
        self.gmail_password = gmail_password or os.getenv('GMAIL_APP_PASSWORD')
        self.enabled = bool(self.gmail_user and self.gmail_password)
    
    def send_generation_email(self, to_email, student_name, module_name, 
                             module_code, practical_number, day_name, 
                             lab_time, sheet_type, generate_token, skip_token, 
                             base_url):
        """Send generation notification email."""
        
        subject = f"🎯 {sheet_type} {practical_number:02d} Ready - {module_name}"
        
        html = self._get_generation_email_html(
            student_name, module_name, module_code, practical_number,
            day_name, lab_time, sheet_type, generate_token, skip_token, base_url
        )
        
        return self.send_email(to_email, subject, html)
    
    def send_confirmation_email(self, to_email, student_name, module_name,
                               practical_number, sheet_type, onedrive_link=None,
                               attachment_path=None):
        """Send confirmation email with optional attachment."""
        
        subject = f"✅ {sheet_type} {practical_number:02d} Generated - {module_name}"
        
        html = self._get_confirmation_email_html(
            student_name, module_name, practical_number, 
            sheet_type, onedrive_link
        )
        
        return self.send_email(to_email, subject, html, attachment_path)
    
    def send_email(self, to_email, subject, html_body, attachment_path=None):
        """
        Send email via Gmail SMTP.
        
        Args:
            to_email: Recipient email
            subject: Email subject
            html_body: HTML email body
            attachment_path: Optional file to attach
            
        Returns:
            bool: True if successful
        """
        if not self.enabled:
            print("Email not configured")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.gmail_user
            msg['To'] = to_email
            
            # Attach HTML body
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Attach file if provided
            if attachment_path and os.path.exists(attachment_path):
                self._attach_file(msg, attachment_path)
            
            # Send email
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(self.gmail_user, self.gmail_password)
                server.send_message(msg)
            
            print(f"Email sent to {to_email}")
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def _attach_file(self, msg, file_path):
        """Attach file to email message."""
        try:
            filename = os.path.basename(file_path)
            
            # Read file
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Create attachment
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(file_data)
            encoders.encode_base64(part)
            
            # Add header
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            
            msg.attach(part)
            
        except Exception as e:
            print(f"Error attaching file: {e}")
    
    def _get_generation_email_html(self, student_name, module_name, module_code,
                                   practical_number, day_name, lab_time, sheet_type,
                                   generate_token, skip_token, base_url):
        """Generate HTML for generation notification email."""
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lab Sheet Ready</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f6f8fa;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 28px; font-weight: 700;">🎯 Lab Sheet Ready</h1>
            <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Time to generate your lab sheet!</p>
        </div>
        
        <!-- Content -->
        <div style="background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <p style="font-size: 16px; color: #24292e; margin-top: 0;">Hi <strong>{student_name}</strong>,</p>
            
            <p style="font-size: 15px; color: #586069; line-height: 1.6;">
                Your lab sheet is ready to generate!
            </p>
            
            <!-- Schedule Details -->
            <div style="background: #f6f8fa; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0; border-radius: 6px;">
                <p style="margin: 0 0 10px 0; font-size: 14px; color: #586069;"><strong>📚 Module:</strong> {module_name} ({module_code})</p>
                <p style="margin: 0 0 10px 0; font-size: 14px; color: #586069;"><strong>📄 {sheet_type}:</strong> #{practical_number:02d}</p>
                <p style="margin: 0 0 10px 0; font-size: 14px; color: #586069;"><strong>🕐 Lab Time:</strong> {day_name} at {lab_time}</p>
            </div>
            
            <!-- Action Buttons -->
            <div style="margin: 30px 0;">
                <p style="font-size: 15px; color: #24292e; margin-bottom: 15px; font-weight: 600;">Choose an action:</p>
                
                <!-- Generate Button -->
                <a href="{base_url}/api/generate/{generate_token}" 
                   style="display: block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 16px 24px; border-radius: 8px; text-align: center; font-weight: 600; font-size: 16px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.3);">
                    ⚡ Generate Now
                </a>
                
                <!-- Skip Button -->
                <a href="{base_url}/api/skip/{skip_token}" 
                   style="display: block; background: #6a737d; color: white; text-decoration: none; padding: 14px 24px; border-radius: 8px; text-align: center; font-weight: 600; font-size: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    ⏭️ Skip This Week
                </a>
            </div>
            
            <!-- Info Box -->
            <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px; padding: 15px; margin-top: 20px;">
                <p style="margin: 0; font-size: 14px; color: #856404; line-height: 1.5;">
                    <strong>💡 What happens after clicking "Generate Now":</strong><br>
                    ✓ Lab sheet will be created automatically<br>
                    ✓ Emailed to you as attachment<br>
                    ✓ Uploaded to OneDrive (with link)<br>
                    ✓ Next practical will be #{practical_number + 1:02d}
                </p>
            </div>
            
            <!-- Skip Info -->
            <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #e1e4e8;">
                <p style="font-size: 13px; color: #6a737d; line-height: 1.6; margin: 0;">
                    <strong>Need to skip this week?</strong><br>
                    Click "Skip This Week" - No sheet will be generated, and next week will still be {sheet_type} #{practical_number:02d}.
                </p>
            </div>
        </div>
        
        <!-- Footer -->
        <div style="text-align: center; margin-top: 20px; padding: 20px;">
            <p style="font-size: 12px; color: #6a737d; margin: 0;">
                Powered by <strong>Lab Sheet Generator V3.0</strong><br>
                This is an automated email. Please do not reply.
            </p>
        </div>
    </div>
</body>
</html>
"""
    
    def _get_confirmation_email_html(self, student_name, module_name, 
                                    practical_number, sheet_type, onedrive_link=None):
        """Generate HTML for confirmation email."""
        
        onedrive_section = ""
        if onedrive_link:
            onedrive_section = f"""
            <div style="margin: 20px 0; padding: 20px; background: #e8f4fd; border-radius: 8px; border-left: 4px solid #0078d4;">
                <p style="margin: 0 0 10px 0; font-size: 15px; color: #0078d4; font-weight: 600;">
                    ☁️ OneDrive Backup:
                </p>
                <a href="{onedrive_link}" 
                   style="display: inline-block; background: #0078d4; color: white; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: 600; font-size: 14px;">
                    Open in OneDrive
                </a>
                <p style="margin: 10px 0 0 0; font-size: 13px; color: #586069;">
                    You can also download from OneDrive on your lab computer.
                </p>
            </div>
            """
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sheet Generated</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f6f8fa;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center;">
            <h1 style="margin: 0 0 20px 0; font-size: 32px; color: #28a745;">
                ✅ Sheet Generated!
            </h1>
            
            <p style="font-size: 16px; color: #24292e; line-height: 1.6; margin: 0 0 15px 0;">
                Hi <strong>{student_name}</strong>,
            </p>
            
            <p style="font-size: 16px; color: #24292e; line-height: 1.6; margin: 0 0 15px 0;">
                Your lab sheet <strong>{sheet_type} #{practical_number:02d}</strong> has been generated successfully!
            </p>
            
            <div style="background: #f6f8fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0 0 10px 0; font-size: 14px; color: #586069;">
                    <strong>📚 Module:</strong> {module_name}
                </p>
                <p style="margin: 0; font-size: 14px; color: #586069;">
                    <strong>📄 {sheet_type}:</strong> #{practical_number:02d}
                </p>
            </div>
            
            <!-- Attachment Notice -->
            <div style="background: #d4edda; border: 1px solid #c3e6cb; border-radius: 6px; padding: 15px; margin: 20px 0;">
                <p style="margin: 0; font-size: 14px; color: #155724; line-height: 1.5;">
                    <strong>📎 File Attached</strong><br>
                    Your lab sheet is attached to this email. Download it directly from your phone or computer!
                </p>
            </div>
            
            {onedrive_section}
            
            <p style="font-size: 14px; color: #6a737d; margin: 20px 0 0 0;">
                Next practical will be <strong>#{practical_number + 1:02d}</strong>.
            </p>
        </div>
        
        <div style="text-align: center; margin-top: 20px; padding: 20px;">
            <p style="font-size: 12px; color: #6a737d; margin: 0;">
                Powered by Lab Sheet Generator V3.0
            </p>
        </div>
    </div>
</body>
</html>
"""


# Singleton instance
_email_manager = None

def get_email_manager():
    """Get email manager singleton."""
    global _email_manager
    if _email_manager is None:
        _email_manager = EmailManager()
    return _email_manager
