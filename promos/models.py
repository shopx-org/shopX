# /home/atusa92/PycharmProjects/ShopX/promos/models.py
from django.db import models
from django.utils import timezone
from django.conf import settings

class Campaign(models.Model):
    name = models.CharField(max_length=120)
    starts_at = models.DateTimeField()
    ends_at   = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    priority  = models.SmallIntegerField(default=0)      # بالاتر = مهم‌تر
    exclusive = models.BooleanField(default=False)
    channel   = models.CharField(max_length=24, default="web")

    def is_running(self, now=None):
        now = now or timezone.now()
        return self.is_active and self.starts_at <= now <= self.ends_at

class Rule(models.Model):
    KINDS = [
        ("product_in", "محصول مشخص"),
        ("category_in", "عضویت در دسته"),
        ("cart_min_total", "حداقل مبلغ سبد"),
        ("qty_at_least", "حداقل تعداد یک سطر"),
        ("variant_in", "واریانت مشخص"),
        ("brand_in", "برند مشخص"),
    ]
    campaign = models.ForeignKey(Campaign, related_name="rules", on_delete=models.CASCADE)
    kind = models.CharField(max_length=32, choices=KINDS)
    payload = models.JSONField(default=dict)  # ex: {"product_ids":[1,2]}, {"category_ids":[10]}

class Action(models.Model):
    KINDS = [("percent_off","درصدی"), ("amount_off","مبلغ ثابت"), ("free_shipping","ارسال رایگان")]
    SCOPES = [("line","سطر"), ("cart","سبد"), ("shipping","ارسال")]
    campaign = models.ForeignKey(Campaign, related_name="actions", on_delete=models.CASCADE)
    kind  = models.CharField(max_length=24, choices=KINDS)
    scope = models.CharField(max_length=16, choices=SCOPES, default="line")
    value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cap   = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

class Coupon(models.Model):
    code = models.CharField(max_length=32, unique=True, db_index=True)
    campaign = models.ForeignKey(Campaign, null=True, blank=True, on_delete=models.SET_NULL)
    starts_at = models.DateTimeField()
    ends_at   = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    usage_limit_total = models.PositiveIntegerField(null=True, blank=True)
    usage_limit_per_user = models.PositiveIntegerField(null=True, blank=True, default=1)
    used_count = models.PositiveIntegerField(default=0)

    def is_running(self, now=None):
        now = now or timezone.now()
        return self.is_active and self.starts_at <= now <= self.ends_at

    stack_with_sales = models.BooleanField(
        default=False,
        verbose_name="تجمیع با تخفیف‌های دیگر",
        help_text="اگر غیرفعال باشد، این کوپن فقط روی کالاهایی اعمال می‌شود که قبلاً تخفیف دیگری نگرفته‌اند."
    )
class CouponRedemption(models.Model):
    STATUS = (("reserved","رزروشده"), ("consumed","مصرف‌شده"), ("canceled","لغوشده"))
    coupon = models.ForeignKey(Coupon, related_name="redemptions", on_delete=models.CASCADE)
    user   = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    guest_key = models.CharField(max_length=191, null=True, blank=True) # hash موبایل/ایمیل مهمان
    # order  = models.ForeignKey("orders.Order", null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=16, choices=STATUS, default="reserved")
    created_at = models.DateTimeField(auto_now_add=True)
    used_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["coupon","user"],
                condition=models.Q(status__in=["reserved","consumed"]),
                name="uniq_coupon_user_active"
            ),
            models.UniqueConstraint(
                fields=["coupon","guest_key"],
                condition=models.Q(status__in=["reserved","consumed"]),
                name="uniq_coupon_guest_active"
            ),
        ]

# promos/models.py

class PromoBanner(models.Model):
    POSITIONS = [
        ("hero", "بنر بزرگ بالای صفحه"),
        ("strip", "نوار وسط صفحه"),
        ("sidebar", "بنر سایدبار"),
        # جدید
        ("home_grid", "گرید بنرهای صفحه اصلی"),
        ("daily_deal", "پیشنهاد روزانه"),
        ("deal_side", "بنر کنار پیشنهاد روزانه"),
    ]
    SLOTS = [
        ("", "—"),
        ("left", "چپ"),
        ("right", "راست"),
        ("top", "بالا"),
        ("bottom", "پایین"),
    ]

    title = models.CharField(max_length=200, verbose_name="عنوان بنر")
    subtitle = models.CharField(max_length=300, blank=True, verbose_name="زیرعنوان / توضیح کوتاه")
    campaign = models.ForeignKey(
        Campaign,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="banners",
        verbose_name="کمپین مرتبط",
    )
    position = models.CharField(max_length=20, choices=POSITIONS, default="hero", verbose_name="محل نمایش")
    image = models.ImageField(upload_to="promos/banners/", verbose_name="تصویر دسکتاپ")
    image_mobile = models.ImageField(
        upload_to="promos/banners/",
        null=True,
        blank=True,
        verbose_name="تصویر موبایل",
    )
    link_url = models.URLField(max_length=500, blank=True, verbose_name="لینک مقصد (لندینگ جشنواره)")
    button_text = models.CharField(max_length=50, blank=True, verbose_name="متن دکمه")

    # کنترل زمان و فعال بودن
    is_active = models.BooleanField(default=True, verbose_name="فعال؟")
    starts_at = models.DateTimeField(null=True, blank=True, verbose_name="شروع نمایش بنر")
    ends_at = models.DateTimeField(null=True, blank=True, verbose_name="پایان نمایش بنر")
    slot = models.CharField(
        max_length=30,
        blank=True,
        default="",
        choices=SLOTS,
        verbose_name="جایگاه داخل گرید",
    )
    priority = models.PositiveSmallIntegerField(
        default=10,
        verbose_name="اولویت نمایش (کمتر = بالاتر)"
    )

    product_filter = models.JSONField(default=dict,
                                      blank=True)  # مثلا {"discount_percent_gte": 30, "category_ids":[...]}
    limit_products = models.PositiveSmallIntegerField(default=12)
    payload = models.JSONField(default=dict, blank=True)
    channel = models.CharField(max_length=24, default="web", verbose_name="کانال")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "بنر تبلیغاتی"
        verbose_name_plural = "بنرهای تبلیغاتی"
        indexes = [
            models.Index(fields=["position", "channel", "is_active"]),
            models.Index(fields=["starts_at", "ends_at"]),
        ]

    def __str__(self):
        return self.title or f"Banner #{self.pk}"

    def is_running(self, now=None):
        """
        هم خود بنر، هم کمپین (اگر وصل باشد) باید در بازه زمانی و فعال باشد.
        """
        from django.utils import timezone
        now = now or timezone.now()

        # چک خود بنر
        if not self.is_active:
            return False
        if self.starts_at and self.starts_at > now:
            return False
        if self.ends_at and self.ends_at < now:
            return False

        # اگر کمپین وصل است، وضعیت خودش هم باید OK باشد
        if self.campaign:
            return self.campaign.is_running(now)

        return True
