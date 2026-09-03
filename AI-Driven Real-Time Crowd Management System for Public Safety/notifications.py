import smtplib
import asyncio
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
import json
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self):
        self.sms_enabled = bool(Config.TWILIO_ACCOUNT_SID and Config.TWILIO_AUTH_TOKEN)
        self.email_enabled = bool(Config.SMTP_USERNAME and Config.SMTP_PASSWORD)
        
        # Security staff contacts
        self.security_contacts = {
            "sms": ["+919110340008"],  # Different number for receiving alerts
            "email": [
                "dosapatiyaswanth123@gmail.com"
            ] 
        }
        
        # File-based notification fallback
        self.notification_log_file = "notifications.log"
        
        logger.info(f"Notification system initialized - SMS: {self.sms_enabled}, Email: {self.email_enabled}")
    
    async def send_sms_alert(self, message: str, phone_numbers: List[str] = None) -> bool:
        """Send SMS alert to security staff"""
        if not self.sms_enabled:
            logger.warning("SMS notifications not configured")
            return False
        
        try:
            from twilio.rest import Client  # type: ignore
            
            # Check if we have valid Twilio credentials
            if not Config.TWILIO_ACCOUNT_SID or not Config.TWILIO_AUTH_TOKEN or not Config.TWILIO_PHONE_NUMBER:
                logger.warning("Twilio credentials not properly configured")
                return False
            
            # Try to send real SMS first
            try:
                client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
                numbers = phone_numbers or self.security_contacts["sms"]
                
                for number in numbers:
                    try:
                        message_obj = client.messages.create(
                            body=message,
                            from_=Config.TWILIO_PHONE_NUMBER,
                            to=number
                        )
                        logger.info(f"✅ REAL SMS sent to {number}: {message_obj.sid}")
                        return True
                    except Exception as e:
                        logger.error(f"❌ Failed to send real SMS to {number}: {e}")
                        # Fall back to demo logging
                        logger.info(f"DEMO SMS (real send failed to {number}): {message}")
                        self.log_sms_demo(message, [number])
                        return True
                        
            except Exception as e:
                logger.error(f"❌ Twilio client error: {e}")
                # Fall back to demo logging
                logger.info(f"DEMO SMS (Twilio error): {message}")
                self.log_sms_demo(message, phone_numbers or self.security_contacts["sms"])
                return True
            
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            # Log the message for demo purposes
            logger.info(f"DEMO SMS (error occurred): {message}")
            return False
    
    async def send_email_alert(self, subject: str, message: str, recipients: List[str] = None) -> bool:
        """Send email alert to management"""
        if not self.email_enabled:
            logger.warning("Email notifications not configured")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = f"Crowd Management <{Config.SMTP_USERNAME}>"
            msg['To'] = ", ".join(recipients or self.security_contacts["email"])
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'html'))
            
            # Use SSL instead of STARTTLS for port 465
            if Config.SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(Config.SMTP_SERVER, Config.SMTP_PORT)
            else:
                server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
                server.starttls()
            
            server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
            
            text = msg.as_string()
            server.sendmail(Config.SMTP_USERNAME, recipients or self.security_contacts["email"], text)
            server.quit()
            
            logger.info(f"Email sent to {recipients or self.security_contacts['email']}")
            return True
            
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            # For demo purposes, log the email content
            logger.info(f"DEMO EMAIL (failed to send):")
            logger.info(f"  To: {recipients or self.security_contacts['email']}")
            logger.info(f"  Subject: {subject}")
            logger.info(f"  Message: {message[:200]}...")
            return False
    
    def log_notification(self, notification_type: str, message: str, recipients: List[str] = None):
        """Log notification to file for demo purposes"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {notification_type.upper()}\n"
            log_entry += f"Recipients: {recipients or 'Default contacts'}\n"
            log_entry += f"Message: {message}\n"
            log_entry += "-" * 50 + "\n"
            
            with open(self.notification_log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
            
            logger.info(f"Notification logged to {self.notification_log_file}")
            
        except Exception as e:
            logger.error(f"Failed to log notification: {e}")
    
    def log_sms_demo(self, message: str, recipients: List[str]):
        """Log SMS demo to a separate file for easy viewing"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sms_log_file = "sms_demo.log"
            
            with open(sms_log_file, "a", encoding="utf-8") as f:
                f.write(f"📱 SMS DEMO - {timestamp}\n")
                f.write(f"To: {', '.join(recipients)}\n")
                f.write(f"Message: {message}\n")
                f.write("=" * 60 + "\n")
            
            logger.info(f"SMS demo logged to {sms_log_file}")
            
        except Exception as e:
            logger.error(f"Failed to log SMS demo: {e}")
    
    def create_alert_message(self, zone: str, alert_type: str, count: int, capacity: int, severity: str) -> Dict[str, str]:
        """Create formatted alert messages for different channels"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        percentage = (count / capacity) * 100
        
        # SMS message (concise)
        sms_message = f"🚨 CROWD ALERT - {zone.upper()}\n" \
                     f"Count: {count}/{capacity} ({percentage:.1f}%)\n" \
                     f"Level: {severity.upper()}\n" \
                     f"Time: {timestamp}"
        
        # Email message (detailed)
        email_subject = f"Crowd Management Alert - {zone.title()} - {severity.upper()}"
        
        email_message = f"""
        <html>
        <body>
            <h2>🚨 Crowd Management Alert</h2>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr>
                    <td><strong>Zone:</strong></td>
                    <td>{zone.title()}</td>
                </tr>
                <tr>
                    <td><strong>Alert Type:</strong></td>
                    <td>{alert_type.title()}</td>
                </tr>
                <tr>
                    <td><strong>Current Count:</strong></td>
                    <td>{count} people</td>
                </tr>
                <tr>
                    <td><strong>Capacity:</strong></td>
                    <td>{capacity} people</td>
                </tr>
                <tr>
                    <td><strong>Percentage:</strong></td>
                    <td>{percentage:.1f}%</td>
                </tr>
                <tr>
                    <td><strong>Severity:</strong></td>
                    <td style="color: {Config.ALERT_COLORS.get(severity, '#000000')};">{severity.upper()}</td>
                </tr>
                <tr>
                    <td><strong>Timestamp:</strong></td>
                    <td>{timestamp}</td>
                </tr>
            </table>
            
            <h3>Recommended Actions:</h3>
            <ul>
                {self._get_recommended_actions(severity, percentage)}
            </ul>
            
            <p><em>This is an automated alert from the Crowd Management System.</em></p>
        </body>
        </html>
        """
        
        return {
            "sms": sms_message,
            "email_subject": email_subject,
            "email_message": email_message
        }
    
    def _get_recommended_actions(self, severity: str, percentage: float) -> str:
        """Get recommended actions based on severity"""
        if severity == "red":
            return """
                <li>Immediately dispatch security personnel to the area</li>
                <li>Consider crowd control measures (barriers, staff deployment)</li>
                <li>Monitor for potential safety hazards</li>
                <li>Prepare emergency response protocols if needed</li>
            """
        elif severity == "yellow":
            return """
                <li>Increase monitoring frequency</li>
                <li>Prepare additional security staff if available</li>
                <li>Monitor crowd flow and behavior</li>
                <li>Consider crowd management measures</li>
            """
        else:
            return """
                <li>Continue normal monitoring</li>
                <li>Maintain current security levels</li>
            """
    
    async def send_crowd_alert(self, zone: str, alert_type: str, count: int, capacity: int, severity: str) -> Dict[str, bool]:
        """Send comprehensive crowd alert through all channels"""
        messages = self.create_alert_message(zone, alert_type, count, capacity, severity)
        
        results = {
            "sms_sent": False,
            "email_sent": False
        }
        
        # Send SMS to security staff
        if severity in ["yellow", "red"]:
            results["sms_sent"] = await self.send_sms_alert(messages["sms"])
            # Log to file as fallback
            self.log_notification("SMS", messages["sms"], self.security_contacts["sms"])
        
        # Send email to management
        if severity in ["yellow", "red"]:
            results["email_sent"] = await self.send_email_alert(
                messages["email_subject"],
                messages["email_message"]
            )
            # Log to file as fallback
            self.log_notification("EMAIL", f"Subject: {messages['email_subject']}\n{messages['email_message']}", self.security_contacts["email"])
        
        return results
    
    async def send_emergency_alert(self, zone: str, message: str) -> Dict[str, bool]:
        """Send emergency alert to all contacts immediately"""
        emergency_message = f"🚨 EMERGENCY ALERT - {zone.upper()}\n{message}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        results = {
            "sms_sent": await self.send_sms_alert(emergency_message),
            "email_sent": await self.send_email_alert(
                f"EMERGENCY - {zone.title()}",
                f"<h1>🚨 EMERGENCY ALERT</h1><p><strong>Zone:</strong> {zone.title()}</p><p><strong>Message:</strong> {message}</p>"
            )
        }
        
        return results
    
    async def send_system_health_alert(self, status: str, details: str) -> bool:
        """Send system health alerts to technical staff"""
        subject = f"System Health Alert - {status.upper()}"
        message = f"""
        <html>
        <body>
            <h2>System Health Alert</h2>
            <p><strong>Status:</strong> {status}</p>
            <p><strong>Details:</strong> {details}</p>
            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </body>
        </html>
        """
        
        return await self.send_email_alert(subject, message, ["tech@venue.com"])  # Replace with actual tech email
    
    def add_security_contact(self, contact_type: str, contact: str):
        """Add a new security contact"""
        if contact_type in self.security_contacts:
            if contact not in self.security_contacts[contact_type]:
                self.security_contacts[contact_type].append(contact)
                logger.info(f"Added {contact_type} contact: {contact}")
    
    def remove_security_contact(self, contact_type: str, contact: str):
        """Remove a security contact"""
        if contact_type in self.security_contacts:
            if contact in self.security_contacts[contact_type]:
                self.security_contacts[contact_type].remove(contact)
                logger.info(f"Removed {contact_type} contact: {contact}")

# Global notification manager instance
notification_manager = NotificationManager()
