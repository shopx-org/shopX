# cart/views.py
from __future__ import annotations
from django.template.loader import render_to_string
from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Tuple,Optional
from promos.models import Coupon, CouponRedemption
from django.contrib import messages
from django.http import HttpRequest, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils import timezone
from .cart import Cart
from products.models import Product, ProductVariant, ProductImage
from promos.services.pricing import PricingEngine
from products.services.pricing_adapter import (
    build_pricing_line_public,
    build_service_line_public,
    build_ephemeral_campaigns_for_lines,
)
from django.views.decorators.http import require_GET
# =========================
# Helpers (pure)
# =========================
def _review_rows_from_result(result, groups):
    """
    review_rows مثل checkout_review
    """
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
        pricing = per_gid.get(
            gid,
            {"items_subtotal": D0, "services_total": D0, "discount": D0, "total": D0, "services": []},
        )

        product_obj = it.variant or it.product
        review_rows.append({
            "gid": gid,
            "product_name": getattr(product_obj, "name", str(product_obj)),
            "variant_name": getattr(getattr(it, "variant", None), "name", "") if getattr(it, "variant", None) else "",
            "qty": getattr(it, "qty", 1),
            "unit_price": getattr(it, "unit_price", None),
            "services": pricing["services"],
            "row_subtotal": pricing["items_subtotal"],
            "row_services_total": pricing["services_total"],
            "row_discount": pricing["discount"],
            "row_total": pricing["total"],
        })

    return review_rows


def _to_number(x: Decimal | int | float | None) -> float:
    if x is None:
        return 0.0
    try:
        return float(x)
    except Exception:
        return 0.0

