import random
import logging
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp_sms(phone, otp):
    print(f"\n{'='*40}\n  OTP for {phone} is: {otp}\n{'='*40}\n")
    return True


def _send_email(to_email, subject, body):
    """Use SendGrid in production, Gmail locally."""
    api_key = getattr(settings, 'SENDGRID_API_KEY', '')

    if api_key:
        # Production — SendGrid HTTP API
        import urllib.request
        import json
        data = json.dumps({
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}]
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.sendgrid.com/v3/mail/send',
            data=data,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 202
        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            return False
    else:
        # Local — Gmail SMTP
        try:
            from django.core.mail import send_mail
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[to_email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            logger.error(f"Gmail error: {e}")
            return False


def send_otp_email(email, otp):
    return _send_email(
        email,
        'Your LocalServe OTP',
        f"""Hi,

Your OTP for LocalServe signup is:

    {otp}

Valid for 5 minutes. Do not share it with anyone.

— LocalServe Team"""
    )


def send_password_reset_email(email, otp):
    return _send_email(
        email,
        'Reset Your LocalServe Password',
        f"""Hi,

Your password reset OTP is:

    {otp}

Valid for 5 minutes. If you did not request this, ignore this email.

— LocalServe Team"""
    )


def send_welcome_email(email, full_name):
    _send_email(
        email,
        'Welcome to LocalServe! 🎉',
        f"""Hi {full_name},

Welcome to LocalServe! Your account is ready.

Login: https://web-production-61033.up.railway.app/login/

— LocalServe Team"""
    )


def send_password_reset_success_email(email, full_name):
    _send_email(
        email,
        'Password Reset Successful ✅',
        f"""Hi {full_name},

Your LocalServe password was reset successfully.

If this wasn't you, contact us immediately.

— LocalServe Team"""
    )


def is_otp_valid(user, otp):
    if not user.otp or not user.otp_created_at:
        return False, "OTP not found. Please request a new one."
    elapsed = timezone.now() - user.otp_created_at
    if elapsed.total_seconds() > 300:
        return False, "OTP expired. Please request a new one."
    if user.otp != otp:
        return False, "Invalid OTP. Please try again."
    return True, "Valid"
