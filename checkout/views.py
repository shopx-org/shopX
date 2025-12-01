# checkout/views.py
from __future__ import annotations
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional, Tuple
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from cart.cart import Cart
from promos.services.pricing import PricingEngine
from products.services.pricing_adapter import (
    build_pricing_line_public,
    build_service_line_public,
    build_ephemeral_campaigns_for_lines,
)
from shipping.models import Address
from shipping.forms import AddressForm


# =========================
# constants
# =========================
SESSION_KEY_ADDR = "checkout.address_id"
SESSION_KEY_SHIPPING = "checkout.shipping_method"
SESSION_KEY_RECEIVER = "checkout.receiver"


# =========================
# forms
# =========================
class ReceiverForm(forms.Form):
    first_name = forms.CharField(label="نام", max_length=50)
    last_name = forms.CharField(label="نام خانوادگی", max_length=50)
    email = forms.EmailField(label="ایمیل", required=False)
    national_id = forms.CharField(label="کد ملی", max_length=10, required=False)
    gender = forms.ChoiceField(
        label="جنسیت",
        required=False,
        choices=[("female", "خانم"), ("male", "آقا")],
        widget=forms.RadioSelect,
    )


# =========================
# helpers (messages)
# =========================
def _split_messages(request: HttpRequest):
    """
    پیام‌های Django را بر اساس extra_tags جدا می‌کند:
    - addr      → مخصوص باکس آدرس‌ها
    - receiver  → مخصوص باکس مشخصات گیرنده
    - other     → پیام‌های عمومی
    """
    storage = get_messages(request)
    addr_msgs, receiver_msgs, other_msgs = [], [], []

    for m in storage:
        if "addr" in m.tags:
            addr_msgs.append(m)
        elif "receiver" in m.tags:
            receiver_msgs.append(m)
        else:
            other_msgs.append(m)

    return addr_msgs, receiver_msgs, other_msgs


# =========================
# helpers (cart/pricing)
# =========================
def _require_nonempty_cart(cart: Cart) -> bool:
    """آیا سبد خالی نیست؟"""
    try:
        return sum(int(getattr(it, "qty", 1)) for it in cart.items()) > 0
    except Exception:
        return False


def _build_lines_with_gids(cart: Cart) -> Tuple[List[Any], List[Tuple[str, SimpleNamespace]]]:
    """
    خطوط پرایسینگ را از آیتم‌های سبد بساز + برای هر ردیف gid بده.
    """
    items: Iterable[SimpleNamespace] = list(cart.items())
    lines: List[Any] = []
    groups: List[Tuple[str, SimpleNamespace]] = []

    for idx, it in enumerate(items):
        gid = f"g{idx}"

        base = build_pricing_line_public(it.variant or it.product, it.qty)
        if getattr(it, "unit_price", None) is not None:
            base.unit_price = Decimal(str(it.unit_price))
            base.line_subtotal = base.unit_price * base.quantity


        setattr(base, "_cart_gid", gid)
        lines.append(base)

        for svc in (getattr(it, "services", []) or []):
            svc_line = build_service_line_public(
                service=svc,
                base_line=base,
                item_unit_price=base.unit_price,
                qty=it.qty,
            )
            setattr(svc_line, "_cart_gid", gid)
            lines.append(svc_line)

        groups.append((gid, it))

    return lines, groups


def _pricing_ctx_for(cart: Cart, channel: str = "web") -> Dict[str, Any]:
    """
    کانتکست ورودی PricingEngine:
    - channel
    - coupons از روی سشن کارت (cart.coupon)
    """
    ctx: Dict[str, Any] = {"channel": channel}
    cp = cart.get_coupon()
    if cp:
        ctx["coupons"] = [cp]
    return ctx


def _evaluate_cart(cart: Cart, channel: str = "web"):
    """
    یک نقطه‌ی واحد برای پرایسینگ سبد:
    - lines + gids
    - ephemeral campaigns
    - coupon
    """
    lines, groups = _build_lines_with_gids(cart)
    ctx = _pricing_ctx_for(cart, channel=channel)

    epis = build_ephemeral_campaigns_for_lines(lines, channel=ctx.get("channel", "web"))
    if epis:
        ctx["ephemeral_campaigns"] = epis

    result = PricingEngine().evaluate(lines, ctx)
    return result, lines, groups


def _summary_from_result(result) -> Dict[str, Decimal]:
    """
    خروجی سایدبار - هم‌منطق با cart/views.py
    total = (subtotal_exclusive - total_discount) + services_total
    """
    lines = getattr(result, "lines", []) or []

    sub_exclusive = Decimal("0")
    svc_total = Decimal("0")
    line_disc = Decimal("0")

    for ln in lines:
        if getattr(ln, "_exclude_from_discounts", False):
            svc_total += getattr(ln, "line_subtotal", Decimal("0"))
        else:
            sub_exclusive += getattr(ln, "line_subtotal", Decimal("0"))
        line_disc += getattr(ln, "line_discount", Decimal("0"))

    cart_disc = getattr(result, "cart_discount", Decimal("0"))

    total_discount = (line_disc + cart_disc)
    total = (sub_exclusive - total_discount) + svc_total

    return {
        "subtotal": sub_exclusive,
        "services_total": svc_total,
        "total_discount": total_discount,
        "total": total,
    }


