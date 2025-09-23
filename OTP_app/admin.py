from django.contrib import admin
from .models import OtpSession, OtpBlock

@admin.register(OtpSession)
class OtpSessionAdmin(admin.ModelAdmin):
    list_display = ("phone", "token", "created_at", "expires_at", "resend_count", "is_used")
    list_filter = ("is_used", "created_at")
    search_fields = ("phone", "token")
    ordering = ("-created_at",)

@admin.register(OtpBlock)
class OtpBlockAdmin(admin.ModelAdmin):
    list_display = ("phone", "blocked_until")
    search_fields = ("phone",)
    ordering = ("-blocked_until",)
