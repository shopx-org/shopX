# checkout/views.py
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Tuple

from django import forms  # 🔸 اضافه شود
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from django.contrib.messages import get_messages
from cart.cart import Cart
from promos.services.pricing import PricingEngine
from products.services.pricing_adapter import (
    build_pricing_line_public,
    build_service_line_public,
    build_ephemeral_campaigns_for_lines,
)
from shipping.models import Address
from shipping.forms import AddressForm


# -------------------- constants --------------------
SESSION_KEY_ADDR = "checkout.address_id"
SESSION_KEY_SHIPPING = "checkout.shipping_method"
# -------------------- constants --------------------

SESSION_KEY_RECEIVER = "checkout.receiver"
# -------------------- helpers --------------------

def _split_messages(request):
    """
    پیام‌های Django را بر اساس extra_tags جدا می‌کند:
    - addr      → مخصوص باکس آدرس‌ها
    - receiver  → مخصوص باکس مشخصات گیرنده
    - other     → پیام‌های عمومی
    """
    storage = get_messages(request)
    addr_msgs = []
    receiver_msgs = []
    other_msgs = []

    for m in storage:
        if "addr" in m.tags:
            addr_msgs.append(m)
        elif "receiver" in m.tags:
            receiver_msgs.append(m)
        else:
            other_msgs.append(m)

    return addr_msgs, receiver_msgs, other_msgs


def _cart_summary_ctx(request: HttpRequest) -> Dict[str, float]:
    """کانتکست جمع سبد برای سایدبار (مثل صفحه cart)."""
    totals = _compute_cart_totals(request)
    cart = Cart(request)
    return {
        "cart_subtotal": totals["subtotal"],
        "cart_services_total": totals["services_total"],
        "cart_total_discount": totals["total_discount"],
        "cart_total": totals["total"],
        "cart_coupon": cart.get_coupon() or "",
    }
# -------------------- helpers --------------------
def _require_nonempty_cart(request: HttpRequest) -> bool:
    """آیا سبد خالی نیست؟"""
    cart = Cart(request)
    try:
        return sum(int(getattr(it, "qty", 1)) for it in cart.items()) > 0
    except Exception:
        return False


def _build_lines_with_gids(cart: Cart) -> Tuple[list[Any], list[tuple[str, Any]]]:
    """خطوط پرایسینگ را از آیتم‌های سبد بساز (برای PricingEngine)."""
    items = list(cart.items())
    lines, groups = [], []
    for idx, it in enumerate(items):
        gid = f"g{idx}"
        base = build_pricing_line_public(it.variant or it.product, it.qty)
        if getattr(it, "unit_price", None) is not None:
            base.unit_price = Decimal(str(it.unit_price))
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


def _pricing_ctx_for(request: HttpRequest) -> Dict[str, Any]:
    cart = Cart(request)
    codes = [cart.get_coupon()] if cart.get_coupon() else []
    return {"channel": "web", "coupons": codes}