def _cart_summary_ctx(cart: Cart, channel: str = "web") -> Dict[str, Any]:
    """
    خلاصه‌ی سبد برای سایدبار چک‌اوت (address/review)
    """
    result, *_ = _evaluate_cart(cart, channel=channel)
    summary = _summary_from_result(result)

    return {
        "cart_subtotal": summary["subtotal"],
        "cart_total_discount": summary["total_discount"],
        "cart_total": summary["total"],
        "cart_services_total": summary["services_total"],
        "cart_coupon": cart.get_coupon() or "",
    }


def _get_user_phone(user) -> str:
    return (
        getattr(user, "phone_number", None)
        or getattr(user, "mobile", None)
        or getattr(user, "phone", None)
        or ""
    )


# =========================
# flow views
# =========================
def checkout_start(request: HttpRequest) -> HttpResponse:
    """
    دروازه ورود چک‌اوت
    """
    cart = Cart(request)
    if not _require_nonempty_cart(cart):
        messages.info(request, "سبد خرید شما خالی است.")
        return redirect("cart:cart_detail")

    if not request.user.is_authenticated:
        login_url = reverse("account:otp_login")
        next_url = reverse("checkout:address")
        return redirect(f"{login_url}?next={next_url}")

    return redirect("checkout:address")


@login_required
def checkout_address(request: HttpRequest) -> HttpResponse:
    """
    مرحله 1:
      - مدیریت آدرس‌ها (add/update/delete/select)
      - ثبت مشخصات گیرنده + روش ارسال
      - سایدبار خلاصه سبد
    """
    cart = Cart(request)
    if not _require_nonempty_cart(cart):
        messages.info(request, "سبد خرید شما خالی است.")
        return redirect("cart:cart_detail")

    user = request.user
    phone = _get_user_phone(user)

    addresses_qs = Address.objects.filter(user=user).order_by(
        "-is_default", "-updated_at", "-id"
    )

    receiver_initial = request.session.get(SESSION_KEY_RECEIVER) or {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": getattr(user, "email", ""),
    }

    def _render(form: AddressForm, receiver_form: ReceiverForm):
        ctx = {
            "addresses": list(addresses_qs),
            "form": form,
            "receiver_form": receiver_form,
            "post_url": reverse("checkout:address"),
            "select_mode": 1,
            "selected_id": request.session.get(SESSION_KEY_ADDR) or "",
            "allow_add": True,
            "phone": phone,
        }
        ctx.update(_cart_summary_ctx(cart))
        addr_msgs, receiver_msgs, other_msgs = _split_messages(request)
        ctx["addr_messages"] = addr_msgs
        ctx["receiver_messages"] = receiver_msgs
        ctx["other_messages"] = other_msgs
        return render(request, "checkout/address.html", ctx)

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip().lower()

        # ---------- add / update address ----------
        if action in {"add", "update"}:
            addr_id = request.POST.get("address_id")
            instance = addresses_qs.filter(pk=addr_id).first() if addr_id else None

            address_form = AddressForm(request.POST, instance=instance)
            receiver_form = ReceiverForm(initial=receiver_initial)

            if address_form.is_valid():
                addr = address_form.save(user=user)
                messages.success(request, "آدرس ذخیره شد.", extra_tags="addr")
                request.session[SESSION_KEY_ADDR] = addr.id
                return redirect("checkout:address")

            return _render(address_form, receiver_form)

        # ---------- delete address ----------
        if action == "delete":
            addr_id = request.POST.get("address_id")
            if addr_id:
                addresses_qs.filter(pk=addr_id).delete()
                if request.session.get(SESSION_KEY_ADDR) == int(addr_id):
                    request.session.pop(SESSION_KEY_ADDR, None)
                messages.info(request, "آدرس حذف شد.", extra_tags="addr")
            return redirect("checkout:address")

        # ---------- select address ----------
        if action == "select":
            addr_id = request.POST.get("address_id")
            if not addr_id:
                default = addresses_qs.filter(is_default=True).first() or addresses_qs.first()
                if not default:
                    messages.error(request, "برای ادامه حداقل یک آدرس ثبت کنید.")
                    return redirect("checkout:address")
                addr_id_int = default.id
            else:
                try:
                    addr_id_int = int(addr_id)
                except Exception:
                    addr_id_int = 0

                if not addresses_qs.filter(pk=addr_id_int).exists():
                    messages.error(request, "آدرس انتخاب‌شده معتبر نیست.", extra_tags="addr")
                    return redirect("checkout:address")

            request.session[SESSION_KEY_ADDR] = addr_id_int
            return redirect("checkout:address")

        # ---------- receiver form ----------
        if action == "receiver":
            address_form = AddressForm()
            receiver_form = ReceiverForm(request.POST)

            if receiver_form.is_valid():
                request.session[SESSION_KEY_RECEIVER] = receiver_form.cleaned_data
                ship_method = request.POST.get("shipping_method") or "tipax"
                request.session[SESSION_KEY_SHIPPING] = ship_method

                # مطمئن شو آدرس انتخاب شده
                if not request.session.get(SESSION_KEY_ADDR):
                    default = addresses_qs.filter(is_default=True).first() or addresses_qs.first()
                    if not default:
                        messages.error(
                            request,
                            "لطفاً ابتدا آدرس ارسال را ثبت و انتخاب کنید.",
                            extra_tags="receiver",
                        )
                        return redirect("checkout:address")
                    request.session[SESSION_KEY_ADDR] = default.id

                return redirect("checkout:review")

            return _render(address_form, receiver_form)

        # action ناشناخته
        return redirect("checkout:address")

    # ---------- GET ----------
    address_form = AddressForm()
    receiver_form = ReceiverForm(initial=receiver_initial)
    return _render(address_form, receiver_form)


