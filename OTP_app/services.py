from .models import OtpSession, OtpBlock
# otp/services.py
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from datetime import timedelta
from uuid import uuid4
import secrets
import ghasedakpack

# تنظیمات
OTP_TTL_SECONDS       = getattr(settings, "OTP_TTL_SECONDS", 120)      # 2 دقیقه
OTP_RESEND_GAP_SEC    = getattr(settings, "OTP_RESEND_GAP_SEC", 60)    # حداقل فاصله 60s بین دو ارسال
OTP_MAX_RESENDS       = getattr(settings, "OTP_MAX_RESENDS", 3)        # برای همان توکن (برای UI)
OTP_BLOCK_DURATION    = getattr(settings, "OTP_BLOCK_DURATION", 3600)  # مدت بلاک: 1 ساعت (ثانیه)
OTP_TEMPLATE_NAME     = getattr(settings, "OTP_TEMPLATE_NAME", "verifyphone")
GHASEDAK_API_KEY      = getattr(settings, "GHASEDAK_API_KEY", "")

# NEW: پنجرهٔ شمارش کل ارسال‌ها
OTP_WINDOW_SECONDS    = getattr(settings, "OTP_WINDOW_SECONDS", 3600)  # 1 ساعت
OTP_MAX_ATTEMPTS_IN_WINDOW = getattr(settings, "OTP_MAX_ATTEMPTS_IN_WINDOW", 3)  # مجموع ارسال‌ها (initial + resend)

def _within_window(block):
    if not block.window_started_at:
        return False
    return (timezone.now() - block.window_started_at).total_seconds() < OTP_WINDOW_SECONDS

def _reset_window(block):
    block.window_started_at = timezone.now()
    block.attempts = 0

def _can_send_now(block):
    """
    قبل از ارسال: اگر بلاک است -> False
    اگر در پنجرهٔ جاری هست و attempts >= 3 -> False (و بلاک کن)
    در غیر اینصورت -> True
    """
    if block.is_blocked():
        return False

    if not _within_window(block):
        # پنجرهٔ جدید را آغاز کن
        _reset_window(block)
        block.save()
        return True

    if block.attempts >= OTP_MAX_ATTEMPTS_IN_WINDOW:
        # همین الان بلاک شود (چهارمین تلاش)
        block.blocked_until = timezone.now() + timedelta(seconds=OTP_BLOCK_DURATION)
        block.save()
        return False
    return True

def _register_attempt(block):
    """
    بعد از ارسال موفق: شمارندهٔ پنجره ++
    اگر با این ارسال به سقف برسیم، اجازه داده‌ایم، اما ارسال بعدی بلاک خواهد شد.
    """
    if not _within_window(block):
        _reset_window(block)
    block.attempts += 1
    block.save()

SMS = ghasedakpack.Ghasedak(settings.GHASEDAK_API_KEY)


class OtpError(Exception): ...
class OtpBlocked(OtpError): ...
class OtpTooSoon(OtpError): ...
class OtpMaxReached(OtpError): ...
class OtpInvalid(OtpError): ...
class OtpExpired(OtpError): ...

def _new_code():
    return secrets.randbelow(9000) + 1000  # 1000..9999

def _send_otp_sms(phone: str, code: int):
    # هیچ لاگ/پرینتی از کد نکن!
    SMS.verification({
        "receptor": phone,
        "type": "1",
        "template": settings.OTP_TEMPLATE_NAME,
        "param1": code
    })

@transaction.atomic
def create_session(phone: str) -> str:
    block, _ = OtpBlock.objects.select_for_update().get_or_create(phone=phone)

    # اول بلاک/سقف کلی را بررسی کن
    if not _can_send_now(block):
        raise OtpBlocked("blocked")

    # فاصله حداقل بین ارسال‌ها (ضد اسپم)
    last = OtpSession.objects.filter(phone=phone, is_used=False).order_by("-created_at").first()
    if last and (timezone.now() - last.last_sent_at).total_seconds() < OTP_RESEND_GAP_SEC:
        raise OtpTooSoon("cooldown")

    # سشن‌های باز قبلی را پاک کن (سادگی)
    OtpSession.objects.filter(phone=phone, is_used=False).delete()

    token = str(uuid4())
    code = _new_code()

    sess = OtpSession(
        token=token,
        phone=phone,
        expires_at=timezone.now() + timedelta(seconds=OTP_TTL_SECONDS),
    )
    sess.set_code(code)
    sess.save()

    # ارسال
    _send_otp_sms(phone, code)

    # ثبت تلاش در پنجرهٔ کلی
    _register_attempt(block)

    return token

@transaction.atomic
def resend(token: str) -> None:
    sess = OtpSession.objects.select_for_update().filter(token=token, is_used=False).first()
    if not sess:
        raise OtpInvalid("not-found")

    block, _ = OtpBlock.objects.select_for_update().get_or_create(phone=sess.phone)

    # اول بلاک/سقف کلی را بررسی کن
    if not _can_send_now(block):
        raise OtpBlocked("blocked")

    # سپس سقف resend همین توکن (برای UI و تجربه کاربری)
    if sess.resend_count >= OTP_MAX_RESENDS:
        # رسید به سقف توکن → همان لحظه بلاک کلی هم فعال شود
        block.blocked_until = timezone.now() + timedelta(seconds=OTP_BLOCK_DURATION)
        block.save()
        raise OtpMaxReached("max-resends")

    # حداقل فاصله بین ارسال‌ها
    if (timezone.now() - sess.last_sent_at).total_seconds() < OTP_RESEND_GAP_SEC:
        raise OtpTooSoon("cooldown")

    # تولید کد جدید
    code = _new_code()
    sess.set_code(code)
    sess.expires_at = timezone.now() + timedelta(seconds=OTP_TTL_SECONDS)
    sess.last_sent_at = timezone.now()
    sess.resend_count += 1
    sess.save()

    _send_otp_sms(sess.phone, code)

    # ثبت تلاش در پنجرهٔ کلی
    _register_attempt(block)

@transaction.atomic
def verify(token: str, code: str) -> str:
    sess = OtpSession.objects.select_for_update().filter(token=token, is_used=False).first()
    if not sess:
        raise OtpInvalid("not-found")
    if sess.is_expired():
        raise OtpExpired("expired")
    if not sess.check_code(code):
        raise OtpInvalid("bad-code")
    sess.is_used = True
    sess.save(update_fields=["is_used"])
    return sess.phone

def seconds_left(token: str) -> int:
    sess = OtpSession.objects.filter(token=token, is_used=False).first()
    if not sess:
        return 0
    return max(0, int((sess.expires_at - timezone.now()).total_seconds()))

def resends_left(token: str) -> int:
    sess = OtpSession.objects.filter(token=token, is_used=False).first()
    if not sess:
        return 0
    return max(0, OTP_MAX_RESENDS - sess.resend_count)

