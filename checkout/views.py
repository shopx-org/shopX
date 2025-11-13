# checkout/views.py
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Tuple

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
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


# -------------------- constants --------------------
SESSION_KEY_ADDR = "checkout.address_id"


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


@login_required
def checkout_address(request: HttpRequest) -> HttpResponse:
    """
    مرحله 1: انتخاب/مدیریت آدرس کاربر در جریان چک‌اوت.
    - GET: نمایش لیست آدرس‌ها + فرم (اجازه افزودن در چک‌اوت هم فعال است)
    - POST:
        action=add/update/delete → مدیریت آدرس‌ها
        action=select + address_id → انتخاب آدرس و رفتن به مرحلهٔ مرور
    """
    if not _require_nonempty_cart(request):
        messages.info(request, "سبد خرید شما خالی است.")
        return redirect("cart:cart_detail")

    user = request.user
    addresses_qs = Address.objects.filter(user=user).order_by("-is_default", "-updated_at", "-id")

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip().lower()

        if action in {"add", "update"}:
            addr_id = request.POST.get("address_id")
            instance = addresses_qs.filter(pk=addr_id).first() if addr_id else None
            form = AddressForm(request.POST, instance=instance)
            if form.is_valid():
                addr = form.save(user=user)
                # اگر تیک «پیش‌فرض» خورده، سایر پیش‌فرض‌ها را در مدل هندل کرده‌ایم
                messages.success(request, "آدرس ذخیره شد.")
                # آدرس تازه را برای ادامه انتخاب کن
                request.session[SESSION_KEY_ADDR] = addr.id
                return redirect("checkout:review")
            else:
                # نمایش همان صفحه با ارورهای فرم
                return render(request, "checkout/address.html", {
                    "addresses": list(addresses_qs),
                    "form": form,
                    "post_url": reverse("checkout:address"),
                    "select_mode": 1,
                    "selected_id": request.session.get(SESSION_KEY_ADDR) or "",
                    "allow_add": True,
                })

        if action == "delete":
            addr_id = request.POST.get("address_id")
            if addr_id:
                addresses_qs.filter(pk=addr_id).delete()
                # اگر همین آدرس انتخابی بوده، از سشن پاکش کن
                if request.session.get(SESSION_KEY_ADDR) == int(addr_id):
                    request.session.pop(SESSION_KEY_ADDR, None)
                messages.info(request, "آدرس حذف شد.")
            return redirect("checkout:address")

        if action == "select":
            addr_id = request.POST.get("address_id")
            try:
                addr_id_int = int(addr_id or 0)
            except Exception:
                addr_id_int = 0

            if not addresses_qs.filter(pk=addr_id_int).exists():
                messages.error(request, "آدرس انتخاب‌شده معتبر نیست.")
                return redirect("checkout:address")

            request.session[SESSION_KEY_ADDR] = addr_id_int
            return redirect("checkout:review")

        messages.error(request, "درخواست نامعتبر است.")
        return redirect("checkout:address")

    # GET
    addresses = list(addresses_qs)
    form = AddressForm()
    selected_id = request.session.get(SESSION_KEY_ADDR) or ""
    # اگر چیزی انتخاب نشده و آدرس پیش‌فرضی هست، به UX کمک کن:
    if not selected_id and addresses:
        default = next((a for a in addresses if a.is_default), None)
        if default:
            selected_id = default.id

    return render(request, "checkout/address.html", {
        "addresses": addresses,
        "form": form,
        "post_url": reverse("checkout:address"),
        "select_mode": 1,                 # در checkout حالت انتخاب فعال است
        "selected_id": selected_id or "",
        "allow_add": True,                # اجازه افزودن آدرس در checkout
    })


@login_required
def checkout_review(request: HttpRequest) -> HttpResponse:
    """
    مرحله 2: مرور سفارش (نمایش آدرس انتخاب‌شده + جمع‌های سبد)
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

    totals = _compute_cart_totals(request)

    return render(request, "checkout/review.html", {
        "address": address,
        "totals": totals,  # {subtotal, services_total, total_discount, total}
    })


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