@login_required
def checkout_review(request: HttpRequest) -> HttpResponse:
    """
    مرحله 2: مرور سفارش
      - آدرس + گیرنده
      - آیتم‌ها و تخفیف ردیفی
      - سایدبار (جمع‌ها + کوپن)
    """
    cart = Cart(request)
    if not _require_nonempty_cart(cart):
        messages.info(request, "سبد خرید شما خالی است.")
        return redirect("cart:cart_detail")

    addr_id = request.session.get(SESSION_KEY_ADDR)
    if not addr_id:
        messages.warning(request, "لطفاً ابتدا آدرس ارسال را انتخاب کنید.")
        return redirect("checkout:address")

    address = Address.objects.filter(user=request.user, pk=addr_id).first()
    if not address:
        messages.error(request, "آدرس انتخاب‌شده یافت نشد.")
        return redirect("checkout:address")

    receiver_data = request.session.get(SESSION_KEY_RECEIVER, {}) or {}
    phone = _get_user_phone(request.user)

    shipping_method = request.session.get(SESSION_KEY_SHIPPING, "tipax")
    shipping_method_display = "ارسال پستی" if shipping_method == "post" else "ارسال تیپاکس"
    shipping_cost = Decimal("0")

    result, lines, groups = _evaluate_cart(cart)

    # -------- per-gid aggregation --------
    D0 = Decimal("0")
    per_gid: Dict[str, Dict[str, Any]] = {}

    for ln in getattr(result, "lines", []) or []:
        gid = getattr(ln, "_cart_gid", None)
        if not gid:
            continue

        row = per_gid.setdefault(
            gid,
            {"items_subtotal": D0, "services_total": D0, "discount": D0, "total": D0, "services": []},
        )

        line_sub = getattr(ln, "line_subtotal", D0)
        line_disc = getattr(ln, "line_discount", D0)
        line_total = getattr(ln, "line_total", line_sub - line_disc)

        is_service = getattr(ln, "_exclude_from_discounts", False)
        if is_service:
            row["services_total"] += line_sub
            label = getattr(ln, "label", None) or getattr(ln, "name", None) or getattr(ln, "title", None)
            if label:
                row["services"].append(label)
        else:
            row["items_subtotal"] += line_sub

        row["discount"] += line_disc
        row["total"] += line_total

    review_rows: List[Dict[str, Any]] = []
    for gid, it in groups:
        pricing = per_gid.get(gid, {"items_subtotal": D0, "services_total": D0, "discount": D0, "total": D0, "services": []})

        product_obj = it.variant or it.product
        review_rows.append({
            "gid": gid,
            "product_name": getattr(product_obj, "name", str(product_obj)),
            "qty": getattr(it, "qty", 1),
            "unit_price": getattr(it, "unit_price", None),
            "services": pricing["services"],
            "row_subtotal": pricing["items_subtotal"],
            "row_services_total": pricing["services_total"],
            "row_discount": pricing["discount"],
            "row_total": pricing["total"],
        })

    ctx: Dict[str, Any] = {
        "address": address,
        "receiver": receiver_data,
        "phone": phone,
        "review_rows": review_rows,
        "shipping_method": shipping_method,
        "shipping_method_display": shipping_method_display,
        "shipping_cost": shipping_cost,
    }
    ctx.update(_cart_summary_ctx(cart))

    return render(request, "checkout/review.html", ctx)