def _pct(sub: Decimal, disc: Decimal) -> int:
    try:
        sub = Decimal(str(sub or 0))
        disc = Decimal(str(disc or 0))
        if sub > 0 and disc > 0:
            p = (disc * Decimal("100")) / sub
            return int(p.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except Exception:
        pass
    return 0

def _cart_items_count(cart: Cart) -> int:
    # اگر کارت متد اختصاصی داشته باشد
    if hasattr(cart, "items_count"):
        try:
            return int(cart.items_count())
        except Exception:
            pass
    # fallback: جمع qty ها
    try:
        return sum(int(getattr(it, "qty", 1)) for it in cart.items())
    except Exception:
        return 0

def _first_image_url(product: Product) -> str | None:
    img: ProductImage | None = (
        product.images.filter(is_primary=True).first()
        or product.images.order_by("position", "id").first()
    )
    return img.image.url if img else None

def _build_lines_with_gids(cart: Cart) -> Tuple[List[Any], List[Tuple[str, SimpleNamespace]]]:
    """
    خطوط مورد نیاز PricingEngine را بر اساس آیتم‌های سبد می‌سازد و برای هر آیتم یک gid می‌گذارد.
    """
    items: Iterable[SimpleNamespace] = list(cart.items())
    lines: List[Any] = []
    groups: List[Tuple[str, SimpleNamespace]] = []

    for idx, it in enumerate(items):
        gid = f"g{idx}"

        # خط پایه (محصول/واریانت)
        base = build_pricing_line_public(it.variant or it.product, it.qty)
        if getattr(it, "unit_price", None) is not None:
            base.unit_price = Decimal(str(it.unit_price))
            base.line_subtotal = base.unit_price * base.quantity
        setattr(base, "_cart_gid", gid)
        lines.append(base)

        # خطوط سرویس‌های افزوده
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

def _ajax(request: HttpRequest) -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"

def _row_payload(result, gid: str | None) -> Dict[str, float] | None:
    """
    خلاصهٔ یک ردیف (با توجه به gid): subtotal/discount/total/discount_percent
    subtotal شامل سرویس‌های همان ردیف هم می‌شود تا «قیمت قبل» ردیف درست نمایش داده شود.
    """
    if not gid:
        return None

    sub_exclusive = Decimal("0")  # فقط خطوط قابل تخفیف
    svc_total     = Decimal("0")  # سرویس‌ها (exclude)
    disc          = Decimal("0")

    for ln in getattr(result, "lines", []) or []:
        if getattr(ln, "_cart_gid", None) != gid:
            continue
        if getattr(ln, "_exclude_from_discounts", False):
            svc_total += getattr(ln, "line_subtotal", Decimal("0"))
        else:
            sub_exclusive += getattr(ln, "line_subtotal", Decimal("0"))
        disc += getattr(ln, "line_discount", Decimal("0"))

    subtotal_display = sub_exclusive + svc_total
    total = (sub_exclusive - disc) + svc_total

    return {
        "subtotal": _to_number(subtotal_display),
        "discount": _to_number(disc),
        "total": _to_number(total),
        "discount_percent": _pct(sub_exclusive, disc),
    }

def _summary_payload(result, request: HttpRequest | None = None) -> Dict[str, float]:
    """
    خروجی «یکدست» برای هم JSON و هم سایدبار:
      - subtotal: مجموع خطوط قابل‌تخفیف (بدون سرویس‌ها)
      - services_total: مجموع هزینهٔ سرویس‌ها
      - total_discount: جمع تخفیف خطی + سبد
      - total: مبلغ پرداختی نهایی = (subtotal - total_discount) + services_total
      - items_count: تعداد آیتم‌های سبد (برای بج هدر)
    """
    lines = getattr(result, "lines", []) or []

    sub_exclusive = Decimal("0")
    services_total = Decimal("0")
    line_disc = Decimal("0")

    for ln in lines:
        if getattr(ln, "_exclude_from_discounts", False):
            services_total += getattr(ln, "line_subtotal", Decimal("0"))
        else:
            sub_exclusive += getattr(ln, "line_subtotal", Decimal("0"))
        line_disc += getattr(ln, "line_discount", Decimal("0"))

    cart_disc = getattr(result, "cart_discount", Decimal("0"))
    total_discount = (line_disc + cart_disc)
    payable = (sub_exclusive - total_discount) + services_total

    items_count = 0
    if request is not None:
        try:
            items_count = _cart_items_count(Cart(request))
        except Exception:
            items_count = 0

    return {
        "subtotal":       _to_number(sub_exclusive),
        "services_total": _to_number(services_total),
        "total_discount": _to_number(total_discount),
        "total":          _to_number(payable),
        "items_count":    int(items_count),
    }

# =========================
# JSON responders
# =========================

def _json_cart_summary(request: HttpRequest) -> JsonResponse:
    cart = Cart(request)
    lines, _ = _build_lines_with_gids(cart)
    ctx = _pricing_ctx_for(request)
    eps = build_ephemeral_campaigns_for_lines(lines, channel=ctx.get("channel", "web"))
    if eps:
        ctx["ephemeral_campaigns"] = eps
    res = PricingEngine().evaluate(lines, ctx)
    return JsonResponse({"ok": True, "summary": _summary_payload(res, request)})

@require_GET
def cart_header_summary(request: HttpRequest) -> JsonResponse:
    """
    خلاصه‌ی سبد برای هدر (بج و مبلغ کل).
    از همان منطق _json_cart_summary استفاده می‌کند.
    """
    return _json_cart_summary(request)

def _json_cart_for_row(request: HttpRequest, product_id: int, variant_id: int | None) -> JsonResponse:
    cart = Cart(request)
    lines, groups = _build_lines_with_gids(cart)
    ctx = _pricing_ctx_for(request)
    eps = build_ephemeral_campaigns_for_lines(lines, channel=ctx.get("channel", "web"))
    if eps:
        ctx["ephemeral_campaigns"] = eps
    res = PricingEngine().evaluate(lines, ctx)

    target_gid: str | None = None
    for gid, it in groups:
        it_vid = (it.variant.id if getattr(it, "variant", None) else None)
        if it.product.id == product_id and it_vid == variant_id:
            target_gid = gid
            break

    return JsonResponse({
        "ok": True,
        "row": _row_payload(res, target_gid),
        "summary": _summary_payload(res, request),
    })

# =========================
# Views
# =========================

def cart_detail(request: HttpRequest) -> HttpResponse:
    """
    صفحهٔ سبد خرید: محاسبهٔ نهایی از PricingEngine و نمایش ردیف‌ها/سرویس‌ها.
    """
    cart = Cart(request)
    lines, groups = _build_lines_with_gids(cart)

    ctx = _pricing_ctx_for(request)
    eps = build_ephemeral_campaigns_for_lines(lines, channel=ctx.get("channel", "web"))
    if eps:
        ctx["ephemeral_campaigns"] = eps



    result = PricingEngine().evaluate(lines, ctx)
    summary = _summary_payload(result, request)  # ← منبع واحد حقیقت برای سایدبار

    # کمکی‌های نمایش رنگ/سایز
    def _color_payload_of(variant: ProductVariant | None):
        if not variant or not getattr(variant, "color_id", None):
            return None
        c = variant.color
        return {"id": c.id, "name": getattr(c, "name", ""), "hex": getattr(c, "hex_code", None)}

    def _size_payload_of(variant: ProductVariant | None):
        if not variant or not getattr(variant, "size_id", None):
            return None
        s = variant.size
        return {"id": s.id, "label": getattr(s, "label", ""), "code": getattr(s, "code", "")}

    def _toggle_url_for(product: Product, variant: ProductVariant | None, service_id: int) -> str:
        if variant:
            return reverse("cart:cart_toggle_service", args=[product.id, variant.id, service_id])
        return reverse("cart:cart_toggle_service_no_variant", args=[product.id, service_id])

    cart_rows: List[Dict[str, Any]] = []

    for gid, it in groups:
        row_sum = _row_payload(result, gid) or {
            "subtotal": 0.0, "discount": 0.0, "total": 0.0, "discount_percent": 0
        }

        product: Product = it.product
        variant: ProductVariant | None = getattr(it, "variant", None)

        # سرویس‌های انتخاب‌شدهٔ همین ردیف در سبد
        selected_services = list(getattr(it, "services", []) or [])
        selected_ids = {getattr(svc, "id", None) for svc in selected_services}

        # سرویس‌های قابل‌افزودن (یونیک)
        services_available: List[Dict[str, Any]] = []
        seen = set()
        try:
            links = product.effective_services() or []  # [{'service': Service, 'is_default_on': bool}, ...]
        except Exception:
            links = []
        for link in links:
            svc = link.get("service")
            if not svc or getattr(svc, "id", None) is None:
                continue
            if svc.id in seen:
                continue
            seen.add(svc.id)
            services_available.append({
                "id": svc.id,
                "name": getattr(svc, "name", str(svc)),
                "checked": (svc.id in selected_ids) or bool(link.get("is_default_on", False)),
                "toggle_url": _toggle_url_for(product, variant, svc.id),
            })

        # سرویس‌هایی که بالفعل در ردیف انتخاب شده‌اند اما در effective_services نبودند
        for svc in selected_services:
            sid = getattr(svc, "id", None)
            if sid is None or sid in seen:
                continue
            seen.add(sid)
            services_available.append({
                "id": sid,
                "name": getattr(svc, "name", str(svc)),
                "checked": True,
                "toggle_url": _toggle_url_for(product, variant, sid),
            })

        services_selected_payload = [
            {"id": getattr(svc, "id", None),
             "name": getattr(svc, "name", str(svc)),
             "toggle_url": _toggle_url_for(product, variant, getattr(svc, "id", None))}
            for svc in selected_services if getattr(svc, "id", None) is not None
        ]

        cart_rows.append({
            "product_id": product.id,
            "variant_id": (variant.id if variant else None),
            "title": product.name if not variant else f"{product.name}",
            "qty": getattr(it, "qty", 1),
            "img": _first_image_url(product),
            "in_stock": (variant.in_stock if variant else True),
            "unit_price": getattr(it, "unit_price", None),

            "color": _color_payload_of(variant),
            "size": _size_payload_of(variant),

            "subtotal": row_sum["subtotal"],
            "discount": row_sum["discount"],
            "total": row_sum["total"],
            "discount_percent": row_sum["discount_percent"],

            "services": services_selected_payload,
            "services_available": services_available,

            "remove_url": "cart:cart_remove" if variant else "cart:cart_remove_no_variant",
            "update_url": "cart:cart_update_qty" if variant else "cart:cart_update_qty_no_variant",
        })

    context = {
        "cart_rows": cart_rows,
        # سایدبار از خلاصهٔ واحد استفاده می‌کند
        "cart_subtotal":       Decimal(str(summary["subtotal"])),
        "cart_total_discount": Decimal(str(summary["total_discount"])),
        "cart_total":          Decimal(str(summary["total"])),
        "cart_services_total": Decimal(str(summary["services_total"])),
        "cart_coupon": Cart(request).get_coupon() or "",
        "result": result,
        "cart_items_count": summary["items_count"],
    }
    return render(request, "cart/cart_detail.html", context)

# =========================
# Mutations
# =========================

@require_POST
def cart_add(request: HttpRequest, product_id: int) -> HttpResponse:
    product = get_object_or_404(Product, pk=product_id, is_active=True, status="pub")
    variant_id_raw = request.POST.get("variant_id")
    qty_raw = request.POST.get("quantity") or "1"
    services = request.POST.getlist("services[]") or request.POST.getlist("services") or []

    try:
        qty = int(qty_raw)
    except ValueError:
        qty = 1
    qty = max(1, min(qty, 999))

    variant: ProductVariant | None = None
    if variant_id_raw not in (None, "", "null", "None"):
        variant = get_object_or_404(ProductVariant, pk=int(variant_id_raw), product=product, is_active=True)

    cart = Cart(request)
    cart.add(product_id=product.id, variant_id=(variant.id if variant else None), qty=qty, services=services)

    messages.success(request, "به سبد خرید اضافه شد.")
    return redirect("cart:cart_detail")

@require_POST
def cart_update_qty(request: HttpRequest, product_id: int, variant_id: int) -> HttpResponse:
    return _update_qty_impl(request, product_id, variant_id)

@require_POST
def cart_update_qty_no_variant(request: HttpRequest, product_id: int) -> HttpResponse:
    return _update_qty_impl(request, product_id, None)

def _get_row_services_safe(cart: Cart, product_id: int, variant_id: int | None) -> List[Any]:
    if hasattr(cart, "get"):
        row = cart.get(product_id=product_id, variant_id=variant_id)
        if row and isinstance(row, dict):
            return list(row.get("services", []))
    try:
        key = f"{product_id}:{variant_id or 'none'}"
        base = getattr(cart, "_data", {}) or {}
        row = base.get(key) or {}
        return list(row.get("services", []))
    except Exception:
        return []

def _update_qty_impl(request: HttpRequest, product_id: int, variant_id: int | None) -> HttpResponse:
    qty_raw = request.POST.get("quantity") or "1"
    try:
        qty = int(qty_raw)
    except ValueError:
        qty = 1
    qty = max(1, min(qty, 999))

    cart = Cart(request)
    services = _get_row_services_safe(cart, product_id, variant_id)

    cart.remove(product_id=product_id, variant_id=variant_id)
    cart.add(product_id=product_id, variant_id=variant_id, qty=qty, services=services)

    if _ajax(request):
        return _json_cart_for_row(request, product_id, variant_id)

    messages.success(request, "تعداد به‌روزرسانی شد.")
    return redirect("cart:cart_detail")

@require_POST
def cart_remove(request: HttpRequest, product_id: int, variant_id: int) -> HttpResponse:
    cart = Cart(request)
    cart.remove(product_id=product_id, variant_id=variant_id)

    if _ajax(request):
        return _json_cart_summary(request)

    messages.info(request, "از سبد حذف شد.")
    return redirect("cart:cart_detail")

@require_POST
def cart_remove_no_variant(request: HttpRequest, product_id: int) -> HttpResponse:
    cart = Cart(request)
    cart.remove(product_id=product_id, variant_id=None)

    if _ajax(request):
        return _json_cart_summary(request)

    messages.info(request, "از سبد حذف شد.")
    return redirect("cart:cart_detail")

@require_POST
def cart_clear(request: HttpRequest) -> HttpResponse:
    cart = Cart(request)
    if hasattr(cart, "clear"):
        cart.clear()
    else:
        cart._data = {}
        cart._save()
    messages.info(request, "سبد خرید خالی شد.")
    return redirect("cart:cart_detail")

@require_POST

def cart_set_coupon(request: HttpRequest):
    cart = Cart(request)

    raw_code = (request.POST.get("coupon") or "").strip()
    code = raw_code.upper()

    next_url = (
        request.POST.get("next")
        or request.META.get("HTTP_REFERER")
        or reverse("cart:cart_detail")
    )

    def is_ajax(req: HttpRequest) -> bool:
        return req.headers.get("X-Requested-With") == "XMLHttpRequest"

    def set_cart_coupon(value: Optional[str]):
        """
        با هر APIای که کارت داشته باشه سازگار می‌شه.
        """
        if value:
            # set
            if hasattr(cart, "set_coupon"):
                cart.set_coupon(value)
            else:
                cart.session[cart.KEY_COUPON] = value
                cart.session.modified = True
        else:
            # clear
            if hasattr(cart, "clear_coupon"):
                cart.clear_coupon()
            elif hasattr(cart, "set_coupon"):
                cart.set_coupon(None)
            else:
                cart.session.pop(cart.KEY_COUPON, None)
                cart.session.modified = True


    def respond(ok: bool, message: str):
        """
        خروجی AJAX: دوباره price می‌کنه و partialها رو می‌فرسته.
        """
        lines, groups = _build_lines_with_gids(cart)

        ctx = {"channel": "web"}
        user = request.user if request.user.is_authenticated else None
        if user:
            ctx["user"] = user  # اگر engine از user استفاده می‌کند

        cp = cart.get_coupon() if hasattr(cart, "get_coupon") else getattr(cart, "coupon", None)
        if cp:
            cp = str(cp).strip()
            ctx["coupons"] = [cp]
            ctx["coupon_codes"] = [cp]   # alias safe
            ctx["coupon"] = cp           # alias safe

        eps = build_ephemeral_campaigns_for_lines(lines, channel=ctx.get("channel", "web"))
        if eps:
            ctx["ephemeral_campaigns"] = eps


        result = PricingEngine().evaluate(lines, ctx)

        summary = _summary_payload(result, request)
        review_rows = _review_rows_from_result(result, groups)

        summary_html = render_to_string(
            "checkout/partials/_summary.html",
            {
                "cart_subtotal": summary["subtotal"],
                "cart_services_total": summary["services_total"],
                "cart_total_discount": summary["total_discount"],
                "cart_total": summary["total"],
                "cart_coupon": cp or "",
            },
            request=request,
        )

        rows_html = render_to_string(
            "checkout/partials/_review_rows.html",
            {"review_rows": review_rows},
            request=request,
        )
        # print("=== PRICING DEBUG ===")
        # print(result.explain)
        # return JsonResponse({
        #     "ok": ok,
        #     "message": message,
        #     "summary_html": summary_html,
        #     "rows_html": rows_html,
        # })

    # ---------- اگر کد خالی بود => حذف کوپن ----------
    if not code:
        set_cart_coupon(None)

        if is_ajax(request):
            return respond(True, "کد تخفیف حذف شد.")
        messages.info(request, "کد تخفیف از سبد شما حذف شد.")
        return redirect(next_url)

    now = timezone.now()
    try:
        coupon = Coupon.objects.select_related("campaign").get(code=code, is_active=True)
    except Coupon.DoesNotExist:
        set_cart_coupon(None)
        if is_ajax(request):
            return respond(False, "کد تخفیف معتبر نیست.")
        messages.error(request, "کد تخفیف معتبر نیست.")
        return redirect(next_url)

    if not coupon.is_running(now):
        set_cart_coupon(None)
        if is_ajax(request):
            return respond(False, "مهلت استفاده از این کد تخفیف تمام شده یا هنوز شروع نشده است.")
        messages.error(request, "مهلت استفاده از این کد تخفیف تمام شده یا هنوز شروع نشده است.")
        return redirect(next_url)

    camp = coupon.campaign
    if camp and not camp.is_running(now):
        set_cart_coupon(None)
        if is_ajax(request):
            return respond(False, "کمپین مربوط به این کد تخفیف فعال نیست.")
        messages.error(request, "کمپین مربوط به این کد تخفیف فعال نیست.")
        return redirect(next_url)

    user = request.user if request.user.is_authenticated else None

    if coupon.usage_limit_total is not None and coupon.used_count >= coupon.usage_limit_total:
        set_cart_coupon(None)
        if is_ajax(request):
            return respond(False, "سقف استفاده از این کد تخفیف تمام شده است.")
        messages.error(request, "سقف استفاده از این کد تخفیف تمام شده است.")
        return redirect(next_url)

    if user and coupon.usage_limit_per_user:
        active_redemptions = CouponRedemption.objects.filter(
            coupon=coupon,
            user=user,
            status__in=["reserved", "consumed"],
        ).count()
        if active_redemptions >= coupon.usage_limit_per_user:
            set_cart_coupon(None)
            if is_ajax(request):
                return respond(False, "شما قبلاً از این کد تخفیف استفاده کرده‌اید.")
            messages.error(request, "شما قبلاً از این کد تخفیف استفاده کرده‌اید.")
            return redirect(next_url)

    # ---------- همه چیز OK ----------
    set_cart_coupon(code)

    if is_ajax(request):
        return respond(True, "کد تخفیف با موفقیت اعمال شد.")
    messages.success(request, "کد تخفیف با موفقیت روی سبد شما اعمال شد.")
    return redirect(next_url)

@require_POST
def cart_toggle_service(request: HttpRequest, product_id: int, variant_id: int, service_id: int) -> HttpResponse:
    cart = Cart(request)
    cart.toggle_service(product_id=product_id, variant_id=variant_id, service_id=service_id)
    return _json_cart_for_row(request, product_id, variant_id)

@require_POST
def cart_toggle_service_no_variant(request: HttpRequest, product_id: int, service_id: int) -> HttpResponse:
    cart = Cart(request)
    cart.toggle_service(product_id=product_id, variant_id=None, service_id=service_id)
    return _json_cart_for_row(request, product_id, None)

# # cart/views.py
# # cart/views.py
# from __future__ import annotations
# from django.urls import reverse
# from decimal import Decimal, ROUND_HALF_UP
# from types import SimpleNamespace
# from typing import Any, Dict, Iterable, List, Tuple
#
# from django.contrib import messages
# from django.http import HttpRequest, JsonResponse, HttpResponse
# from django.shortcuts import get_object_or_404, redirect, render
# from django.views.decorators.http import require_POST
#
# from .cart import Cart
# from products.models import Product, ProductVariant, ProductImage
# from promos.services.pricing import PricingEngine
# from products.services.pricing_adapter import (
#     build_pricing_line_public,
#     build_service_line_public,
#     build_ephemeral_campaigns_for_lines,
# )
#
# # ========= Helpers (pure) =========
# def _cart_items_count(cart: Cart) -> int:
#     # ترجیحاً متد داخلی کارت
#     if hasattr(cart, "items_count"):
#         try:
#             return int(cart.items_count())
#         except Exception:
#             pass
#     # جمع qty ها به عنوان fallback
#     try:
#         return sum(int(getattr(it, "qty", 1)) for it in cart.items())
#     except Exception:
#         return 0
#
# def _summary_payload(result, request: HttpRequest | None = None) -> Dict[str, float]:
#     items_count = 0
#     if request is not None:
#         try:
#             items_count = Cart(request).items_count()
#         except Exception:
#             items_count = 0
#
#     return {
#         "subtotal": _to_number(getattr(result, "subtotal", 0)),
#         "total_discount": _to_number(getattr(result, "total_discount", 0)),
#         "total": _to_number(getattr(result, "total", 0)),
#         # اگر قبلاً services_total را به result اضافه کرده‌ای:
#         "services_total": _to_number(getattr(result, "services_total", 0)),
#         "items_count": int(items_count),
#     }
#
#
# def _summary_payload(result) -> Dict[str, float]:
#     """
#     result: خروجی PricingEngine.evaluate
#     خروجی این تابع، با منطق نمایش ردیف‌ها هم‌راستا می‌شود:
#     - subtotal: مجموع آیتم‌های «قابل‌تخفیف» (بدون سرویس‌ها)
#     - services_total: مجموع هزینهٔ سرویس‌ها (لاین‌های exclude)
#     - total_discount: جمع تخفیف خطی + تخفیف سبد
#     - total: مبلغ پرداختی نهایی = (subtotal - total_discount) + services_total
#     """
#     from decimal import Decimal
#
#     lines = getattr(result, "lines", []) or []
#
#     sub_exclusive = Decimal("0")  # فقط خطوط قابل‌تخفیف
#     svc_total     = Decimal("0")  # خطوط سرویس (exclude)
#     line_disc     = Decimal("0")
#
#     for ln in lines:
#         if getattr(ln, "_exclude_from_discounts", False):
#             svc_total += getattr(ln, "line_subtotal", Decimal("0"))
#         else:
#             sub_exclusive += getattr(ln, "line_subtotal", Decimal("0"))
#         line_disc += getattr(ln, "line_discount", Decimal("0"))
#
#     cart_disc = getattr(result, "cart_discount", Decimal("0"))
#
#     total_discount = (line_disc + cart_disc)
#     payable = (sub_exclusive - total_discount) + svc_total
#
#     def _f(x):  # به float برای JSON
#         try:
#             return float(x)
#         except Exception:
#             return 0.0
#
#     return {
#         "subtotal": _f(sub_exclusive),
#         "services_total": _f(svc_total),
#         "total_discount": _f(total_discount),
#         "total": _f(payable),
#     }
#
#
# # --- helpers for variant meta shown in cart ---
# def _color_payload(variant: ProductVariant | None):
#     try:
#         c = getattr(variant, "color", None)
#         if not c:
#             return None
#         return {
#             "name": getattr(c, "name", "") or "",
#             "hex":  str(getattr(c, "hex_code", "") or ""),
#             "slug": getattr(c, "slug", "") or "",
#             "swatch": (c.swatch_image.url if getattr(c, "swatch_image", None) else None),
#         }
#     except Exception:
#         return None
#
# def _size_payload(variant: ProductVariant | None):
#     try:
#         s = getattr(variant, "size", None)
#         if not s:
#             return None
#         return {"label": getattr(s, "label", "") or "", "code": getattr(s, "code", "") or ""}
#     except Exception:
#         return None
#
# def _pct(sub: Decimal, disc: Decimal) -> int:
#     try:
#         sub = Decimal(str(sub or 0))
#         disc = Decimal(str(disc or 0))
#         if sub > 0 and disc > 0:
#             p = (disc * Decimal("100")) / sub
#             return int(p.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
#     except Exception:
#         pass
#     return 0
#
# def _to_number(x: Decimal | int | float | None) -> float:
#     if x is None:
#         return 0.0
#     try:
#         return float(x)
#     except Exception:
#         return 0.0
#
# def _summary_payload(result) -> Dict[str, float]:
#     return {
#         "subtotal": _to_number(getattr(result, "subtotal", 0)),
#         "total_discount": _to_number(getattr(result, "total_discount", 0)),
#         "total": _to_number(getattr(result, "total", 0)),
#     }
#
# def _row_payload(result, gid: str | None) -> Dict[str, float] | None:
#     if not gid:
#         return None
#
#     sub_exclusive = Decimal("0")  # discountable lines only
#     svc_total = Decimal("0")      # excluded (services)
#     disc = Decimal("0")
#
#     for ln in getattr(result, "lines", []) or []:
#         if getattr(ln, "_cart_gid", None) != gid:
#             continue
#         if getattr(ln, "_exclude_from_discounts", False):
#             svc_total += getattr(ln, "line_subtotal", Decimal("0"))
#         else:
#             sub_exclusive += getattr(ln, "line_subtotal", Decimal("0"))
#         disc += getattr(ln, "line_discount", Decimal("0"))
#
#     subtotal_display = sub_exclusive + svc_total
#     total = (sub_exclusive - disc) + svc_total
#
#     return {
#         "subtotal": _to_number(subtotal_display),
#         "discount": _to_number(disc),
#         "total": _to_number(total),
#         "discount_percent": _pct(sub_exclusive, disc),
#     }
#
# def _first_image_url(product: Product) -> str | None:
#     img: ProductImage | None = (
#         product.images.filter(is_primary=True).first()
#         or product.images.order_by("position", "id").first()
#     )
#     return img.image.url if img else None
#
# def _build_lines_with_gids(cart: Cart) -> Tuple[List[Any], List[Tuple[str, SimpleNamespace]]]:
#     items: Iterable[SimpleNamespace] = list(cart.items())
#     lines: List[Any] = []
#     groups: List[Tuple[str, SimpleNamespace]] = []
#
#     for idx, it in enumerate(items):
#         gid = f"g{idx}"
#
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
#
#     return lines, groups
#
# def _pricing_ctx_for(request: HttpRequest) -> Dict[str, Any]:
#     cart = Cart(request)
#     codes = [cart.get_coupon()] if cart.get_coupon() else []
#     return {"channel": "web", "coupons": codes}
#
# def _ajax(request: HttpRequest) -> bool:
#     return request.headers.get("X-Requested-With") == "XMLHttpRequest"
#
# # ========= JSON responders =========
#
# def _json_cart_summary(request: HttpRequest) -> JsonResponse:
#     cart = Cart(request)
#     lines, _ = _build_lines_with_gids(cart)
#     ctx = _pricing_ctx_for(request)
#     eps = build_ephemeral_campaigns_for_lines(lines, channel=ctx.get("channel", "web"))
#     if eps:
#         ctx["ephemeral_campaigns"] = eps
#     res = PricingEngine().evaluate(lines, ctx)
#     return JsonResponse({"ok": True, "summary": _summary_payload(res, request)})
#
# def _json_cart_for_row(request: HttpRequest, product_id: int, variant_id: int | None) -> JsonResponse:
#     cart = Cart(request)
#     lines, groups = _build_lines_with_gids(cart)
#     ctx = _pricing_ctx_for(request)
#     eps = build_ephemeral_campaigns_for_lines(lines, channel=ctx.get("channel", "web"))
#     if eps:
#         ctx["ephemeral_campaigns"] = eps
#     res = PricingEngine().evaluate(lines, ctx)
#
#     target_gid: str | None = None
#     for gid, it in groups:
#         it_vid = (it.variant.id if getattr(it, "variant", None) else None)
#         if it.product.id == product_id and it_vid == variant_id:
#             target_gid = gid
#             break
#
#     return JsonResponse({
#         "ok": True,
#         "row": _row_payload(res, target_gid),
#         "summary": _summary_payload(res, request),
#     })
# # ========= Views =========
#
# def cart_detail(request: HttpRequest) -> HttpResponse:
#     """
#     صفحه‌ی سبد خرید با محاسبه‌ی کامل:
#     - اعمال کمپین‌ها/کوپن‌ها با PricingEngine
#     - جمع ردیفی (محصول + سرویس‌ها) با استفاده از gid
#     - لیست سرویس‌های انتخاب‌شده و سرویس‌های قابل‌افزودن به هر ردیف (به‌همراه toggle_url)
#     - محاسبه‌ی مجموع هزینه‌ی سرویس‌ها برای سایدبار
#     """
#     cart = Cart(request)
#     lines, groups = _build_lines_with_gids(cart)
#
#     # کانتکست موتور قیمت‌گذاری + کمپین‌های موقت
#     ctx = _pricing_ctx_for(request)
#     eps = build_ephemeral_campaigns_for_lines(lines, channel=ctx.get("channel", "web"))
#     if eps:
#         ctx["ephemeral_campaigns"] = eps
#
#     # خروجی موتور قیمت‌گذاری
#     result = PricingEngine().evaluate(lines, ctx)
#     sub_exclusive = Decimal("0")
#     services_total = Decimal("0")
#     line_disc = Decimal("0")
#
#     for ln in getattr(result, "lines", []) or []:
#         if getattr(ln, "_exclude_from_discounts", False):
#             services_total += getattr(ln, "line_subtotal", Decimal("0"))
#         else:
#             sub_exclusive += getattr(ln, "line_subtotal", Decimal("0"))
#         line_disc += getattr(ln, "line_discount", Decimal("0"))
#
#     cart_disc = getattr(result, "cart_discount", Decimal("0"))
#     total_discount = (line_disc + cart_disc)
#     payable = (sub_exclusive - total_discount) + services_total
#
#     # کمکی‌های داخلی برای رنگ/سایز (self-contained)
#     def _color_payload_of(variant: ProductVariant | None):
#         if not variant or not getattr(variant, "color_id", None):
#             return None
#         c = variant.color
#         return {
#             "id": c.id,
#             "name": getattr(c, "name", ""),
#             "hex": getattr(c, "hex_code", None),
#         }
#
#     def _size_payload_of(variant: ProductVariant | None):
#         if not variant or not getattr(variant, "size_id", None):
#             return None
#         s = variant.size
#         return {
#             "id": s.id,
#             "label": getattr(s, "label", ""),
#             "code": getattr(s, "code", ""),
#         }
#
#     def _toggle_url_for(product: Product, variant: ProductVariant | None, service_id: int) -> str:
#         if variant:
#             return reverse("cart:cart_toggle_service", args=[product.id, variant.id, service_id])
#         return reverse("cart:cart_toggle_service_no_variant", args=[product.id, service_id])
#
#     cart_rows: List[Dict[str, Any]] = []
#
#     for gid, it in groups:
#         # جمع‌های ردیفی از نتیجه‌ی موتور
#         row_sum = _row_payload(result, gid) or {
#             "subtotal": 0.0,
#             "discount": 0.0,
#             "total": 0.0,
#             "discount_percent": 0,
#         }
#
#         product: Product = it.product
#         variant: ProductVariant | None = getattr(it, "variant", None)
#
#         # سرویس‌های انتخاب‌شدهٔ همین ردیف در سبد
#         selected_services = list(getattr(it, "services", []) or [])
#         selected_ids = {getattr(svc, "id", None) for svc in selected_services}
#
#         # سرویس‌های «قابل‌اعمال» سطح محصول/دسته (برای نمایش سوییچ)
#         services_available: List[Dict[str, Any]] = []
#         try:
#             links = product.effective_services() or []   # [{'service': Service, 'is_default_on': bool}, ...]
#         except Exception:
#             links = []
#
#         seen = set()  # برای جلوگیری از تکرار
#         for link in links:
#             svc = link.get("service")
#             if not svc or getattr(svc, "id", None) is None:
#                 continue
#             if svc.id in seen:
#                 continue
#             seen.add(svc.id)
#             services_available.append({
#                 "id": svc.id,
#                 "name": getattr(svc, "name", str(svc)),
#                 "checked": (svc.id in selected_ids) or bool(link.get("is_default_on", False)),
#                 "toggle_url": _toggle_url_for(product, variant, svc.id),
#             })
#
#         # اگر سرویسی در ردیف انتخاب شده ولی در effective_services نبود، اضافه‌اش کنیم
#         for svc in selected_services:
#             sid = getattr(svc, "id", None)
#             if sid is None or sid in seen:
#                 continue
#             seen.add(sid)
#             services_available.append({
#                 "id": sid,
#                 "name": getattr(svc, "name", str(svc)),
#                 "checked": True,
#                 "toggle_url": _toggle_url_for(product, variant, sid),
#             })
#
#         # همچنین لیست فشرده از سرویس‌های انتخاب‌شده (برای نمایش زیر هر ردیف)
#         services_selected_payload = [
#             {
#                 "id": getattr(svc, "id", None),
#                 "name": getattr(svc, "name", str(svc)),
#                 "toggle_url": _toggle_url_for(product, variant, getattr(svc, "id", None)),
#             }
#             for svc in selected_services
#             if getattr(svc, "id", None) is not None
#         ]
#
#         cart_rows.append({
#             "product_id": product.id,
#             "variant_id": (variant.id if variant else None),
#             "title": product.name if not variant else f"{product.name}",
#             "qty": getattr(it, "qty", 1),
#             "img": _first_image_url(product),
#             "in_stock": (variant.in_stock if variant else True),
#             "unit_price": getattr(it, "unit_price", None),
#
#             # رنگ/سایز برای نمایش
#             "color": _color_payload_of(variant),
#             "size": _size_payload_of(variant),
#
#             # جمع‌های محاسبه‌شده برای ردیف
#             "subtotal": row_sum["subtotal"],
#             "discount": row_sum["discount"],
#             "total": row_sum["total"],
#             "discount_percent": row_sum["discount_percent"],
#
#             # سرویس‌ها
#             "services": services_selected_payload,      # فقط انتخاب‌شده‌ها
#             "services_available": services_available,    # برای سوییچ/تغییر وضعیت
#
#             # URLهای اکشن
#             "remove_url": "cart:cart_remove" if variant else "cart:cart_remove_no_variant",
#             "update_url": "cart:cart_update_qty" if variant else "cart:cart_update_qty_no_variant",
#         })
#
#     context = {
#         "cart_rows": cart_rows,
#         "cart_subtotal": sub_exclusive,          # «جمع جزء» (بدون سرویس‌ها)
#         "cart_total_discount": total_discount,   # تخفیف کل (خطی + سبد)
#         "cart_total": payable,                   # مبلغ پرداختی نهایی = محصولات - تخفیف + سرویس‌ها
#         "cart_services_total": services_total,   # برای خط «هزینه سرویس‌ها» در سایدبار
#         "cart_coupon": Cart(request).get_coupon() or "",
#         "result": result,
#         "cart_items_count": _cart_items_count(cart),  # ← این خط جدید
#     }
#     return render(request, "cart/cart_detail.html", context)
#
#
# @require_POST
# def cart_add(request: HttpRequest, product_id: int) -> HttpResponse:
#     product = get_object_or_404(Product, pk=product_id, is_active=True, status="pub")
#     variant_id_raw = request.POST.get("variant_id")
#     qty_raw = request.POST.get("quantity") or "1"
#     services = request.POST.getlist("services[]") or request.POST.getlist("services") or []
#
#     try:
#         qty = int(qty_raw)
#     except ValueError:
#         qty = 1
#     qty = max(1, min(qty, 999))
#
#     variant: ProductVariant | None = None
#     if variant_id_raw not in (None, "", "null", "None"):
#         variant = get_object_or_404(ProductVariant, pk=int(variant_id_raw), product=product, is_active=True)
#
#     cart = Cart(request)
#     cart.add(product_id=product.id, variant_id=(variant.id if variant else None), qty=qty, services=services)
#
#     messages.success(request, "به سبد خرید اضافه شد.")
#     return redirect("cart:cart_detail")
#
# @require_POST
# def cart_update_qty(request: HttpRequest, product_id: int, variant_id: int) -> HttpResponse:
#     return _update_qty_impl(request, product_id, variant_id)
#
# @require_POST
# def cart_update_qty_no_variant(request: HttpRequest, product_id: int) -> HttpResponse:
#     return _update_qty_impl(request, product_id, None)
#
# def _get_row_services_safe(cart: Cart, product_id: int, variant_id: int | None) -> List[Any]:
#     if hasattr(cart, "get"):
#         row = cart.get(product_id=product_id, variant_id=variant_id)
#         if row and isinstance(row, dict):
#             return list(row.get("services", []))
#     try:
#         key = f"{product_id}:{variant_id or 'none'}"
#         base = getattr(cart, "_data", {}) or {}
#         row = base.get(key) or {}
#         return list(row.get("services", []))
#     except Exception:
#         return []
#
# def _update_qty_impl(request: HttpRequest, product_id: int, variant_id: int | None) -> HttpResponse:
#     qty_raw = request.POST.get("quantity") or "1"
#     try:
#         qty = int(qty_raw)
#     except ValueError:
#         qty = 1
#     qty = max(1, min(qty, 999))
#
#     cart = Cart(request)
#     services = _get_row_services_safe(cart, product_id, variant_id)
#
#     cart.remove(product_id=product_id, variant_id=variant_id)
#     cart.add(product_id=product_id, variant_id=variant_id, qty=qty, services=services)
#
#     if _ajax(request):
#         return _json_cart_for_row(request, product_id, variant_id)
#
#     messages.success(request, "تعداد به‌روزرسانی شد.")
#     return redirect("cart:cart_detail")
#
# @require_POST
# def cart_remove(request: HttpRequest, product_id: int, variant_id: int) -> HttpResponse:
#     cart = Cart(request)
#     cart.remove(product_id=product_id, variant_id=variant_id)
#
#     if _ajax(request):
#         return _json_cart_summary(request)
#
#     messages.info(request, "از سبد حذف شد.")
#     return redirect("cart:cart_detail")
#
# @require_POST
# def cart_remove_no_variant(request: HttpRequest, product_id: int) -> HttpResponse:
#     cart = Cart(request)
#     cart.remove(product_id=product_id, variant_id=None)
#
#     if _ajax(request):
#         return _json_cart_summary(request)
#
#     messages.info(request, "از سبد حذف شد.")
#     return redirect("cart:cart_detail")
#
# @require_POST
# def cart_clear(request: HttpRequest) -> HttpResponse:
#     cart = Cart(request)
#     if hasattr(cart, "clear"):
#         cart.clear()
#     else:
#         cart._data = {}
#         cart._save()
#     messages.info(request, "سبد خرید خالی شد.")
#     return redirect("cart:cart_detail")
#
# @require_POST
# def cart_set_coupon(request: HttpRequest) -> HttpResponse:
#     code = (request.POST.get("coupon") or "").strip()
#     cart = Cart(request)
#     cart.set_coupon(code if code else None)
#
#     if _ajax(request):
#         return _json_cart_summary(request)
#
#     messages.success(request, "کوپن ثبت شد." if code else "کوپن حذف شد.")
#     return redirect("cart:cart_detail")
#
#
# @require_POST
# def cart_toggle_service(request: HttpRequest, product_id: int, variant_id: int, service_id: int) -> HttpResponse:
#     cart = Cart(request)
#     cart.toggle_service(product_id=product_id, variant_id=variant_id, service_id=service_id)
#     return _json_cart_for_row(request, product_id, variant_id)
#
# @require_POST
# def cart_toggle_service_no_variant(request: HttpRequest, product_id: int, service_id: int) -> HttpResponse:
#     cart = Cart(request)
#     cart.toggle_service(product_id=product_id, variant_id=None, service_id=service_id)
#     return _json_cart_for_row(request, product_id, None)