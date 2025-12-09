# orders/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseBadRequest
from cart.cart import Cart
from .services.zarinpal import ZarinpalClient
from .models import Order
from django.urls import reverse
# برای پاک کردن سشن‌های چک‌اوت
from checkout.views import (
    SESSION_KEY_ADDR,
    SESSION_KEY_SHIPPING,
    SESSION_KEY_RECEIVER,
)
from django.views.decorators.http import require_POST
from products.services.inventory import consume_stock_for_cart

@login_required
def payment_start(request, order_id):
    """
    شروع پرداخت زرین‌پال:
      - گرفتن مبلغ از Order
      - ارسال درخواست به زرین‌پال
      - ذخیره authority در order.payment_ref
      - ریدایرکت به صفحه پرداخت
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.is_paid:
        messages.info(request, "این سفارش قبلاً پرداخت شده است.")
        return redirect("orders:payment_success", order_id=order.id)

    zp = ZarinpalClient()

    callback_url = request.build_absolute_uri(
        reverse("orders:payment_callback")
    )

    user = request.user
    mobile = getattr(user, "phone", None)
    email = getattr(user, "email", None)

    resp = zp.request_payment(
        amount=order.total,
        callback_url=callback_url,
        description=f"پرداخت سفارش #{order.id}",
        mobile=mobile,
        email=email,
    )

    if not resp["ok"]:
        messages.error(request, f"خطا در اتصال به درگاه: {resp.get('error')}")
        order.payment_status = Order.PaymentStatus.FAILED
        order.save(update_fields=["payment_status"])
        return redirect("checkout:review")

    # ذخیره authority در سفارش
    order.payment_ref = resp["authority"]
    order.payment_gateway = "zarinpal"
    order.save(update_fields=["payment_ref", "payment_gateway"])

    return redirect(resp["pay_url"])


@login_required
def payment_callback(request):
    """
    Callback زرین‌پال بعد از پرداخت.
    """
    authority = request.GET.get("Authority")
    status = request.GET.get("Status")

    if not authority:
        return HttpResponseBadRequest("Authority missing")

    order = get_object_or_404(Order, payment_ref=authority, user=request.user)

    # کاربر در درگاه Cancel زده
    if status != "OK":
        order.payment_status = Order.PaymentStatus.FAILED
        order.save(update_fields=["payment_status"])
        messages.warning(request, "پرداخت توسط کاربر لغو شد.")
        return redirect("orders:payment_failed", order_id=order.id)

    zp = ZarinpalClient()
    verify = zp.verify_payment(authority=authority, amount=order.total)

    if verify["ok"]:
        # اگر قبلاً paid نشده (اینجا is_paid فقط property هست)
        if not order.is_paid:
            cart = Cart(request)

            # ۱) اول کم کردن موجودی از روی سبد
            try:
                consume_stock_for_cart(cart)
            except ValueError as e:
                order.payment_status = Order.PaymentStatus.FAILED
                order.save(update_fields=["payment_status"])
                messages.error(request, f"مشکلی در موجودی کالاها پیش آمد: {e}")
                return redirect("orders:payment_failed", order_id=order.id)

            # ۲) حالا وضعیت سفارش را PAID کن
            order.payment_status = Order.PaymentStatus.PAID
            order.paid_at = timezone.now()
            order.payment_ref = str(verify["ref_id"])
            order.payment_gateway = "zarinpal"
            order.save(update_fields=[
                "payment_status",
                "paid_at",
                "payment_ref",
                "payment_gateway",
            ])

            # ۳) خالی کردن سبد
            cart.clear()

            # ۴) پاک کردن سشن‌های checkout
            for k in (SESSION_KEY_ADDR, SESSION_KEY_SHIPPING, SESSION_KEY_RECEIVER):
                request.session.pop(k, None)

        # اگر از قبل paid بود، فقط برو صفحه موفقیت
        return redirect("orders:payment_success", order_id=order.id)

    # verify ناموفق
    order.payment_status = Order.PaymentStatus.FAILED
    order.save(update_fields=["payment_status"])
    messages.error(request, f"تأیید پرداخت ناموفق بود (کد {verify.get('code')}).")
    return redirect("orders:payment_failed", order_id=order.id)




# @login_required
# def payment_callback(request):
#     """
#     Callback زرین‌پال بعد از پرداخت.
#     """
#     authority = request.GET.get("Authority")
#     status = request.GET.get("Status")
#
#     if not authority:
#         return HttpResponseBadRequest("Authority missing")
#
#     order = get_object_or_404(Order, payment_ref=authority, user=request.user)
#
#     # کاربر در درگاه Cancel زده
#     if status != "OK":
#         order.payment_status = Order.PaymentStatus.FAILED
#         order.save(update_fields=["payment_status"])
#         messages.warning(request, "پرداخت توسط کاربر لغو شد.")
#         return redirect("orders:payment_failed", order_id=order.id)
#
#     zp = ZarinpalClient()
#     verify = zp.verify_payment(authority=authority, amount=order.total)
#
#     if verify["ok"]:
#         # اگر قبلاً paid نشده
#         if not order.is_paid:
#             order.payment_status = Order.PaymentStatus.PAID
#             order.paid_at = timezone.now()
#             order.payment_ref = str(verify["ref_id"])
#             order.payment_gateway = "zarinpal"
#             order.save(update_fields=["payment_status", "paid_at", "payment_ref", "payment_gateway"])
#
#             # خالی کردن cart
#             Cart(request).clear()
#             # پاک کردن سشن‌های checkout
#             for k in (SESSION_KEY_ADDR, SESSION_KEY_SHIPPING, SESSION_KEY_RECEIVER):
#                 request.session.pop(k, None)
#
#         return redirect("orders:payment_success", order_id=order.id)
#
#     # verify ناموفق
#     order.payment_status = Order.PaymentStatus.FAILED
#     order.save(update_fields=["payment_status"])
#     messages.error(request, f"تأیید پرداخت ناموفق بود (کد {verify.get('code')}).")
#     return redirect("orders:payment_failed", order_id=order.id)


