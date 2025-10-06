from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile, PasswordLock
from .forms import XUserCreationForm, XUserChangeForm


# Inline برای نمایش پروفایل در صفحه ویرایش کاربر
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False  # جلوگیری از حذف پروفایل از طریق ادمین
    verbose_name_plural = "پروفایل"
    fields = ("national_id", "birth_date", "gender", "display_name")
    extra = 0  # جلوگیری از نمایش فرم خالی اضافی


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = XUserCreationForm
    form = XUserChangeForm
    model = User

    # نمایش پروفایل به‌صورت inline
    inlines = [ProfileInline]

    list_display = ("phone", "first_name", "last_name", "email", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active")
    ordering = ("-date_joined",)
    search_fields = ("phone", "first_name", "last_name", "email", "profile__national_id", "profile__display_name")

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("اطلاعات شخصی", {"fields": ("first_name", "last_name", "email")}),
        ("دسترسی‌ها", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("تاریخ‌ها", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'password1', 'password2', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser')
        }),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "national_id", "birth_date", "gender", "display_name")
    search_fields = ("user__phone", "national_id", "display_name")
    list_filter = ("gender",)
    ordering = ("user__phone",)

    fieldsets = (
        (None, {"fields": ("user",)}),
        ("اطلاعات پروفایل", {"fields": ("national_id", "birth_date", "gender", "display_name")}),
    )


@admin.register(PasswordLock)
class PasswordLockAdmin(admin.ModelAdmin):
    list_display = ("phone", "failed", "locked_until", "is_locked")
    search_fields = ("phone",)
    list_filter = ("locked_until",)
    ordering = ("phone",)

    fieldsets = (
        (None, {"fields": ("phone", "failed", "locked_until")}),
    )