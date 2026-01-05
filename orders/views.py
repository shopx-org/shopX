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
    SESSION_KEY_PENDING_ORDER,
)
from django.views.decorators.http import require_POST
from products.services.inventory import consume_stock_for_cart



# orders/views.py
from django.db import transaction
from django.views.decorators.http import require_GET  # اگر فعلاً GET نگه می‌داری

@login_required
@require_GET
def payment_start(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.is_paid:
        messages.info(request, "این سفارش قبلاً پرداخت شده است.")
        return redirect("orders:payment_success", order_id=order.id)

    zp = ZarinpalClient()
    callback_url = request.build_absolute_uri(reverse("orders:payment_callback"))

    user = request.user
    mobile = getattr(user, "phone", None)
    email = getattr(user, "email", None)

    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order.id)

        # ✅ اگر قبلاً authority داریم و هنوز پرداخت نشده → reuse
        if order.payment_status == Order.PaymentStatus.PENDING and order.payment_ref:
            return redirect(zp.startpay_url + order.payment_ref)

        resp = zp.request_payment(
            amount=order.total,
            callback_url=callback_url,
            description=f"پرداخت سفارش #{order.id}",
            mobile=mobile,
            email=email,
        )

        if not resp["ok"]:
            messages.error(request, f"خطا در اتصال به درگاه: {resp.get('error')}")
            # order.payment_status = Order.PaymentStatus.FAILED
            # order.save(update_fields=["payment_status"])
            print("ZP REQUEST FAIL:", resp)
            return redirect("checkout:review")

        order.payment_ref = resp["authority"]
        order.payment_gateway = "zarinpal"
        order.payment_status = Order.PaymentStatus.PENDING
        order.save(update_fields=["payment_ref", "payment_gateway", "payment_status"])

    return redirect(resp["pay_url"])