@login_required
def payment_success(request, order_id):
    """
    صفحه نمایش پرداخت موفق
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "orders/payment_success.html", {"order": order})


@login_required
def payment_failed(request, order_id):
    """
    صفحه نمایش پرداخت ناموفق
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "orders/payment_failed.html", {"order": order})


# @require_POST
# def payment_verify(request):
#     # ۱) این‌جا جواب درگاه رو چک می‌کنی و مطمئن می‌شی پرداخت موفق بوده
#     #    مثلا:
#     #    success, ref_id, gateway_resp = verify_with_gateway(request)
#     #    if not success:  ...  (هندل خطا)
#
#     # ۲) ساخت سفارش (Order) و آیتم‌ها (OrderItem) از روی سبد
#     cart = Cart(request)
#     # order = create_order_from_cart(request.user, cart, ref_id=ref_id, ...)
#
#     # ۳) فقط یک‌بار، در لحظه‌ای که سفارش رو «paid» می‌کنی، موجودی را کم کن
#     try:
#         consume_stock_for_cart(cart)
#     except ValueError as e:
#         # اگر جایی موجودی کافی نبود، می‌تونی سفارش رو failed کنی
#         # یا پیام مناسب نشون بدی. فعلاً ساده:
#         messages.error(request, f"مشکلی در موجودی کالاها پیش آمد: {e}")
#         # این‌جا بسته به استراتژی خودت، ممکنه redirect کنی به سبد:
#         return redirect("cart:cart_detail")
#
#     # ۴) حالا که موجودی کم شد، سبد را خالی کن
#     cart.clear()  # همین متدی که الان در Cart داری
#
#     messages.success(request, "پرداخت با موفقیت انجام شد و سفارش ثبت گردید.")
#     return redirect("orders:success_page")  # یا هر URL موفقیت خودت
