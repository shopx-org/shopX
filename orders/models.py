from __future__ import annotations

from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from products.models import Product, ProductVariant
from shipping.models import Address, ShippingMethod


class Order(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING  = "pending",  "در انتظار پرداخت"
        PAID     = "paid",     "پرداخت شده"
        FAILED   = "failed",   "ناموفق"
        CANCELED = "canceled", "لغو شده"
        REFUNDED = "refunded", "بازپرداخت شده"

    class FulfillmentStatus(models.TextChoices):
        NEW        = "new",        "جدید"
        PROCESSING = "processing", "در حال آماده‌سازی"
        SHIPPED    = "shipped",    "ارسال شده"
        DELIVERED  = "delivered",  "تحویل شده"
        RETURNED   = "returned",   "مرجوع شده"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="orders",
        verbose_name="کاربر",
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name="وضعیت پرداخت",
    )

    fulfillment_status = models.CharField(
        max_length=20,
        choices=FulfillmentStatus.choices,
        default=FulfillmentStatus.NEW,
        verbose_name="وضعیت ارسال",
    )

    address = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="آدرس ارسال",
    )
    shipping_method = models.ForeignKey(
        ShippingMethod,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
        verbose_name="روش ارسال",
    )
    shipping_price = models.DecimalField(
        max_digits=14, decimal_places=0,
        default=0,
        verbose_name="هزینه ارسال",
    )

    subtotal = models.DecimalField(
        max_digits=14, decimal_places=0,
        default=0, verbose_name="جمع کل قبل تخفیف"
    )
    total_discount = models.DecimalField(
        max_digits=14, decimal_places=0,
        default=0, verbose_name="جمع تخفیف"
    )
    total = models.DecimalField(
        max_digits=14, decimal_places=0,
        default=0, verbose_name="مبلغ نهایی"
    )

    payment_ref = models.CharField(
        max_length=120, blank=True, null=True,
        verbose_name="کد مرجع پرداخت"
    )
    payment_gateway = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name="درگاه پرداخت"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ پرداخت")

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"

    def __str__(self) -> str:
        return f"Order#{self.id} - {self.payment_status}"

    @property
    def is_paid(self) -> bool:
        return self.payment_status == self.PaymentStatus.PAID

    def mark_paid(self, *, ref: str | None = None, gateway: str | None = None):
        self.payment_status = self.PaymentStatus.PAID
        if ref:
            self.payment_ref = ref
        if gateway:
            self.payment_gateway = gateway
        self.paid_at = timezone.now()
        self.save(update_fields=["payment_status", "payment_ref", "payment_gateway", "paid_at"])


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, related_name="items",
        on_delete=models.CASCADE,
        verbose_name="سفارش"
    )

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT,
        verbose_name="محصول"
    )
    variant = models.ForeignKey(
        ProductVariant, null=True, blank=True,
        on_delete=models.PROTECT,
        verbose_name="واریانت"
    )

    qty = models.PositiveIntegerField(default=1, verbose_name="تعداد")

    unit_price = models.DecimalField(
        max_digits=14, decimal_places=0,
        default=0, verbose_name="قیمت واحد"
    )
    discount = models.DecimalField(
        max_digits=14, decimal_places=0,
        default=0, verbose_name="تخفیف ردیف"
    )
    total = models.DecimalField(
        max_digits=14, decimal_places=0,
        default=0, verbose_name="جمع ردیف"
    )

    product_name = models.CharField(
        max_length=255, blank=True,
        verbose_name="نام محصول (اسنپ‌شات)"
    )

    class Meta:
        verbose_name = "آیتم سفارش"
        verbose_name_plural = "آیتم‌های سفارش"

    def save(self, *args, **kwargs):
        if not self.product_name:
            self.product_name = self.product.name

        if not self.total:
            self.total = (Decimal(self.unit_price) * self.qty) - Decimal(self.discount)

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.product_name} x{self.qty}"


class OrderDraft(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="order_drafts",
        verbose_name="کاربر",
    )
    session_key = models.CharField(max_length=120, blank=True)

    address = models.ForeignKey(
        Address,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name="آدرس انتخاب‌شده",
    )
    shipping_method = models.ForeignKey(
        ShippingMethod,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name="روش ارسال",
    )

    shipping_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=0, verbose_name="هزینه ارسال"
    )
    cart_total = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=0, verbose_name="جمع سبد"
    )
    payable_total = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=0, verbose_name="مبلغ پرداختی"
    )

    step = models.CharField(
        max_length=20,
        default="address",  # address → shipping → review
        verbose_name="مرحله چک‌اوت",
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین تغییر")

    class Meta:
        verbose_name = "پیش‌نویس سفارش"
        verbose_name_plural = "پیش‌نویس‌های سفارش"

    def __str__(self):
        return f"Draft #{self.id} for {self.user}"
