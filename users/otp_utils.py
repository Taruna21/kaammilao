import random
import logging
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp_sms(phone, otp):
    logger.warning(f"SMS OTP for {phone}: {otp}")
    print(f"\n{'='*40}\n  OTP for {phone} is: {otp}\n{'='*40}\n")
    return True


def send_otp_email(email, otp):
    try:
        send_mail(
            subject='Your LocalServe OTP',
            message=f"""Hi,

Your OTP for LocalServe signup is:

        ➤  {otp}

⏱ Valid for 5 minutes only.
🔒 Do not share this with anyone.

— LocalServe Team""",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Email OTP error: {e}")
        return False


def send_welcome_email(email, full_name):
    try:
        send_mail(
            subject='Welcome to LocalServe! 🎉',
            message=f"""Hi {full_name},

Welcome to LocalServe! Your account has been created successfully.

You can now:
  • Browse and apply for jobs near you
  • Chat with recruiters directly
  • Build your profile and get hired

Login here: https://web-production-61033.up.railway.app/login/

— LocalServe Team""",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Welcome email error: {e}")


def send_password_reset_email(email, otp):
    try:
        send_mail(
            subject='Reset Your LocalServe Password 🔑',
            message=f"""Hi,

You requested a password reset on LocalServe.

Your OTP is:

        ➤  {otp}

⏱ Valid for 5 minutes only.
If you did not request this, ignore this email.

— LocalServe Team""",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Reset email error: {e}")
        return False


def send_password_reset_success_email(email, full_name):
    try:
        send_mail(
            subject='Password Reset Successful ✅',
            message=f"""Hi {full_name},

Your LocalServe password has been reset successfully.

If you did not do this, please contact us immediately by replying to this email.

Login here: https://web-production-61033.up.railway.app/login/

— LocalServe Team""",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Reset success email error: {e}")


def is_otp_valid(user, otp):
    if not user.otp or not user.otp_created_at:
        return False, "OTP not found. Please request a new one."
    elapsed = timezone.now() - user.otp_created_at
    if elapsed.total_seconds() > 300:  # 5 minutes
        return False, "OTP expired. Please request a new one."
    if user.otp != otp:
        return False, "Invalid OTP. Please try again."
    return True, "Valid"
