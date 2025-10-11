from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile, PasswordLock
from .forms import XUserCreationForm, XUserChangeForm
from django_jalali.admin.filters import JDateFieldListFilter

admin.site.site_header = "پنل مدیریت shopX"
admin.site.site_title = "پنل"
admin.site.index_title = "پنل مدیریت"


# Inline برای نمایش پروفایل در صفحه ویرایش کاربر
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "پروفایل"
    fields = (("day", "month", "year"), "national_id", "gender", "display_name", "birth_date")
    readonly_fields = ("birth_date",)  # تعریف توی Inline
    extra = 0

    def birth_date(self, obj):
        return obj.birth_date

    birth_date.short_description = "تاریخ تولد"  # تنظیم verbose_name


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = XUserCreationForm
    form = XUserChangeForm
    model = User
    inlines = [ProfileInline]

    list_display = ("phone", "first_name", "last_name", "email", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active", ("date_joined", JDateFieldListFilter))
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
            "classes": ("wide",),
            "fields": ("phone", "password1", "password2", "first_name", "last_name", "email", "is_active", "is_staff",
                       "is_superuser"),
        }),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "national_id", "day", "month", "year", "gender", "display_name", "birth_date")
    search_fields = ("user__phone", "national_id", "display_name")
    list_filter = ("gender", ("year", JDateFieldListFilter))
    ordering = ("user__phone",)
    readonly_fields = ("birth_date",)  # تعریف توی ProfileAdmin

    fieldsets = (
        (None, {"fields": ("user",)}),
        ("اطلاعات پروفایل", {
            "fields": (("day", "month", "year"), "national_id", "gender", "display_name"),
        }),
        ("تاریخ تولد", {  # بخش جداگانه برای birth_date
            "fields": ("birth_date",),
        }),
    )

    def birth_date(self, obj):
        return obj.birth_date

    birth_date.short_description = "تاریخ تولد"  # تنظیم verbose_name


@admin.register(PasswordLock)
class PasswordLockAdmin(admin.ModelAdmin):
    list_display = ("phone", "failed", "locked_until", "is_locked")
    search_fields = ("phone",)
    list_filter = (("locked_until", JDateFieldListFilter),)
    ordering = ("phone",)

    fieldsets = (
        (None, {"fields": ("phone", "failed", "locked_until")}),
    )
