# orders/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from django.utils import timezone

import jdatetime

from .models import Order, OrderItem


# ---------------- Inlines ----------------

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    autocomplete_fields = ("product", "variant")
    readonly_fields = ("product_name", "unit_price", "discount", "total")
    fields = ("product", "variant", "product_name", "qty", "unit_price", "discount", "total")
    show_change_link = True


# ---------------- Order Admin ----------------

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    inlines = [OrderItemInline]

    list_display = (
        "id",
        "user_display",
        "payment_status_badge",
        "fulfillment_status_badge",
        "items_count",
        "subtotal_display",
        "discount_display",
        "total_display",
        "created_at_jalali",   # ✅ نمایش جلالی در لیست
    )

    # ⚠️ list_filter فقط باید Field واقعی یا Filter کلاس باشد
    list_filter = ("payment_status", "fulfillment_status", "created_at")

    search_fields = ("id", "user__phone", "user__email", "payment_ref")

    # این‌ها readonly هستند (فیلد اصلی + نمایش جلالی)
    readonly_fields = (
        "created_at",
        "created_at_jalali",
        "paid_at",
        "paid_at_jalali",
        "subtotal",
        "total_discount",
        "total",
        "items_count",
        "items_preview",
    )

    fieldsets = (
        ("اطلاعات اصلی", {"fields": ("user", "address", "created_at_jalali")}),
        ("مبالغ", {"fields": ("subtotal", "total_discount", "total")}),
        ("پرداخت", {"fields": ("payment_gateway", "payment_ref", "paid_at_jalali")}),
        ("وضعیت‌ها", {"fields": ("payment_status", "fulfillment_status")}),
        ("خلاصه آیتم‌ها", {"fields": ("items_count", "items_preview")}),
    )

    actions = (
        "make_paid",
        "make_failed",
        "make_processing",
        "make_shipped",
        "make_delivered",
        "make_canceled",
        "make_send_canceled",
    )

    # ---------- Jalali displays ----------

    @admin.display(description="تاریخ ثبت", ordering="created_at")
    def created_at_jalali(self, obj: Order):
        if not obj.created_at:
            return "—"
        dt = timezone.localtime(obj.created_at)
        return jdatetime.datetime.fromgregorian(datetime=dt).strftime("%Y/%m/%d %H:%M")

    @admin.display(description="زمان پرداخت", ordering="paid_at")
    def paid_at_jalali(self, obj: Order):
        if not obj.paid_at:
            return "—"
        dt = timezone.localtime(obj.paid_at)
        return jdatetime.datetime.fromgregorian(datetime=dt).strftime("%Y/%m/%d %H:%M")

    # ---------- Pretty displays ----------

    @admin.display(description="کاربر")
    def user_display(self, obj: Order):
        if not obj.user:
            return "—"
        full = obj.user.get_full_name()
        return full or obj.user.phone or obj.user.email or "—"

    @admin.display(description="وضعیت پرداخت", ordering="payment_status")
    def payment_status_badge(self, obj: Order):
        status = obj.payment_status
        label = obj.get_payment_status_display()

        color_map = {
            Order.PaymentStatus.PENDING: "#f0ad4e",
            Order.PaymentStatus.PAID: "#5cb85c",
            Order.PaymentStatus.FAILED: "#d9534f",
            Order.PaymentStatus.CANCELED: "#777777",
            Order.PaymentStatus.REFUNDED: "#5bc0de",
        }
        color = color_map.get(status, "#999")

        return format_html(
            '<span style="padding:4px 8px;border-radius:999px;background:{};'
            'color:#fff;font-weight:700;font-size:12px;">{}</span>',
            color, label
        )

    @admin.display(description="وضعیت ارسال", ordering="fulfillment_status")
    def fulfillment_status_badge(self, obj: Order):
        status = obj.fulfillment_status
        label = obj.get_fulfillment_status_display()

        color_map = {
            Order.FulfillmentStatus.NEW: "#6c757d",
            Order.FulfillmentStatus.PROCESSING: "#0d6efd",
            Order.FulfillmentStatus.SHIPPED: "#6610f2",
            Order.FulfillmentStatus.DELIVERED: "#198754",
            Order.FulfillmentStatus.RETURNED: "#dc3545",
            Order.FulfillmentStatus.SEND_CANCELED: "#fd7e14",
        }
        color = color_map.get(status, "#999")

        return format_html(
            '<span style="padding:4px 8px;border-radius:999px;background:{};'
            'color:#fff;font-weight:700;font-size:12px;">{}</span>',
            color, label
        )

    @admin.display(description="تعداد آیتم‌ها")
    def items_count(self, obj: Order):
        return obj.items.aggregate(c=Sum("qty"))["c"] or 0

    @admin.display(description="پیش‌نمایش آیتم‌ها")
    def items_preview(self, obj: Order):
        items = obj.items.all()[:6]
        lines = [f"{it.product_name} × {it.qty}" for it in items]
        more = obj.items.count() - len(lines)
        if more > 0:
            lines.append(f"… و {more} آیتم دیگر")
        return " | ".join(lines) or "—"

    @admin.display(description="جمع کل")
    def subtotal_display(self, obj: Order):
        return f"{int(obj.subtotal):,} تومان"

    @admin.display(description="تخفیف")
    def discount_display(self, obj: Order):
        return f"{int(obj.total_discount):,} تومان"

    @admin.display(description="مبلغ نهایی")
    def total_display(self, obj: Order):
        return f"{int(obj.total):,} تومان"

    # ---------- Actions ----------

    @admin.action(description="تغییر به پرداخت شده")
    def make_paid(self, _request, queryset):
        queryset.update(payment_status=Order.PaymentStatus.PAID)

    @admin.action(description="تغییر به پرداخت ناموفق")
    def make_failed(self, _request, queryset):
        queryset.update(payment_status=Order.PaymentStatus.FAILED)

    @admin.action(description="تغییر به در حال آماده‌سازی")
    def make_processing(self, _request, queryset):
        queryset.update(fulfillment_status=Order.FulfillmentStatus.PROCESSING)

    @admin.action(description="تغییر به ارسال شده")
    def make_shipped(self, _request, queryset):
        queryset.update(fulfillment_status=Order.FulfillmentStatus.SHIPPED)

    @admin.action(description="تغییر به تحویل شده")
    def make_delivered(self, _request, queryset):
        queryset.update(fulfillment_status=Order.FulfillmentStatus.DELIVERED)

    @admin.action(description="تغییر به لغو شده")
    def make_canceled(self, _request, queryset):
        queryset.update(payment_status=Order.PaymentStatus.CANCELED)

    @admin.action(description="تغییر به لغو ارسال")
    def make_send_canceled(self, _request, queryset):
        queryset.update(fulfillment_status=Order.FulfillmentStatus.SEND_CANCELED)


# ---------------- OrderItem Admin ----------------

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product_name", "qty", "unit_price", "discount", "total")
    search_fields = ("order__id", "product_name", "product__name")
    list_filter = ("order__payment_status",)
    readonly_fields = ("product_name", "total")
