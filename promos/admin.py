# promos/admin.py
from django.contrib import admin
from django.utils.timezone import now

from .models import Campaign, Rule, Action, Coupon, CouponRedemption, PromoBanner
from .forms import RuleAdminForm, PromoBannerAdminForm

class RuleInline(admin.TabularInline):
    model = Rule
    form = RuleAdminForm
    extra = 1
    verbose_name = "شرط"
    verbose_name_plural = "شرایط"
    fields = ("kind", "categories", "brands", "products", "variants", "threshold", "qty")

    class Media:
        js = ("promos/js/rule_inline.js",)


class ActionInline(admin.TabularInline):
    model = Action
    extra = 1
    verbose_name = "تخفیف / اقدام"
    verbose_name_plural = "تخفیف‌ها / اقدامات"
    fields = ("kind", "scope", "value", "cap")


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "channel", "priority", "exclusive", "is_active", "starts_at", "ends_at", "is_running_now")
    list_filter = ("channel", "is_active", "exclusive")
    search_fields = ("name",)
    ordering = ("-priority", "-id")
    inlines = [RuleInline, ActionInline]

    fieldsets = (
        (None, {"fields": ("name", "channel", "priority", "exclusive")}),
        ("زمان‌بندی", {"fields": ("is_active", "starts_at", "ends_at")}),
    )

    def is_running_now(self, obj):
        return obj.is_running(now())

    is_running_now.boolean = True
    is_running_now.short_description = "در حال اجرا؟"

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "campaign", "is_active", "starts_at", "ends_at", "is_running_now",
                    "usage_limit_total", "usage_limit_per_user", "used_count")
    list_filter = ("is_active", "campaign")
    search_fields = ("code", "campaign__name")
    ordering = ("-starts_at", "-id")
    readonly_fields = ("used_count",)

    fieldsets = (
        ("اطلاعات کوپن", {"fields": ("code", "campaign", "stack_with_sales")}),
        ("زمان‌بندی", {"fields": ("is_active", "starts_at", "ends_at")}),
        ("محدودیت استفاده", {"fields": ("usage_limit_total", "usage_limit_per_user", "used_count")}),
    )

    def is_running_now(self, obj):
        return obj.is_running(now())
    is_running_now.boolean = True
    is_running_now.short_description = "فعال الان؟"

    def save_model(self, request, obj, form, change):
        if obj.code:
            obj.code = obj.code.strip().upper()
        super().save_model(request, obj, form, change)


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = ("coupon", "user_or_guest", "status", "created_at", "used_at")
    list_filter = ("status", "coupon")
    search_fields = ("coupon__code", "user__username", "user__phone_number", "guest_key")
    readonly_fields = ("created_at", "used_at")

    fieldsets = (
        ("وضعیت", {"fields": ("coupon", "status")}),
        ("کاربر / مهمان", {"fields": ("user", "guest_key")}),
        ("زمان‌ها", {"fields": ("created_at", "used_at")}),
    )

    def user_or_guest(self, obj):
        if obj.user:
            return f"{obj.user}"
        if obj.guest_key:
            return f"Guest: {obj.guest_key}"
        return "-"
    user_or_guest.short_description = "کاربر/مهمان"


@admin.register(PromoBanner)
class PromoBannerAdmin(admin.ModelAdmin):
    form = PromoBannerAdminForm

    list_display = ("title", "position", "slot", "campaign", "channel", "priority", "is_active", "starts_at", "ends_at",
                    "is_running_now", "updated_at")
    list_filter = ("position", "slot", "channel", "is_active", "campaign")
    search_fields = ("title", "subtitle", "link_url", "campaign__name")
    ordering = ("position", "priority", "-updated_at")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("نمایش و جایگاه",
         {"fields": ("position", "slot", "channel", "priority", "is_active", "starts_at", "ends_at")}),
        ("محتوا", {"fields": ("title", "subtitle", "button_text", "link_url")}),
        ("تصاویر", {"fields": ("image", "image_mobile")}),
        ("کمپین و فیلتر محصول", {
            "fields": ("campaign", "filter_kind", "filter_categories", "filter_brands", "filter_products",
                       "filter_variants", "limit_products")}),
        ("سیستمی", {"fields": ("created_at", "updated_at")}),
    )

    class Media:
        js = ("promos/js/promobanner_filter.js",)

    def is_running_now(self, obj):
        return obj.is_running(now())

    is_running_now.boolean = True
    is_running_now.short_description = "در حال نمایش؟"

# @admin.register(PromoBanner)
# class PromoBannerAdmin(admin.ModelAdmin):
#     list_display = (
#         "title",
#         "position",
#         "campaign",
#         "channel",
#         "is_active",
#         "starts_at",
#         "ends_at",
#         "is_running_now",
#     )
#     list_filter = ("position", "channel", "is_active", "campaign")
#     search_fields = ("title", "subtitle", "campaign__name")
#     ordering = ("-created_at",)
#
#     fieldsets = (
#         ("اطلاعات کلی", {
#             "fields": ("title", "subtitle", "campaign", "position", "channel")
#         }),
#         ("تصاویر و لینک", {
#             "fields": ("image", "image_mobile", "link_url", "button_text")
#         }),
#         ("زمان‌بندی و وضعیت", {
#             "fields": ("is_active", "starts_at", "ends_at")
#         }),
#     )
#
#     def is_running_now(self, obj):
#         return obj.is_running(now())
#     is_running_now.boolean = True
#     is_running_now.short_description = "در حال نمایش؟"
