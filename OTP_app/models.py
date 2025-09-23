from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

class OtpSession(models.Model):
    token = models.CharField(max_length=64, db_index=True)
    phone = models.CharField(max_length=11, db_index=True)

    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_sent_at = models.DateTimeField(auto_now_add=True)
    resend_count = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    def set_code(self, code: str):
        self.code_hash = make_password(str(code))

    def check_code(self, code: str) -> bool:
        return check_password(str(code), self.code_hash)

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at


class OtpBlock(models.Model):
    phone = models.CharField(max_length=11, unique=True)
    blocked_until = models.DateTimeField(null=True, blank=True)
    # NEW: شمارش تلاش‌ها در یک بازه (پنجره) زمانی
    attempts = models.PositiveSmallIntegerField(default=0)
    window_started_at = models.DateTimeField(null=True, blank=True)

    def is_blocked(self) -> bool:
        return self.blocked_until and timezone.now() < self.blocked_until