#
# @login_required
# def payment_start(request, order_id):
#     """
#     شروع پرداخت زرین‌پال:
#       - گرفتن مبلغ از Order
#       - ارسال درخواست به زرین‌پال
#       - ذخیره authority در order.payment_ref
#       - ریدایرکت به صفحه پرداخت
#     """
#     order = get_object_or_404(Order, id=order_id, user=request.user)
#
#     if order.is_paid:
#         messages.info(request, "این سفارش قبلاً پرداخت شده است.")
#         return redirect("orders:payment_success", order_id=order.id)
#
#     zp = ZarinpalClient()
#
#     callback_url = request.build_absolute_uri(
#         reverse("orders:payment_callback")
#     )
#
#     user = request.user
#     mobile = getattr(user, "phone", None)
#     email = getattr(user, "email", None)
#
#     resp = zp.request_payment(
#         amount=order.total,
#         callback_url=callback_url,
#         description=f"پرداخت سفارش #{order.id}",
#         mobile=mobile,
#         email=email,
#     )
#
#     if not resp["ok"]:
#         messages.error(request, f"خطا در اتصال به درگاه: {resp.get('error')}")
#         order.payment_status = Order.PaymentStatus.FAILED
#         order.save(update_fields=["payment_status"])
#         return redirect("checkout:review")
#
#     # ذخیره authority در سفارش
#     order.payment_ref = resp["authority"]
#     order.payment_gateway = "zarinpal"
#     order.save(update_fields=["payment_ref", "payment_gateway"])
#
#     return redirect(resp["pay_url"])


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
#     if status != "OK":
#         order.payment_status = Order.PaymentStatus.FAILED
#         order.save(update_fields=["payment_status"])
#
#         request.session["pay_error_message"] = "پرداخت توسط کاربر لغو شد."
#         request.session["pay_error_code"] = None
#
#     # # کاربر در درگاه Cancel زده
#     # if status != "OK":
#     #     order.payment_status = Order.PaymentStatus.FAILED
#     #     order.save(update_fields=["payment_status"])
#     #     messages.warning(request, "پرداخت توسط کاربر لغو شد.")
#     #     return redirect("orders:payment_failed", order_id=order.id)
#
#     zp = ZarinpalClient()
#     verify = zp.verify_payment(authority=authority, amount=order.total)
#
#     if verify["ok"]:
#         # اگر قبلاً paid نشده (اینجا is_paid فقط property هست)
#         if not order.is_paid:
#             cart = Cart(request)
#
#             # ۱) اول کم کردن موجودی از روی سبد
#             try:
#                 consume_stock_for_cart(cart)
#             except ValueError as e:
#                 order.payment_status = Order.PaymentStatus.FAILED
#                 order.save(update_fields=["payment_status"])
#                 messages.error(request, f"مشکلی در موجودی کالاها پیش آمد: {e}")
#                 return redirect("orders:payment_failed", order_id=order.id)
#
#             # ۲) حالا وضعیت سفارش را PAID کن
#             order.payment_status = Order.PaymentStatus.PAID
#             order.paid_at = timezone.now()
#             order.payment_ref = str(verify["ref_id"])
#             order.payment_gateway = "zarinpal"
#             order.save(update_fields=[
#                 "payment_status",
#                 "paid_at",
#                 "payment_ref",
#                 "payment_gateway",
#             ])
#
#             # ۳) خالی کردن سبد
#             cart.clear()
#
#             # ۴) پاک کردن سشن‌های checkout
#             for k in (SESSION_KEY_ADDR, SESSION_KEY_SHIPPING, SESSION_KEY_RECEIVER):
#                 request.session.pop(k, None)
#
#         # اگر از قبل paid بود، فقط برو صفحه موفقیت
#         return redirect("orders:payment_success", order_id=order.id)
#
#     # verify ناموفق
#     order.payment_status = Order.PaymentStatus.FAILED
#     order.save(update_fields=["payment_status"])
#     messages.error(request, f"تأیید پرداخت ناموفق بود (کد {verify.get('code')}).")
#
#     return redirect("orders:payment_failed", order_id=order.id)
#



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
def payment_callback(request):
    """
    Callback زرین‌پال بعد از پرداخت.

    - Status != OK  => پرداخت لغو/ناموفق (بدون verify)
    - Status == OK  => verify انجام می‌شود
    - پیام خطا/کد خطا از طریق session به payment_failed منتقل می‌شود
    - در حالت FAIL، SESSION_KEY_PENDING_ORDER پاک می‌شود تا کاربر مجبور نشود سبد را خالی کند
    """
    authority = request.GET.get("Authority")
    status = (request.GET.get("Status") or "").upper()

    if not authority:
        return HttpResponseBadRequest("Authority missing")

    # ✅ حالت معمول: order با authority پیدا می‌شود
    # ⚠️ اگر قبلاً payment_ref را با ref_id جایگزین کرده باشی، ممکن است این خط Order را پیدا نکند.
    # در نسخه ایده‌آل باید فیلد جدا برای authority داشته باشی.
    try:
        order = Order.objects.get(payment_ref=authority, user=request.user)
    except Order.DoesNotExist:
        # fallback: اگر کاربر صفحه callback را refresh کند و payment_ref تبدیل به ref_id شده باشد
        # از session pending order کمک می‌گیریم (اگر موجود باشد)
        pending_id = request.session.get(SESSION_KEY_PENDING_ORDER)
        if not pending_id:
            return HttpResponseBadRequest("Order not found for this authority")
        order = get_object_or_404(Order, id=pending_id, user=request.user)

    # Helper برای Fail خروجی یکپارچه
    def _fail(message: str, code=None):
        order.payment_status = Order.PaymentStatus.FAILED
        order.save(update_fields=["payment_status"])

        request.session["pay_error_message"] = message
        request.session["pay_error_code"] = code

        # ✅ خیلی مهم: اجازه بده کاربر بدون خالی کردن سبد، دوباره مسیر پرداخت را طی کند
        request.session.pop(SESSION_KEY_PENDING_ORDER, None)

        return redirect("orders:payment_failed", order_id=order.id)

    # 1) کاربر در درگاه Cancel زده یا Status OK نیست => مستقیم fail
    if status != "OK":
        return _fail("پرداخت توسط کاربر لغو شد یا تکمیل نشد.", None)

    # 2) اگر سفارش قبلاً paid شده => دوباره verify/stock نزن
    if order.is_paid:
        return redirect("orders:payment_success", order_id=order.id)

    # 3) verify در زرین‌پال
    zp = ZarinpalClient()
    verify = zp.verify_payment(authority=authority, amount=order.total) or {}

    if verify.get("ok"):
        cart = Cart(request)

        # 3-1) مصرف موجودی (قبل از PAID شدن سفارش)
        try:
            consume_stock_for_cart(cart)
        except ValueError as e:
            return _fail(f"مشکلی در موجودی کالاها پیش آمد: {e}", None)

        # 3-2) ثبت پرداخت موفق
        order.payment_status = Order.PaymentStatus.PAID
        order.paid_at = timezone.now()
        order.payment_gateway = "zarinpal"

        # ⚠️ توصیه: ref_id را در فیلد جدا ذخیره کن.
        # فعلاً طبق ساختار فعلی تو:
        ref_id = verify.get("ref_id")
        if ref_id is not None:
            order.payment_ref = str(ref_id)

        order.save(update_fields=["payment_status", "paid_at", "payment_ref", "payment_gateway"])

        # 3-3) خالی کردن سبد (فقط روی موفقیت)
        cart.clear()

        # 3-4) پاک کردن سشن‌های checkout (فقط روی موفقیت)
        for k in (SESSION_KEY_ADDR, SESSION_KEY_SHIPPING, SESSION_KEY_RECEIVER, SESSION_KEY_PENDING_ORDER):
            request.session.pop(k, None)

        return redirect("orders:payment_success", order_id=order.id)

    # 4) verify ناموفق => fail با پیام مناسب
    code = verify.get("code")

    if code == -12:
        msg = "تعداد تلاش برای پرداخت زیاد بوده. لطفاً ۳۰ تا ۶۰ ثانیه بعد دوباره امتحان کنید."
    elif code is None:
        msg = "تأیید پرداخت ناموفق بود. لطفاً دوباره تلاش کنید."
    else:
        msg = f"تأیید پرداخت ناموفق بود (کد {code})."

    return _fail(msg, code)


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

    error_message = request.session.pop("pay_error_message", None)
    error_code = request.session.pop("pay_error_code", None)

    return render(request, "orders/payment_failed.html", {
        "order": order,
        "error_message": error_message,
        "error_code": error_code,
    })


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