@login_required
def checkout_confirm(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("checkout:review")

    cart = Cart(request)
    if not _require_nonempty_cart(cart):
        messages.info(request, "سبد خرید شما خالی است.")
        return redirect("cart:cart_detail")

    # 1) آدرس انتخاب‌شده از سشن
    addr_id = request.session.get(SESSION_KEY_ADDR)
    address = Address.objects.filter(user=request.user, pk=addr_id).first()
    if not address:
        messages.error(request, "آدرس نامعتبر است.")
        return redirect("checkout:address")

    # 2) پرایسینگ نهایی با همون موتور review
    from decimal import Decimal
    from orders.models import Order, OrderItem

    result, lines, groups = _evaluate_cart(cart)
    summary = _summary_from_result(result)

    # 3) ساخت Order در اپ orders
    order = Order.objects.create(
        user=request.user,
        address=address,
        subtotal=summary["subtotal"],
        total_discount=summary["total_discount"],
        total=summary["total"],
        payment_status=Order.PaymentStatus.PENDING,
        fulfillment_status=Order.FulfillmentStatus.NEW,
    )

    # 4) خلاصه‌ی پر-گید (دقیقاً همون منطق checkout_review)
    D0 = Decimal("0")
    per_gid: Dict[str, Dict[str, Any]] = {}

    for ln in getattr(result, "lines", []) or []:
        gid = getattr(ln, "_cart_gid", None)
        if not gid:
            continue

        row = per_gid.setdefault(
            gid,
            {"items_subtotal": D0, "services_total": D0, "discount": D0, "total": D0, "services": []},
        )

        line_sub = getattr(ln, "line_subtotal", D0)
        line_disc = getattr(ln, "line_discount", D0)
        line_total = getattr(ln, "line_total", line_sub - line_disc)

        is_service = getattr(ln, "_exclude_from_discounts", False)
        if is_service:
            row["services_total"] += line_sub
        else:
            row["items_subtotal"] += line_sub

        row["discount"] += line_disc
        row["total"] += line_total

    # 5) ساخت OrderItem بر اساس هر ردیف سبد
    for gid, it in groups:
        pricing = per_gid.get(
            gid,
            {"items_subtotal": D0, "services_total": D0, "discount": D0, "total": D0, "services": []},
        )

        product_obj = getattr(it, "product")
        variant_obj = getattr(it, "variant", None)
        qty = getattr(it, "qty", 1) or 1

        unit_price = (pricing["items_subtotal"] / qty) if qty else pricing["items_subtotal"]

        OrderItem.objects.create(
            order=order,
            product=product_obj,
            variant=variant_obj,
            qty=qty,
            unit_price=unit_price,
            discount=pricing["discount"],
            total=pricing["total"],
            product_name=getattr(product_obj, "name", str(product_obj)),
        )

    # 6) رفتن به مرحله پرداخت (فعلاً همون payment_start تستی)
    return redirect("orders:payment_start", order_id=order.id)

# from __future__ import annotations
#
# from decimal import Decimal
# from typing import Any, Dict, Tuple
#
# from django import forms  # 🔸 اضافه شود
# from django.contrib import messages
# from django.contrib.auth.decorators import login_required
# from django.http import HttpRequest, HttpResponse
# from django.shortcuts import redirect, render
# from django.urls import reverse
#
# from django.contrib.messages import get_messages
# from cart.cart import Cart
# from promos.services.pricing import PricingEngine
# from products.services.pricing_adapter import (
#     build_pricing_line_public,
#     build_service_line_public,
#     build_ephemeral_campaigns_for_lines,
# )
# from shipping.models import Address
# from shipping.forms import AddressForm
#
#
# # -------------------- constants --------------------
# SESSION_KEY_ADDR = "checkout.address_id"
# SESSION_KEY_SHIPPING = "checkout.shipping_method"
# # -------------------- constants --------------------
#
# SESSION_KEY_RECEIVER = "checkout.receiver"
# # -------------------- helpers --------------------
#
# def _split_messages(request):
#     """
#     پیام‌های Django را بر اساس extra_tags جدا می‌کند:
#     - addr      → مخصوص باکس آدرس‌ها
#     - receiver  → مخصوص باکس مشخصات گیرنده
#     - other     → پیام‌های عمومی
#     """
#     storage = get_messages(request)
#     addr_msgs = []
#     receiver_msgs = []
#     other_msgs = []
#
#     for m in storage:
#         if "addr" in m.tags:
#             addr_msgs.append(m)
#         elif "receiver" in m.tags:
#             receiver_msgs.append(m)
#         else:
#             other_msgs.append(m)
#
#     return addr_msgs, receiver_msgs, other_msgs
# #
# # def _pricing_ctx_for(request: HttpRequest, cart: Cart | None = None) -> Dict[str, Any]:
# #     """
# #     کانتکست ورودی برای PricingEngine:
# #       - channel
# #       - coupons از روی سشن کارت
# #       - (اپه‌مرال‌ها را خود ویو اضافه می‌کند)
# #     """
# #     cart = cart or Cart(request)
# #     ctx: Dict[str, Any] = {"channel": "web"}
# #     coupon = cart.get_coupon()
# #     if coupon:
# #         ctx["coupons"] = [coupon]
# #     return ctx
#
#
# def _cart_summary_ctx(request: HttpRequest) -> Dict[str, Any]:
#     """
#     خلاصه‌ی سبد برای سایدبار چک‌اوت (address / review)
#     دقیقاً با همان منطقی که در cart/views.py استفاده می‌کنیم:
#     - شامل تخفیف‌های پروموشن
#     - شامل کوپن
#     - شامل سرویس‌ها
#     """
#     summary = _compute_cart_totals(request)  # از خطوط/اپه‌مرال/کوپن استفاده می‌کند
#     cart = Cart(request)
#
#     return {
#         "cart_subtotal":       Decimal(str(summary["subtotal"])),
#         "cart_total_discount": Decimal(str(summary["total_discount"])),
#         "cart_total":          Decimal(str(summary["total"])),
#         "cart_services_total": Decimal(str(summary["services_total"])),
#         "cart_coupon":         cart.get_coupon() or "",
#     }
# # -------------------- helpers --------------------
# def _require_nonempty_cart(request: HttpRequest) -> bool:
#     """آیا سبد خالی نیست؟"""
#     cart = Cart(request)
#     try:
#         return sum(int(getattr(it, "qty", 1)) for it in cart.items()) > 0
#     except Exception:
#         return False
#
#
# def _build_lines_with_gids(cart: Cart) -> Tuple[list[Any], list[tuple[str, Any]]]:
#     """خطوط پرایسینگ را از آیتم‌های سبد بساز (برای PricingEngine)."""
#     items = list(cart.items())
#     lines, groups = [], []
#     for idx, it in enumerate(items):
#         gid = f"g{idx}"
#         base = build_pricing_line_public(it.variant or it.product, it.qty)
#         if getattr(it, "unit_price", None) is not None:
#             base.unit_price = Decimal(str(it.unit_price))
#         setattr(base, "_cart_gid", gid)
#         lines.append(base)
#
#         for svc in (getattr(it, "services", []) or []):
#             svc_line = build_service_line_public(
#                 service=svc,
#                 base_line=base,
#                 item_unit_price=base.unit_price,
#                 qty=it.qty,
#             )
#             setattr(svc_line, "_cart_gid", gid)
#             lines.append(svc_line)
#
#         groups.append((gid, it))
#     return lines, groups
#
#
# def _pricing_ctx_for(request: HttpRequest) -> Dict[str, Any]:
#     cart = Cart(request)
#     codes = [cart.get_coupon()] if cart.get_coupon() else []
#     return {"channel": "web", "coupons": codes}
#
#
# def _summary_from_result(result) -> Dict[str, float]:
#     """
#     total = (subtotal_exclusive - total_discount) + services_total
#     """
#     lines = getattr(result, "lines", []) or []
#     sub_exclusive = Decimal("0")
#     svc_total = Decimal("0")
#     line_disc = Decimal("0")
#
#     for ln in lines:
#         if getattr(ln, "_exclude_from_discounts", False):
#             svc_total += getattr(ln, "line_subtotal", Decimal("0"))
#         else:
#             sub_exclusive += getattr(ln, "line_subtotal", Decimal("0"))
#         line_disc += getattr(ln, "line_discount", Decimal("0"))
#
#     cart_disc = getattr(result, "cart_discount", Decimal("0"))
#     total_discount = (line_disc + cart_disc)
#     total = (sub_exclusive - total_discount) + svc_total
#
#     def f(x: Decimal) -> float:
#         try:
#             return float(x)
#         except Exception:
#             return 0.0
#
#     return {
#         "subtotal": f(sub_exclusive),
#         "services_total": f(svc_total),
#         "total_discount": f(total_discount),
#         "total": f(total),
#     }
#
#
# def _compute_cart_totals(request: HttpRequest) -> Dict[str, float]:
#     cart = Cart(request)
#     lines, _ = _build_lines_with_gids(cart)
#     ctx = _pricing_ctx_for(request)
#     eps = build_ephemeral_campaigns_for_lines(lines, channel=ctx.get("channel", "web"))
#     if eps:
#         ctx["ephemeral_campaigns"] = eps
#     result = PricingEngine().evaluate(lines, ctx)
#     return _summary_from_result(result)
#
#
# # -------------------- flow --------------------
# def checkout_start(request: HttpRequest) -> HttpResponse:
#     """
#     دروازهٔ ورود به چک‌اوت:
#     - اگر سبد خالی بود → بازگشت به صفحهٔ سبد
#     - اگر لاگین نبود → هدایت به OTP-Login با next=checkout:address
#     - اگر لاگین بود → هدایت به مرحلهٔ انتخاب/مدیریت آدرس
#     """
#     if not _require_nonempty_cart(request):
#         messages.info(request, "سبد خرید شما خالی است.")
#         return redirect("cart:cart_detail")
#
#     if not request.user.is_authenticated:
#         login_url = reverse("account:otp_login")
#         next_url = reverse("checkout:address")
#         return redirect(f"{login_url}?next={next_url}")
#
#     return redirect("checkout:address")
#
#
# class ReceiverForm(forms.Form):
#     first_name = forms.CharField(label="نام", max_length=50)
#     last_name = forms.CharField(label="نام خانوادگی", max_length=50)
#     email = forms.EmailField(label="ایمیل", required=False)
#     national_id = forms.CharField(label="کد ملی", max_length=10, required=False)
#     gender = forms.ChoiceField(
#         label="جنسیت",
#         required=False,
#         choices=[("female", "خانم"), ("male", "آقا")],
#         widget=forms.RadioSelect
#     )
#
# @login_required
# def checkout_address(request: HttpRequest) -> HttpResponse:
#     """
#     مرحله 1: انتخاب/مدیریت آدرس + وارد کردن مشخصات گیرنده.
#     در همین صفحه سایدبار جمع سبد را هم داریم.
#     """
#     if not _require_nonempty_cart(request):
#         messages.info(request, "سبد خرید شما خالی است.")
#         return redirect("cart:cart_detail")
#
#     user = request.user
#
#     # 🔹 شماره موبایل کاربر (هر کدوم از این فیلدها بود)
#     phone = (
#         getattr(user, "phone_number", None)
#         or getattr(user, "mobile", None)
#         or getattr(user, "phone", None)
#         or ""
#     )
#
#     addresses_qs = Address.objects.filter(user=user).order_by(
#         "-is_default", "-updated_at", "-id"
#     )
#
#     # --- مقدار اولیه فرم گیرنده ---
#     receiver_initial = request.session.get(SESSION_KEY_RECEIVER) or {
#         "first_name": user.first_name,
#         "last_name": user.last_name,
#         "email": getattr(user, "email", ""),
#     }
#
#     if request.method == "POST":
#         action = (request.POST.get("action") or "").strip().lower()
#
#         # -------- آدرس: add / update --------
#         if action in {"add", "update"}:
#             addr_id = request.POST.get("address_id")
#             instance = addresses_qs.filter(pk=addr_id).first() if addr_id else None
#             address_form = AddressForm(request.POST, instance=instance)
#             receiver_form = ReceiverForm(initial=receiver_initial)
#
#             if address_form.is_valid():
#                 addr = address_form.save(user=user)
#                 messages.success(request, "آدرس ذخیره شد.", extra_tags="addr")
#                 request.session[SESSION_KEY_ADDR] = addr.id
#                 return redirect("checkout:address")
#
#             # اگر آدرس ایراد داشت
#             ctx = {
#                 "addresses": list(addresses_qs),
#                 "form": address_form,
#                 "receiver_form": receiver_form,
#                 "post_url": reverse("checkout:address"),
#                 "select_mode": 1,
#                 "selected_id": request.session.get(SESSION_KEY_ADDR) or "",
#                 "allow_add": True,
#                 "phone": phone,   # ✅ این‌جا اضافه شد
#             }
#             ctx.update(_cart_summary_ctx(request))
#             return render(request, "checkout/address.html", ctx)
#
#         # -------- آدرس: delete --------
#         if action == "delete":
#             addr_id = request.POST.get("address_id")
#             if addr_id:
#                 addresses_qs.filter(pk=addr_id).delete()
#                 if request.session.get(SESSION_KEY_ADDR) == int(addr_id):
#                     request.session.pop(SESSION_KEY_ADDR, None)
#                 messages.info(request,"آدرس حذف شد.",extra_tags="addr")
#             return redirect("checkout:address")
#
#         # -------- آدرس: select --------
#         if action == "select":
#             addr_id = request.POST.get("address_id")
#
#             if not addr_id:
#                 default = addresses_qs.filter(is_default=True).first() or addresses_qs.first()
#                 if not default:
#                     messages.error(request, "برای ادامه، حداقل یک آدرس ثبت و انتخاب کنید.")
#                     return redirect("checkout:address")
#                 addr_id_int = default.id
#             else:
#                 try:
#                     addr_id_int = int(addr_id or 0)
#                 except Exception:
#                     addr_id_int = 0
#
#                 if not addresses_qs.filter(pk=addr_id_int).exists():
#                     messages.error(request, "آدرس انتخاب‌شده معتبر نیست.",extra_tags="addr")
#                     return redirect("checkout:address")
#
#             request.session[SESSION_KEY_ADDR] = addr_id_int
#             return redirect("checkout:address")
#
#         # -------- فرم مشخصات گیرنده --------
#         if action == "receiver":
#             address_form = AddressForm()  # برای پارشیال آدرس
#             receiver_form = ReceiverForm(request.POST)
#
#             if receiver_form.is_valid():
#                 request.session[SESSION_KEY_RECEIVER] = receiver_form.cleaned_data
#
#                 # 🔹 روش ارسال را هم در سشن ذخیره کن
#                 ship_method = request.POST.get("shipping_method") or "tipax"
#                 request.session[SESSION_KEY_SHIPPING] = ship_method
#
#                 # حتماً آدرس انتخاب‌شده هم داشته باشیم
#                 if not request.session.get(SESSION_KEY_ADDR):
#                     default = addresses_qs.filter(is_default=True).first() or addresses_qs.first()
#                     if not default:
#                         messages.error(
#                             request,
#                             "لطفاً ابتدا آدرس ارسال را ثبت و انتخاب کنید.",
#                             extra_tags="receiver",
#                         )
#                         return redirect("checkout:address")
#                     request.session[SESSION_KEY_ADDR] = default.id
#
#                 return redirect("checkout:review")
#
#             # اگر فرم گیرنده ایراد داشت
#             ctx = {
#                 "addresses": list(addresses_qs),
#                 "form": address_form,
#                 "receiver_form": receiver_form,
#                 "post_url": reverse("checkout:address"),
#                 "select_mode": 1,
#                 "selected_id": request.session.get(SESSION_KEY_ADDR) or "",
#                 "allow_add": True,
#                 "phone": phone,
#             }
#             ctx.update(_cart_summary_ctx(request))
#
#             addr_msgs, receiver_msgs, other_msgs = _split_messages(request)
#             ctx["addr_messages"] = addr_msgs
#             ctx["receiver_messages"] = receiver_msgs
#             ctx["other_messages"] = other_msgs
#
#             return render(request, "checkout/address.html", ctx)
#
#     # ---------------- GET ----------------
#     addresses = list(addresses_qs)
#     address_form = AddressForm()
#     receiver_form = ReceiverForm(initial=receiver_initial)
#     selected_id = request.session.get(SESSION_KEY_ADDR) or ""
#     if not selected_id and addresses:
#         default = next((a for a in addresses if a.is_default), None)
#         if default:
#             selected_id = default.id
#
#     ctx = {
#         "addresses": addresses,
#         "form": address_form,
#         "receiver_form": receiver_form,
#         "post_url": reverse("checkout:address"),
#         "select_mode": 1,
#         "selected_id": selected_id or "",
#         "allow_add": True,
#         "phone": phone,
#     }
#     ctx.update(_cart_summary_ctx(request))
#
#     addr_msgs, receiver_msgs, other_msgs = _split_messages(request)
#     ctx["addr_messages"] = addr_msgs
#     ctx["receiver_messages"] = receiver_msgs
#     ctx["other_messages"] = other_msgs
#
#     return render(request, "checkout/address.html", ctx)
#
#
# @login_required
# def checkout_review(request: HttpRequest) -> HttpResponse:
#     """
#     مرحله 2: مرور سفارش (آدرس + مشخصات گیرنده + جمع‌های سبد + آیتم‌ها)
#     """
#     # 1) سبد خالی نباشد
#     if not _require_nonempty_cart(request):
#         messages.info(request, "سبد خرید شما خالی است.")
#         return redirect("cart:cart_detail")
#
#     # 2) آدرس انتخاب‌شده از سشن
#     addr_id = request.session.get(SESSION_KEY_ADDR)
#     if not addr_id:
#         messages.warning(request, "لطفاً ابتدا آدرس ارسال را انتخاب کنید.")
#         return redirect("checkout:address")
#
#     address = Address.objects.filter(user=request.user, pk=addr_id).first()
#     if not address:
#         messages.error(request, "آدرس انتخاب‌شده یافت نشد.")
#         return redirect("checkout:address")
#
#     # 3) آبجکت Cart مشترک
#     cart = Cart(request)
#
#     # 4) خلاصه سبد (اعداد سایدبار) → حتماً با کوپن
#     summary_ctx = _cart_summary_ctx(request)
#
#     # 5) اطلاعات گیرنده + تلفن
#     receiver_data = request.session.get(SESSION_KEY_RECEIVER, {})
#     user = request.user
#     phone = (
#         getattr(user, "phone_number", None)
#         or getattr(user, "mobile", None)
#         or getattr(user, "phone", None)
#         or ""
#     )
#
#     # 6) روش ارسال + هزینه
#     shipping_method = request.session.get(SESSION_KEY_SHIPPING, "tipax")
#     if shipping_method == "post":
#         shipping_method_display = "ارسال پستی"
#     else:
#         shipping_method_display = "ارسال تیپاکس"
#
#     shipping_cost = Decimal("0")  # فعلاً ثابت؛ بعداً می‌تونی بر اساس آدرس/روش حسابش کنی
#
#     # 7) جزییات ردیف‌های سبد با gid (مثل inspect_cart)
#     lines, groups = _build_lines_with_gids(cart)
#
#     price_ctx = _pricing_ctx_for(request)
#     epis = build_ephemeral_campaigns_for_lines(
#         lines,
#         channel=price_ctx.get("channel", "web"),
#     )
#     if epis:
#         price_ctx["ephemeral_campaigns"] = epis
#
#     result = PricingEngine().evaluate(lines, price_ctx)
#
#     # 8) تجمیع per-gid برای ساختن review_rows
#     from decimal import Decimal as D
#
#     per_gid: Dict[str, Dict[str, Any]] = {}
#     for ln in getattr(result, "lines", []) or []:
#         gid = getattr(ln, "_cart_gid", None)
#         if not gid:
#             continue
#
#         row = per_gid.setdefault(
#             gid,
#             {
#                 "items_subtotal": D("0"),
#                 "services_total": D("0"),
#                 "discount": D("0"),
#                 "total": D("0"),
#                 "services": [],
#             },
#         )
#
#         line_subtotal = getattr(ln, "line_subtotal", D("0"))
#         line_discount = getattr(ln, "line_discount", D("0"))
#         line_total = getattr(ln, "line_total", line_subtotal - line_discount)
#         is_service = getattr(ln, "_exclude_from_discounts", False)
#
#         if is_service:
#             row["services_total"] += line_subtotal
#             label = (
#                 getattr(ln, "label", None)
#                 or getattr(ln, "name", None)
#                 or getattr(ln, "title", None)
#             )
#             if label:
#                 row["services"].append(label)
#         else:
#             row["items_subtotal"] += line_subtotal
#
#         row["discount"] += line_discount
#         row["total"] += line_total
#
#     review_rows = []
#     for gid, it in groups:
#         pricing = per_gid.get(
#             gid,
#             {
#                 "items_subtotal": D("0"),
#                 "services_total": D("0"),
#                 "discount": D("0"),
#                 "total": D("0"),
#                 "services": [],
#             },
#         )
#
#         product_obj = it.variant or it.product
#         product_name = getattr(product_obj, "name", None) or str(product_obj)
#         unit_price = getattr(it, "unit_price", None)
#
#         review_rows.append(
#             {
#                 "gid": gid,
#                 "product_name": product_name,
#                 "qty": getattr(it, "qty", 1),
#                 "unit_price": unit_price,
#                 "services": pricing["services"],
#                 "row_subtotal": pricing["items_subtotal"],
#                 "row_services_total": pricing["services_total"],
#                 "row_discount": pricing["discount"],
#                 "row_total": pricing["total"],
#             }
#         )
#
#     # 9) کانتکست نهایی + merge با summary_ctx (که شامل cart_* و cart_coupon است)
#     ctx: Dict[str, Any] = {
#         "address": address,
#         "receiver": receiver_data,
#         "phone": phone,
#
#         "review_rows": review_rows,
#
#         "shipping_method": shipping_method,
#         "shipping_method_display": shipping_method_display,
#         "shipping_cost": shipping_cost,  # می‌تونی Decimal بفرستی؛ در تمپلیت با floatformat/intcomma اوکی است
#     }
#     ctx.update(summary_ctx)  # cart_subtotal, cart_total_discount, cart_total, cart_services_total, cart_coupon
#
#     return render(request, "checkout/review.html", ctx)

# @login_required
# def checkout_review(request: HttpRequest) -> HttpResponse:
#     """
#     مرحله 2: مرور سفارش (آدرس + مشخصات گیرنده + جمع‌های سبد + آیتم‌ها)
#     """
#     if not _require_nonempty_cart(request):
#         messages.info(request, "سبد خرید شما خالی است.")
#         return redirect("cart:cart_detail")
#
#     addr_id = request.session.get(SESSION_KEY_ADDR)
#     if not addr_id:
#         messages.warning(request, "لطفاً ابتدا آدرس ارسال را انتخاب کنید.")
#         return redirect("checkout:address")
#
#     address = Address.objects.filter(user=request.user, pk=addr_id).first()
#     if not address:
#         messages.error(request, "آدرس انتخاب‌شده یافت نشد.")
#         return redirect("checkout:address")
#
#     # ---------------- جمع سبد برای سایدبار ----------------
#     summary_ctx = _cart_summary_ctx(request)
#
#     # ---------------- اطلاعات گیرنده + تلفن ----------------
#     receiver_data = request.session.get(SESSION_KEY_RECEIVER, {})
#     user = request.user
#     phone = (
#         getattr(user, "phone_number", None)
#         or getattr(user, "mobile", None)
#         or getattr(user, "phone", None)
#         or ""
#     )
#
#     # ---------------- روش ارسال ----------------
#     shipping_method = request.session.get(SESSION_KEY_SHIPPING, "tipax")
#     if shipping_method == "post":
#         shipping_method_display = "ارسال پستی"
#     else:
#         shipping_method_display = "ارسال تیپاکس"
#
#     # فعلاً هزینهٔ ارسال را صفر می‌گذاریم (بعداً می‌توانیم از روی شهر/روش حساب کنیم)
#     shipping_cost = Decimal("0")
#
#     # ---------------- جزییات ردیف‌های سبد ----------------
#     cart = Cart(request)
#     lines, groups = _build_lines_with_gids(cart)
#
#     price_ctx = _pricing_ctx_for(request)
#     eps = build_ephemeral_campaigns_for_lines(lines, channel=price_ctx.get("channel", "web"))
#     if eps:
#         price_ctx["ephemeral_campaigns"] = eps
#
#     result = PricingEngine().evaluate(lines, price_ctx)
#
#     # تجمیع بر اساس gid هر ردیف سبد
#     per_gid: Dict[str, Dict[str, Any]] = {}
#     for ln in getattr(result, "lines", []) or []:
#         gid = getattr(ln, "_cart_gid", None)
#         if not gid:
#             continue
#
#         row = per_gid.setdefault(
#             gid,
#             {
#                 "items_subtotal": Decimal("0"),
#                 "services_total": Decimal("0"),
#                 "discount": Decimal("0"),
#                 "total": Decimal("0"),
#                 "services": [],
#             },
#         )
#
#         line_subtotal = getattr(ln, "line_subtotal", Decimal("0"))
#         line_discount = getattr(ln, "line_discount", Decimal("0"))
#         line_total = getattr(ln, "line_total", line_subtotal - line_discount)
#         is_service = getattr(ln, "_exclude_from_discounts", False)
#
#         if is_service:
#             row["services_total"] += line_subtotal
#             label = (
#                 getattr(ln, "label", None)
#                 or getattr(ln, "name", None)
#                 or getattr(ln, "title", None)
#             )
#             if label:
#                 row["services"].append(label)
#         else:
#             row["items_subtotal"] += line_subtotal
#
#         row["discount"] += line_discount
#         row["total"] += line_total
#
#     # ساختن ساختار مناسب برای تمپلیت
#     review_rows = []
#     for gid, it in groups:
#         pricing = per_gid.get(
#             gid,
#             {
#                 "items_subtotal": Decimal("0"),
#                 "services_total": Decimal("0"),
#                 "discount": Decimal("0"),
#                 "total": Decimal("0"),
#                 "services": [],
#             },
#         )
#
#         product_obj = it.variant or it.product
#         product_name = getattr(product_obj, "name", None) or str(product_obj)
#         unit_price = getattr(it, "unit_price", None)
#
#         review_rows.append(
#             {
#                 "gid": gid,
#                 "product_name": product_name,
#                 "qty": getattr(it, "qty", 1),
#                 "unit_price": unit_price,
#                 "services": pricing["services"],
#                 "row_subtotal": pricing["items_subtotal"],
#                 "row_services_total": pricing["services_total"],
#                 "row_discount": pricing["discount"],
#                 "row_total": pricing["total"],
#             }
#         )
#
#     # ---------------- کانتکست نهایی ----------------
#     ctx: Dict[str, Any] = {
#         "address": address,
#         "receiver": receiver_data,
#         "phone": phone,
#         "review_rows": review_rows,
#         "shipping_method": shipping_method,
#         "shipping_method_display": shipping_method_display,
#         "shipping_cost": float(shipping_cost),
#     }
#     ctx.update(summary_ctx)
#     return render(request, "checkout/review.html", ctx)
#
# @login_required
# def checkout_confirm(request: HttpRequest) -> HttpResponse:
#     """
#     مرحله 3: تایید نهایی (بعداً: ایجاد Order/Payment)
#     """
#     if request.method != "POST":
#         return redirect("checkout:review")
#
#     if not _require_nonempty_cart(request):
#         messages.info(request, "سبد خرید شما خالی است.")
#         return redirect("cart:cart_detail")
#
#     addr_id = request.session.get(SESSION_KEY_ADDR)
#     address = Address.objects.filter(user=request.user, pk=addr_id).first()
#     if not address:
#         messages.error(request, "آدرس نامعتبر است.")
#         return redirect("checkout:address")
#
#
#     messages.success(request, "سفارش شما تایید اولیه شد. (ایجاد Order/Payment به‌زودی)")
#     return redirect("checkout:review")
