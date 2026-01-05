# promos/admin.py
from django.contrib import admin
from django.utils.timezone import now
from Core.admin_mixins import JalaliAdminMixin
from .models import Campaign, Rule, Action, Coupon, CouponRedemption, PromoBanner
from .forms import RuleAdminForm, PromoBannerAdminForm
from django.core.exceptions import ValidationError
from django.contrib import admin
from django.utils.html import format_html
from .models import PromoBanner

def _used_product_ids_in_any_campaign(exclude_campaign_id=None) -> set[int]:
    from promos.models import Rule

    qs = Rule.objects.filter(kind="product_in").only("campaign_id", "payload")
    if exclude_campaign_id:
        qs = qs.exclude(campaign_id=exclude_campaign_id)

    used: set[int] = set()
    for r in qs:
        payload = getattr(r, "payload", None) or {}
        ids = payload.get("product_ids") or []
        for pid in ids:
            try:
                used.add(int(pid))
            except Exception:
                pass
    return used

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
class CampaignAdmin(JalaliAdminMixin):
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
class CouponAdmin(JalaliAdminMixin):
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
class PromoBannerAdmin(JalaliAdminMixin):
    form = PromoBannerAdminForm

    list_display = ("title", "position", "slot", "campaign", "channel", "priority",
                    "is_active", "starts_at", "ends_at", "is_running_now", "updated_at")
    list_filter = ("position", "slot", "channel", "is_active", "campaign")
    search_fields = ("title", "subtitle", "campaign__name")
    ordering = ("position", "priority", "-updated_at")
    readonly_fields = ("created_at", "updated_at")
    exclude = ("link_url",)

    fieldsets = (
        ("نمایش و جایگاه", {"fields": ("position", "slot", "priority", "is_active")}),
        ("کمپین", {"fields": ("campaign",)}),
        ("زمان‌بندی (اگر کمپین انتخاب شود از کمپین پر می‌شود)", {"fields": ("channel", "starts_at", "ends_at")}),
        ("محتوا", {"fields": ("title", "subtitle", "button_text")}),
        ("جشنواره / کانت‌داون", {"fields": ("show_before_campaign", "show_countdown", "countdown_mode")}),
        ("تصاویر", {"fields": ("image", "image_mobile")}),
        ("سیستمی", {"fields": ("created_at", "updated_at")}),
    )

    def destination_preview(self, obj):
        if not obj or obj.destination_url in ("", "#"):
            return "—"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">باز کردن صفحه هدف ↗</a>',
            obj.destination_url
        )

    destination_preview.short_description = "صفحه هدف (خودکار)"

    def clean(self):
        cleaned = super().clean()

        campaign = cleaned.get("campaign")
        kind = (cleaned.get("filter_kind") or "").strip()

        # کانت‌داون/پیش‌جشنواره
        show_before = bool(cleaned.get("show_before_campaign"))
        countdown_mode = cleaned.get("countdown_mode") or ""
        if (show_before or countdown_mode) and not campaign:
            raise ValidationError({"campaign": "برای پیش‌جشنواره/کانت‌داون باید یک کمپین انتخاب کنید."})

        if campaign:
            # 1) کانال یکی باشد
            if cleaned.get("channel") and campaign.channel != cleaned["channel"]:
                raise ValidationError({"channel": "کانال بنر باید با کانال کمپین یکی باشد."})

            # 2) زمان‌بندی بنر داخل بازه کمپین (اگر ست شده)
            starts_at = cleaned.get("starts_at")
            ends_at = cleaned.get("ends_at")
            if starts_at and starts_at < campaign.starts_at:
                raise ValidationError({"starts_at": "شروع بنر نمی‌تواند قبل از شروع کمپین باشد."})
            if ends_at and ends_at > campaign.ends_at:
                raise ValidationError({"ends_at": "پایان بنر نمی‌تواند بعد از پایان کمپین باشد."})

            # 3) چک زیرمجموعه بودن فیلتر بنر نسبت به Ruleهای کمپین
            if kind:
                self._validate_banner_filter_is_subset_of_campaign(cleaned, campaign)

        # اعتبارسنجی ساده قبلی خودت برای فیلترهای بنر (همچنان لازم)
        if kind == "category_in" and not cleaned.get("filter_categories"):
            raise ValidationError({"filter_categories": "حداقل یک دسته انتخاب کنید."})
        if kind == "brand_in" and not cleaned.get("filter_brands"):
            raise ValidationError({"filter_brands": "حداقل یک برند انتخاب کنید."})
        if kind == "product_in" and not cleaned.get("filter_products"):
            raise ValidationError({"filter_products": "حداقل یک محصول انتخاب کنید."})
        if kind == "variant_in" and not cleaned.get("filter_variants"):
            raise ValidationError({"filter_variants": "حداقل یک واریانت انتخاب کنید."})

        return cleaned

    def _campaign_allowed_sets(self, campaign):
        """
        از Ruleهای کمپین، دامنه‌ی مجاز را استخراج می‌کند.
        نکته: اینجا فقط ruleهای فیلترکننده کالا را در نظر می‌گیریم.
        """
        allowed = {
            "category_ids": set(),
            "brand_ids": set(),
            "product_ids": set(),
            "variant_ids": set(),
        }

        for r in campaign.rules.all():
            p = r.payload or {}
            if r.kind == "category_in":
                allowed["category_ids"].update(p.get("category_ids", []))
            elif r.kind == "brand_in":
                allowed["brand_ids"].update(p.get("brand_ids", []))
            elif r.kind == "product_in":
                allowed["product_ids"].update(p.get("product_ids", []))
            elif r.kind == "variant_in":
                allowed["variant_ids"].update(p.get("variant_ids", []))

        return allowed

    def _validate_banner_filter_is_subset_of_campaign(self, cleaned, campaign):
        kind = (cleaned.get("filter_kind") or "").strip()
        allowed = self._campaign_allowed_sets(campaign)

        # اگر کمپین هیچ rule فیلترکننده‌ای نداشت، تداخل نداریم (کمپین عمومی است)
        has_any_scope_rule = any(len(s) for s in allowed.values())
        if not has_any_scope_rule:
            return

        # زیرمجموعه بودن با توجه به نوع فیلتر بنر
        if kind == "category_in":
            chosen = set(cleaned["filter_categories"].values_list("id", flat=True))
            camp = allowed["category_ids"]
            if camp and not chosen.issubset(camp):
                raise ValidationError(
                    {"filter_categories": "دسته‌های انتخابی بنر باید زیرمجموعه‌ی دسته‌های کمپین باشد."})

        elif kind == "brand_in":
            chosen = set(cleaned["filter_brands"].values_list("id", flat=True))
            camp = allowed["brand_ids"]
            if camp and not chosen.issubset(camp):
                raise ValidationError({"filter_brands": "برندهای انتخابی بنر باید زیرمجموعه‌ی برندهای کمپین باشد."})

        elif kind == "product_in":
            chosen = set(cleaned["filter_products"].values_list("id", flat=True))
            camp = allowed["product_ids"]
            # اگر کمپین product_in دارد، باید زیرمجموعه باشد
            if camp and not chosen.issubset(camp):
                raise ValidationError({"filter_products": "محصولات انتخابی بنر باید زیرمجموعه‌ی محصولات کمپین باشد."})

        elif kind == "variant_in":
            chosen = set(cleaned["filter_variants"].values_list("id", flat=True))
            camp = allowed["variant_ids"]
            if camp and not chosen.issubset(camp):
                raise ValidationError(
                    {"filter_variants": "واریانت‌های انتخابی بنر باید زیرمجموعه‌ی واریانت‌های کمپین باشد."})

    #
    # class Media:
    #     js = ("promos/js/promobanner_filter.js",)

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
