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
