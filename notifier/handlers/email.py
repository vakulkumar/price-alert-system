"""Email notification handler using aiosmtplib."""
import logging
import os
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiosmtplib

from shared.schemas import NotificationEvent

logger = logging.getLogger(__name__)


class EmailHandler:
    """Sends email notifications via SMTP."""
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
    
    def _create_email(self, notification: NotificationEvent) -> MIMEMultipart:
        """Create email message from notification."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚨 Price Alert: {notification.symbol} triggered!"
        msg["From"] = self.from_email
        msg["To"] = notification.user_email
        
        # Plain text version
        text = f"""
Your price alert has been triggered!

Symbol: {notification.symbol}
Condition: {notification.condition} ${notification.target_price:,.2f}
Current Price: ${notification.current_price:,.2f}

---
Price Alert System
        """
        
        # HTML version
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 500px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ padding: 30px; }}
        .price-box {{ background: #f8f9fa; border-radius: 8px; padding: 20px; margin: 20px 0; }}
        .symbol {{ font-size: 28px; font-weight: bold; color: #333; }}
        .price {{ font-size: 36px; font-weight: bold; color: #22c55e; margin: 10px 0; }}
        .condition {{ color: #666; font-size: 14px; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #888; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 Price Alert Triggered!</h1>
        </div>
        <div class="content">
            <div class="price-box">
                <div class="symbol">{notification.symbol}</div>
                <div class="price">${notification.current_price:,.2f}</div>
                <div class="condition">
                    Alert: {notification.condition.value.upper()} ${notification.target_price:,.2f}
                </div>
            </div>
            <p style="color: #666; font-size: 14px;">
                Your price alert condition has been met. The current market price of 
                <strong>{notification.symbol}</strong> is <strong>${notification.current_price:,.2f}</strong>.
            </p>
        </div>
        <div class="footer">
            Price Alert System • Powered by Real-Time Market Data
        </div>
    </div>
</body>
</html>
        """
        
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))
        
        return msg
    
    async def send(self, notification: NotificationEvent) -> bool:
        """Send email notification."""
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials not configured, skipping email")
            return False
        
        try:
            msg = self._create_email(notification)
            
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=True
            )
            
            logger.info(f"Email sent to {notification.user_email} for {notification.symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {notification.user_email}: {e}")
            return False