def _summary_from_result(result) -> Dict[str, float]:
    """
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

    def f(x: Decimal) -> float:
        try:
            return float(x)
        except Exception:
            return 0.0

    return {
        "subtotal": f(sub_exclusive),
        "services_total": f(svc_total),
        "total_discount": f(total_discount),
        "total": f(total),
    }


def _compute_cart_totals(request: HttpRequest) -> Dict[str, float]:
    cart = Cart(request)
    lines, _ = _build_lines_with_gids(cart)
    ctx = _pricing_ctx_for(request)
    eps = build_ephemeral_campaigns_for_lines(lines, channel=ctx.get("channel", "web"))
    if eps:
        ctx["ephemeral_campaigns"] = eps
    result = PricingEngine().evaluate(lines, ctx)
    return _summary_from_result(result)


# -------------------- flow --------------------
def checkout_start(request: HttpRequest) -> HttpResponse:
    """
    دروازهٔ ورود به چک‌اوت:
    - اگر سبد خالی بود → بازگشت به صفحهٔ سبد
    - اگر لاگین نبود → هدایت به OTP-Login با next=checkout:address
    - اگر لاگین بود → هدایت به مرحلهٔ انتخاب/مدیریت آدرس
    """
    if not _require_nonempty_cart(request):
        messages.info(request, "سبد خرید شما خالی است.")
        return redirect("cart:cart_detail")

    if not request.user.is_authenticated:
        login_url = reverse("account:otp_login")
        next_url = reverse("checkout:address")
        return redirect(f"{login_url}?next={next_url}")

    return redirect("checkout:address")


class ReceiverForm(forms.Form):
    first_name = forms.CharField(label="نام", max_length=50)
    last_name = forms.CharField(label="نام خانوادگی", max_length=50)
    email = forms.EmailField(label="ایمیل", required=False)
    national_id = forms.CharField(label="کد ملی", max_length=10, required=False)
    gender = forms.ChoiceField(
        label="جنسیت",
        required=False,
        choices=[("female", "خانم"), ("male", "آقا")],
        widget=forms.RadioSelect
    )

@login_required
def checkout_address(request: HttpRequest) -> HttpResponse:
    """
    مرحله 1: انتخاب/مدیریت آدرس + وارد کردن مشخصات گیرنده.
    در همین صفحه سایدبار جمع سبد را هم داریم.
    """
    if not _require_nonempty_cart(request):
        messages.info(request, "سبد خرید شما خالی است.")
        return redirect("cart:cart_detail")

    user = request.user

    # 🔹 شماره موبایل کاربر (هر کدوم از این فیلدها بود)
    phone = (
        getattr(user, "phone_number", None)
        or getattr(user, "mobile", None)
        or getattr(user, "phone", None)
        or ""
    )

    addresses_qs = Address.objects.filter(user=user).order_by(
        "-is_default", "-updated_at", "-id"
    )

    # --- مقدار اولیه فرم گیرنده ---
    receiver_initial = request.session.get(SESSION_KEY_RECEIVER) or {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": getattr(user, "email", ""),
    }

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip().lower()

        # -------- آدرس: add / update --------
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

            # اگر آدرس ایراد داشت
            ctx = {
                "addresses": list(addresses_qs),
                "form": address_form,
                "receiver_form": receiver_form,
                "post_url": reverse("checkout:address"),
                "select_mode": 1,
                "selected_id": request.session.get(SESSION_KEY_ADDR) or "",
                "allow_add": True,
                "phone": phone,   # ✅ این‌جا اضافه شد
            }
            ctx.update(_cart_summary_ctx(request))
            return render(request, "checkout/address.html", ctx)

        # -------- آدرس: delete --------
        if action == "delete":
            addr_id = request.POST.get("address_id")
            if addr_id:
                addresses_qs.filter(pk=addr_id).delete()
                if request.session.get(SESSION_KEY_ADDR) == int(addr_id):
                    request.session.pop(SESSION_KEY_ADDR, None)
                messages.info(request,"آدرس حذف شد.",extra_tags="addr")
            return redirect("checkout:address")

        # -------- آدرس: select --------
        if action == "select":
            addr_id = request.POST.get("address_id")

            if not addr_id:
                default = addresses_qs.filter(is_default=True).first() or addresses_qs.first()
                if not default:
                    messages.error(request, "برای ادامه، حداقل یک آدرس ثبت و انتخاب کنید.")
                    return redirect("checkout:address")
                addr_id_int = default.id
            else:
                try:
                    addr_id_int = int(addr_id or 0)
                except Exception:
                    addr_id_int = 0

                if not addresses_qs.filter(pk=addr_id_int).exists():
                    messages.error(request, "آدرس انتخاب‌شده معتبر نیست.",extra_tags="addr")
                    return redirect("checkout:address")

            request.session[SESSION_KEY_ADDR] = addr_id_int
            return redirect("checkout:address")

        # -------- فرم مشخصات گیرنده --------
        if action == "receiver":
            address_form = AddressForm()  # برای پارشیال آدرس
            receiver_form = ReceiverForm(request.POST)

            if receiver_form.is_valid():
                request.session[SESSION_KEY_RECEIVER] = receiver_form.cleaned_data

                # 🔹 روش ارسال را هم در سشن ذخیره کن
                ship_method = request.POST.get("shipping_method") or "tipax"
                request.session[SESSION_KEY_SHIPPING] = ship_method

                # حتماً آدرس انتخاب‌شده هم داشته باشیم
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

            # اگر فرم گیرنده ایراد داشت
            ctx = {
                "addresses": list(addresses_qs),
                "form": address_form,
                "receiver_form": receiver_form,
                "post_url": reverse("checkout:address"),
                "select_mode": 1,
                "selected_id": request.session.get(SESSION_KEY_ADDR) or "",
                "allow_add": True,
                "phone": phone,
            }
            ctx.update(_cart_summary_ctx(request))

            addr_msgs, receiver_msgs, other_msgs = _split_messages(request)
            ctx["addr_messages"] = addr_msgs
            ctx["receiver_messages"] = receiver_msgs
            ctx["other_messages"] = other_msgs

            return render(request, "checkout/address.html", ctx)

    # ---------------- GET ----------------
    addresses = list(addresses_qs)
    address_form = AddressForm()
    receiver_form = ReceiverForm(initial=receiver_initial)
    selected_id = request.session.get(SESSION_KEY_ADDR) or ""
    if not selected_id and addresses:
        default = next((a for a in addresses if a.is_default), None)
        if default:
            selected_id = default.id

    ctx = {
        "addresses": addresses,
        "form": address_form,
        "receiver_form": receiver_form,
        "post_url": reverse("checkout:address"),
        "select_mode": 1,
        "selected_id": selected_id or "",
        "allow_add": True,
        "phone": phone,
    }
    ctx.update(_cart_summary_ctx(request))

    addr_msgs, receiver_msgs, other_msgs = _split_messages(request)
    ctx["addr_messages"] = addr_msgs
    ctx["receiver_messages"] = receiver_msgs
    ctx["other_messages"] = other_msgs

    return render(request, "checkout/address.html", ctx)

@login_required
def checkout_review(request: HttpRequest) -> HttpResponse:
    """
    مرحله 2: مرور سفارش (آدرس + مشخصات گیرنده + جمع‌های سبد + آیتم‌ها)
    """
    if not _require_nonempty_cart(request):
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

    # ---------------- جمع سبد برای سایدبار ----------------
    summary_ctx = _cart_summary_ctx(request)

    # ---------------- اطلاعات گیرنده + تلفن ----------------
    receiver_data = request.session.get(SESSION_KEY_RECEIVER, {})
    user = request.user
    phone = (
        getattr(user, "phone_number", None)
        or getattr(user, "mobile", None)
        or getattr(user, "phone", None)
        or ""
    )

    # ---------------- روش ارسال ----------------
    shipping_method = request.session.get(SESSION_KEY_SHIPPING, "tipax")
    if shipping_method == "post":
        shipping_method_display = "ارسال پستی"
    else:
        shipping_method_display = "ارسال تیپاکس"

    # فعلاً هزینهٔ ارسال را صفر می‌گذاریم (بعداً می‌توانیم از روی شهر/روش حساب کنیم)
    shipping_cost = Decimal("0")

    # ---------------- جزییات ردیف‌های سبد ----------------
    cart = Cart(request)
    lines, groups = _build_lines_with_gids(cart)

    price_ctx = _pricing_ctx_for(request)
    eps = build_ephemeral_campaigns_for_lines(lines, channel=price_ctx.get("channel", "web"))
    if eps:
        price_ctx["ephemeral_campaigns"] = eps

    result = PricingEngine().evaluate(lines, price_ctx)

    # تجمیع بر اساس gid هر ردیف سبد
    per_gid: Dict[str, Dict[str, Any]] = {}
    for ln in getattr(result, "lines", []) or []:
        gid = getattr(ln, "_cart_gid", None)
        if not gid:
            continue

        row = per_gid.setdefault(
            gid,
            {
                "items_subtotal": Decimal("0"),
                "services_total": Decimal("0"),
                "discount": Decimal("0"),
                "total": Decimal("0"),
                "services": [],
            },
        )

        line_subtotal = getattr(ln, "line_subtotal", Decimal("0"))
        line_discount = getattr(ln, "line_discount", Decimal("0"))
        line_total = getattr(ln, "line_total", line_subtotal - line_discount)
        is_service = getattr(ln, "_exclude_from_discounts", False)

        if is_service:
            row["services_total"] += line_subtotal
            label = (
                getattr(ln, "label", None)
                or getattr(ln, "name", None)
                or getattr(ln, "title", None)
            )
            if label:
                row["services"].append(label)
        else:
            row["items_subtotal"] += line_subtotal

        row["discount"] += line_discount
        row["total"] += line_total

    # ساختن ساختار مناسب برای تمپلیت
    review_rows = []
    for gid, it in groups:
        pricing = per_gid.get(
            gid,
            {
                "items_subtotal": Decimal("0"),
                "services_total": Decimal("0"),
                "discount": Decimal("0"),
                "total": Decimal("0"),
                "services": [],
            },
        )

        product_obj = it.variant or it.product
        product_name = getattr(product_obj, "name", None) or str(product_obj)
        unit_price = getattr(it, "unit_price", None)

        review_rows.append(
            {
                "gid": gid,
                "product_name": product_name,
                "qty": getattr(it, "qty", 1),
                "unit_price": unit_price,
                "services": pricing["services"],
                "row_subtotal": pricing["items_subtotal"],
                "row_services_total": pricing["services_total"],
                "row_discount": pricing["discount"],
                "row_total": pricing["total"],
            }
        )

    # ---------------- کانتکست نهایی ----------------
    ctx: Dict[str, Any] = {
        "address": address,
        "receiver": receiver_data,
        "phone": phone,
        "review_rows": review_rows,
        "shipping_method": shipping_method,
        "shipping_method_display": shipping_method_display,
        "shipping_cost": float(shipping_cost),
    }
    ctx.update(summary_ctx)
    return render(request, "checkout/review.html", ctx)

@login_required
def checkout_confirm(request: HttpRequest) -> HttpResponse:
    """
    مرحله 3: تایید نهایی (بعداً: ایجاد Order/Payment)
    """
    if request.method != "POST":
        return redirect("checkout:review")

    if not _require_nonempty_cart(request):
        messages.info(request, "سبد خرید شما خالی است.")
        return redirect("cart:cart_detail")

    addr_id = request.session.get(SESSION_KEY_ADDR)
    address = Address.objects.filter(user=request.user, pk=addr_id).first()
    if not address:
        messages.error(request, "آدرس نامعتبر است.")
        return redirect("checkout:address")

    # TODO: در اینجا ایجاد Order + پرداخت انجام می‌شود.
    messages.success(request, "سفارش شما تایید اولیه شد. (ایجاد Order/Payment به‌زودی)")
    return redirect("checkout:review")
