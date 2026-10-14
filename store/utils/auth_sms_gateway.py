import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class TextbeeGateway:
    def send_sms(self, device, token):
        url = "https://api.textbee.dev/api/v1/gateway/send-sms"
        headers = {
            "x-api-key": settings.TEXTBEE_API_KEY,
            "Content-Type": "application/json"
        }
        # Dynamically fetches the user's registered phone number
        target_number = device.number.as_e164

        # Break the 6-digit token into two 3-digit parts separated by a space
        # This prevents telecom filters from blocking the self-sent OTP message
        token_str = str(token)
        # formatted_token = f"{token_str[:3]} {token_str[3:]}"

        payload = {
            "recipients": [target_number],
            "message": f"Your MEcomm,Hello! This is a test Security pin is: {token_str}.Keep it up.",
            "deviceId": settings.TEXTBEE_DEVICE_ID
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info(f"Successfully triggered Textbee SMS to {target_number}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Textbee SMS failed: {e}")

