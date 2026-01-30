"""SMS notification handler using Twilio."""
import logging
import os
from typing import Optional

from twilio.rest import Client as TwilioClient

from shared.schemas import NotificationEvent

logger = logging.getLogger(__name__)


class SMSHandler:
    """Sends SMS notifications via Twilio."""
    
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER", "")
        
        self._client: Optional[TwilioClient] = None
        if self.account_sid and self.auth_token:
            self._client = TwilioClient(self.account_sid, self.auth_token)
    
    def _create_message(self, notification: NotificationEvent) -> str:
        """Create SMS message text."""
        return (
            f"🚨 {notification.symbol} Alert!\n"
            f"Price: ${notification.current_price:,.2f}\n"
            f"Condition: {notification.condition.value} ${notification.target_price:,.2f}\n"
            f"- Price Alert System"
        )
    
    async def send(self, notification: NotificationEvent) -> bool:
        """Send SMS notification."""
        if not self._client:
            logger.warning("Twilio not configured, skipping SMS")
            return False
        
        if not notification.user_phone:
            logger.warning(f"No phone number for user {notification.user_id}")
            return False
        
        try:
            message = self._client.messages.create(
                body=self._create_message(notification),
                from_=self.from_number,
                to=notification.user_phone
            )
            
            logger.info(
                f"SMS sent to {notification.user_phone} for {notification.symbol} "
                f"(SID: {message.sid})"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS to {notification.user_phone}: {e}")
            return False
