from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User
from .forms import XUserCreationForm, XUserChangeForm


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = XUserCreationForm
    form = XUserChangeForm
    model = User

    list_display = ("phone", "first_name", "last_name", "email", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active")
    ordering = ("-date_joined",)
    search_fields = ("phone", "first_name", "last_name", "email")

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("اطلاعات شخصی", {"fields": ("first_name", "last_name", "email")}),
        ("دسترسی‌ها", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("تاریخ‌ها", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser')
        }),
    )

