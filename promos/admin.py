# promos/admin.py
from django.contrib import admin
from django.utils.timezone import now

from .models import Campaign, Rule, Action, Coupon, CouponRedemption, PromoBanner
from .forms import RuleAdminForm


# ========== Inlines ==========

class RuleInline(admin.TabularInline):
    """
    قاعده‌های کمپین؛ از RuleAdminForm استفاده می‌کنیم تا
    برای category_in / cart_min_total / qty_at_least
    payload به‌صورت خودکار ساخته شود.
    """
    model = Rule
    form = RuleAdminForm
    extra = 1
    verbose_name = "قاعده"
    verbose_name_plural = "قواعد"
    # فیلدهایی که در اینلاین نشان داده می‌شوند
    fields = ("kind", "categories", "threshold", "qty", "payload")


class ActionInline(admin.TabularInline):
    """
    اکشن‌های کمپین (درصدی، مبلغ ثابت، ارسال رایگان ...)
    """
    model = Action
    extra = 1
    verbose_name = "اکشن"
    verbose_name_plural = "اکشن‌ها"
    fields = ("kind", "scope", "value", "cap")


# ========== Campaign Admin ==========

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "channel",
        "priority",
        "exclusive",
        "is_active",
        "starts_at",
        "ends_at",
        "is_running_now",

    )
    list_filter = ("channel", "is_active", "exclusive")
    search_fields = ("name",)
    ordering = ("-priority", "-id")
    inlines = [RuleInline, ActionInline]

    fieldsets = (
        (None, {
            "fields": ("name", "channel", "priority", "exclusive")
        }),
        ("وضعیت زمان‌بندی", {
            "fields": ("is_active", "starts_at", "ends_at")
        }),
    )

    def is_running_now(self, obj):
        return obj.is_running(now())
    is_running_now.boolean = True
    is_running_now.short_description = "در حال اجرا؟"


# ========== Coupon Admin ==========

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "campaign",
        "is_active",
        "starts_at",
        "ends_at",
        "is_running_now",
        "usage_limit_total",
        "usage_limit_per_user",
        "used_count",

    )
    list_filter = ("is_active", "campaign")
    search_fields = ("code", "campaign__name")
    ordering = ("-starts_at", "-id")
    readonly_fields = ("used_count",)

    fieldsets = (
        (None, {
            "fields": ("code", "campaign","stack_with_sales")
        }),
        ("بازه زمانی و وضعیت", {
            "fields": ("is_active", "starts_at", "ends_at")
        }),
        ("محدودیت استفاده", {
            "fields": ("usage_limit_total", "usage_limit_per_user","used_count")
        }),
    )

    def is_running_now(self, obj):
        return obj.is_running(now())
    is_running_now.boolean = True
    is_running_now.short_description = "در حال اجرا؟"

    def save_model(self, request, obj, form, change):
        # کد کوپن را همیشه trim و Uppercase می‌کنیم
        if obj.code:
            obj.code = obj.code.strip().upper()
        super().save_model(request, obj, form, change)


# ========== CouponRedemption Admin ==========

@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = (
        "coupon",
        "user_or_guest",
        "status",
        "created_at",
        "used_at",
    )
    list_filter = ("status", "coupon")
    search_fields = (
        "coupon__code",
        "user__username",
        "user__phone_number",
        "guest_key",
    )
    readonly_fields = ("created_at", "used_at")

    fieldsets = (
        (None, {
            "fields": ("coupon", "status")
        }),
        ("کاربر / مهمان", {
            "fields": ("user", "guest_key")
        }),
        ("زمان‌ها", {
            "fields": ("created_at", "used_at")
        }),
    )

    def user_or_guest(self, obj):
        if obj.user:
            return f"User: {obj.user}"
        if obj.guest_key:
            return f"Guest: {obj.guest_key}"
        return "-"
    user_or_guest.short_description = "کاربر/مهمان"


# ========== PromoBanner Admin ==========

@admin.register(PromoBanner)
class PromoBannerAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "position",
        "campaign",
        "channel",
        "is_active",
        "starts_at",
        "ends_at",
        "is_running_now",
    )
    list_filter = ("position", "channel", "is_active", "campaign")
    search_fields = ("title", "subtitle", "campaign__name")
    ordering = ("-created_at",)

    fieldsets = (
        ("اطلاعات کلی", {
            "fields": ("title", "subtitle", "campaign", "position", "channel")
        }),
        ("تصاویر و لینک", {
            "fields": ("image", "image_mobile", "link_url", "button_text")
        }),
        ("زمان‌بندی و وضعیت", {
            "fields": ("is_active", "starts_at", "ends_at")
        }),
    )

    def is_running_now(self, obj):
        return obj.is_running(now())
    is_running_now.boolean = True
    is_running_now.short_description = "در حال نمایش؟"
