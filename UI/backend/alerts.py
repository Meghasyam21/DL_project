import logging
import smtplib
import sys
import time
from email.message import EmailMessage
from pathlib import Path

# Add parent directory to path to enable absolute imports
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    ALERT_EMAIL_ENABLED,
    ALERT_EMAIL_FROM,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_PASSWORD,
    SMTP_USERNAME,
    ALERT_SMS_ENABLED,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_FROM_PHONE,
    ALERT_COOLDOWN_SECONDS,
    ALERT_DEFAULT_COUNTRY_CODE,
)
from contacts import get_all_contacts

try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
_last_alert_by_source = {}


def send_email_alert(subject: str, body: str):
    if not ALERT_EMAIL_ENABLED or not ALERT_EMAIL_FROM:
        logger.info("Email alert disabled or missing sender configuration.")
        return False

    contacts = get_all_contacts()
    alert_emails = contacts.get("emails", [])

    if not alert_emails:
        logger.info("No registered emails for alerts.")
        return False

    message = EmailMessage()
    message["From"] = ALERT_EMAIL_FROM
    message["To"] = ", ".join(alert_emails)
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.send_message(message)
        logger.info("Email alert sent to %s", alert_emails)
        return True
    except Exception as exc:
        logger.error("Email alert failed: %s", exc)
        return False


def send_sms_alert(body: str):
    if not ALERT_SMS_ENABLED or not TWILIO_AVAILABLE:
        logger.info("SMS alert disabled or Twilio not available.")
        return False

    contacts = get_all_contacts()
    alert_phones = contacts.get("phones", [])

    if not alert_phones:
        logger.info("No registered phones for alerts.")
        return False

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        for phone in alert_phones:
            phone = normalize_phone(phone)
            client.messages.create(
                body=body,
                from_=TWILIO_FROM_PHONE,
                to=phone,
            )
        logger.info("SMS alert sent to %s", alert_phones)
        return True
    except Exception as exc:
        logger.error("SMS alert failed: %s", exc)
        return False


def normalize_phone(phone: str) -> str:
    value = "".join(phone.strip().split())
    if value.startswith("+"):
        return value
    digits = "".join(char for char in value if char.isdigit())
    country_code = ALERT_DEFAULT_COUNTRY_CODE.strip()
    if digits and country_code:
        return f"{country_code}{digits}"
    return value


def send_detection_alert(source: str, detections: list):
    alert_label = detections[0]["label"] if detections else "Object"
    subject = f"{alert_label.title()} Alert from YOLOv8 Detection"
    body = f"{alert_label.title()} detected in source: {source}\n\nDetections:\n"
    for detection in detections:
        body += f"- {detection['label']} ({detection['confidence']:.2f}) at {detection['bbox']}\n"

    now = time.time()
    cooldown_key = source.split(" frame ", 1)[0]
    last_alert = _last_alert_by_source.get(cooldown_key, 0)
    if now - last_alert < ALERT_COOLDOWN_SECONDS:
        logger.info("Alert suppressed for %s during cooldown.", cooldown_key)
        return {
            "triggered": True,
            "suppressed": True,
            "reason": "cooldown",
            "email_sent": False,
            "sms_sent": False,
        }

    _last_alert_by_source[cooldown_key] = now
    email_sent = send_email_alert(subject, body)
    sms_sent = send_sms_alert(body)
    return {
        "triggered": True,
        "suppressed": False,
        "email_sent": email_sent,
        "sms_sent": sms_sent,
    }


def send_gun_alert(source: str, detections: list):
    return send_detection_alert(source, detections)
