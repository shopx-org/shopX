# shipping/models
from django.db import models
from account.models import User


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    title = models.CharField(max_length=100, blank=True, verbose_name="نام آدرس")
    province = models.CharField(max_length=50, verbose_name="استان")
    city = models.CharField(max_length=50, verbose_name="شهر")
    address = models.TextField(verbose_name="آدرس دقیق")
    number = models.CharField(max_length=50, blank=True, verbose_name="پلاک")
    unit = models.CharField(max_length=50, blank=True, verbose_name="واحد")
    postal_code = models.CharField(max_length=10, verbose_name="کد پستی")
    latitude = models.FloatField(null=True, blank=True, verbose_name="عرض جغرافیایی")
    longitude = models.FloatField(null=True, blank=True, verbose_name="طول جغرافیایی")
    is_default = models.BooleanField(default=False, verbose_name="آدرس پیش‌فرض")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")

    # tapin_province_id = models.IntegerField(null=True, blank=True)
    # tapin_city_id = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "آدرس"
        verbose_name_plural = "آدرس‌ها"

    def __str__(self):
        title_str = f"{self.title} - " if self.title else ""
        return f"{title_str}{self.province} - {self.city} - {self.address[:50]}..."


# =========================
# ShippingMethod
# =========================
from django.db import models

class ShippingMethod(models.Model):
    CARRIER_CHOICES = (
        ("post", "پست"),
        ("tipax", "تیپاکس"),
        ("courier", "پیک / ارسال درون‌شهری"),
        ("custom", "سفارشی"),
    )

    POST_SERVICE_CHOICES = (
        (0, "پست سفارشی"),
        (1, "پست پیشتاز"),
    )

    code = models.SlugField(max_length=50, unique=True, verbose_name="کد")
    name = models.CharField(max_length=100, verbose_name="عنوان")
    carrier = models.CharField(
        max_length=20,
        choices=CARRIER_CHOICES,
        default="post",
        verbose_name="نوع سرویس‌دهنده",
    )
    # فقط برای carrier == "post" استفاده میشه:
    tapin_post_service_type = models.IntegerField(
        choices=POST_SERVICE_CHOICES,
        null=True,
        blank=True,
        verbose_name="نوع سرویس پست در تاپین",
        help_text="برای پست سفارشی ۰ و برای پیشتاز ۱ (مطابق مستندات تاپین).",
    )

    is_active = models.BooleanField(default=True, verbose_name="فعال")
    base_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="هزینه ثابت پایه (تومان)",
        help_text="هزینه ثابت که به همه سفارش‌ها اضافه می‌شود (اختیاری).",
    )
    max_weight_grams = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="حداکثر وزن مجاز (گرم)",
        help_text="اگر خالی باشد، محدودیت وزنی ندارد.",
    )

    estimated_min_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="حداقل روز تحویل",
    )
    estimated_max_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="حداکثر روز تحویل",
    )

    class Meta:
        verbose_name = "روش ارسال"
        verbose_name_plural = "روش‌های ارسال"

    def __str__(self):
        return self.name

#
# # shipping/models.py
# from django.db import models
#
# class TapinConfig(models.Model):
#     shop_id = models.UUIDField(verbose_name="شناسه فروشگاه در تاپین")
#     from_province_id = models.IntegerField(verbose_name="استان مبدا (تاپین)")
#     from_city_id = models.IntegerField(verbose_name="شهر مبدا (تاپین)")
#
#     default_box_id = models.IntegerField(verbose_name="شناسه باکس پیش‌فرض پست")
#
#     # تنظیمات عمومی تیپاکس
#     tipax_shop_id = models.UUIDField(verbose_name="شناسه فروشگاه تیپاکس", null=True, blank=True)
#     tipax_product_type_id = models.IntegerField(default=0)
#     tipax_packing_type_id = models.IntegerField(default=0)
#     tipax_payment_type = models.IntegerField(default=1)
#     tipax_service_type = models.IntegerField(default=1)
#     tipax_delivery_type = models.IntegerField(default=1)
#     tipax_pickup_type = models.IntegerField(default=1)
#
#     api_token = models.CharField(max_length=255, blank=True, verbose_name="توکن API تاپین")
#
#     class Meta:
#         verbose_name = "تنظیمات تاپین"
#         verbose_name_plural = "تنظیمات تاپین"
#
#     def __str__(self):
#         return f"Tapin ({self.shop_id})"
