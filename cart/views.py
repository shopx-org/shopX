# cart/views.py
# cart/views.py
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Tuple

from django.contrib import messages
from django.http import HttpRequest, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .cart import Cart
from products.models import Product, ProductVariant, ProductImage
from promos.services.pricing import PricingEngine
from products.services.pricing_adapter import (
    build_pricing_line_public,
    build_service_line_public,
    build_ephemeral_campaigns_for_lines,
)

# ========= Helpers (pure) =========

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

def _to_number(x: Decimal | int | float | None) -> float:
    if x is None:
        return 0.0
    try:
        return float(x)
    except Exception:
        return 0.0

def _summary_payload(result) -> Dict[str, float]:
    return {
        "subtotal": _to_number(getattr(result, "subtotal", 0)),
        "total_discount": _to_number(getattr(result, "total_discount", 0)),
        "total": _to_number(getattr(result, "total", 0)),
    }

def _row_payload(result, gid: str | None) -> Dict[str, float] | None:
    if not gid:
        return None

    sub_exclusive = Decimal("0")  # discountable lines only
    svc_total = Decimal("0")      # excluded (services)
    disc = Decimal("0")

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

def _first_image_url(product: Product) -> str | None:
    img: ProductImage | None = (
        product.images.filter(is_primary=True).first()
        or product.images.order_by("position", "id").first()
    )
    return img.image.url if img else None

def _build_lines_with_gids(cart: Cart) -> Tuple[List[Any], List[Tuple[str, SimpleNamespace]]]:
    items: Iterable[SimpleNamespace] = list(cart.items())
    lines: List[Any] = []
    groups: List[Tuple[str, SimpleNamespace]] = []

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

def _ajax(request: HttpRequest) -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"

# ========= JSON responders =========

def _json_cart_summary(request: HttpRequest) -> JsonResponse:
    cart = Cart(request)
    lines, _ = _build_lines_with_gids(cart)
    ctx = _pricing_ctx_for(request)
    eps = build_ephemeral_campaigns_for_lines(lines, channel=ctx.get("channel", "web"))
    if eps:
        ctx["ephemeral_campaigns"] = eps
    res = PricingEngine().evaluate(lines, ctx)
    return JsonResponse({"ok": True, "summary": _summary_payload(res)})

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
        "summary": _summary_payload(res),
    })

# ========= Views =========

def cart_detail(request: HttpRequest) -> HttpResponse:
    cart = Cart(request)
    lines, groups = _build_lines_with_gids(cart)

    ctx = _pricing_ctx_for(request)
    eps = build_ephemeral_campaigns_for_lines(lines, channel=ctx.get("channel", "web"))
    if eps:
        ctx["ephemeral_campaigns"] = eps

    result = PricingEngine().evaluate(lines, ctx)

    cart_rows: List[Dict[str, Any]] = []
    for gid, it in groups:
        row_sum = _row_payload(result, gid) or {
            "subtotal": 0.0, "discount": 0.0, "total": 0.0, "discount_percent": 0
        }

        product: Product = it.product
        variant: ProductVariant | None = getattr(it, "variant", None)

        cart_rows.append({
            "product_id": product.id,
            "variant_id": (variant.id if variant else None),
            "title": product.name if not variant else f"{product.name}",
            "qty": getattr(it, "qty", 1),
            "img": _first_image_url(product),
            "in_stock": (variant.in_stock if variant else True),
            "unit_price": getattr(it, "unit_price", None),

            # values computed by PricingEngine + row helper
            "subtotal": row_sum["subtotal"],
            "discount": row_sum["discount"],
            "total": row_sum["total"],
            "discount_percent": row_sum["discount_percent"],

            "services": [
                {"id": getattr(s, "id", None), "name": getattr(s, "name", str(s))}
                for s in (getattr(it, "services", []) or [])
            ],
            "remove_url": "cart:cart_remove" if variant else "cart:cart_remove_no_variant",
            "update_url": "cart:cart_update_qty" if variant else "cart:cart_update_qty_no_variant",
        })

    context = {
        "cart_rows": cart_rows,
        "cart_subtotal": getattr(result, "subtotal", Decimal("0")),
        "cart_total_discount": getattr(result, "total_discount", Decimal("0")),
        "cart_total": getattr(result, "total", Decimal("0")),
        "cart_coupon": Cart(request).get_coupon() or "",
        "result": result,
    }
    return render(request, "cart/cart_detail.html", context)

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
def cart_set_coupon(request: HttpRequest) -> HttpResponse:
    code = (request.POST.get("coupon") or "").strip()
    cart = Cart(request)
    cart.set_coupon(code if code else None)

    if _ajax(request):
        return _json_cart_summary(request)

    messages.success(request, "کوپن ثبت شد." if code else "کوپن حذف شد.")
    return redirect("cart:cart_detail")
