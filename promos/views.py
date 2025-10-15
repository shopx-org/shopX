# promos/views.py
from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

from django.http import JsonResponse, HttpResponseBadRequest, HttpRequest, HttpResponseNotAllowed
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.cache import caches
from django.views.decorators.csrf import csrf_protect

from .models import Coupon
from .services.pricing import PricingEngine, PricingLine  # ← Engine/Line مطابق فایل تو :contentReference[oaicite:1]{index=1}


# ---------- Helpers ----------

def _json_bad_request(msg: str, extra: Dict[str, Any] | None = None) -> JsonResponse:
    data = {"ok": False, "error": msg}
    if extra:
        data.update(extra)
    return JsonResponse(data, status=400)

def _get_session_coupons(request: HttpRequest) -> List[str]:
    return request.session.get("coupons", [])

def _set_session_coupons(request: HttpRequest, codes: List[str]) -> None:
    request.session["coupons"] = codes
    request.session.modified = True

def _ratelimit_bump(key: str, limit: int, ttl_seconds: int) -> bool:
    """
    افزایش شمارنده و اعلام مجاز/غیرمجاز. اگر alias ratelimit نبود، همیشه مجاز.
    """
    try:
        rl = caches["ratelimit"]
    except Exception:
        return True  # fallback: بدون ریت‌لیمیت

    try:
        # django-redis: incr(..., ignore_key_check=True)
        count = rl.incr(key, ignore_key_check=True)
    except TypeError:
        # LocMem: set اولیه
        existing = rl.get(key)
        if existing is None:
            rl.set(key, 1, timeout=ttl_seconds)
            count = 1
        else:
            count = rl.incr(key)

    if count == 1 and hasattr(rl, "expire"):
        try:
            rl.expire(key, ttl_seconds)
        except Exception:
            pass

    return count <= limit


# ---------- Coupon endpoints ----------

@require_POST
@csrf_protect
def apply_coupon(request: HttpRequest) -> JsonResponse:
    """
    POST form-data: code=<str>
    کوپن معتبر را به سشن اضافه می‌کند (مصرف نمی‌کند). مصرف نهایی در Checkout انجام می‌شود.
    """
    code = (request.POST.get("code") or "").strip()
    if not code:
        return _json_bad_request("کد کوپن خالی است.")

    # Rate-limit سبک: 5 بار در 60 ثانیه بر اساس کاربر/IP
    user_or_ip = str(getattr(request.user, "id", None) or request.META.get("REMOTE_ADDR", "guest"))
    if not _ratelimit_bump(f"promo:apply:{user_or_ip}", limit=5, ttl_seconds=60):
        return JsonResponse({"ok": False, "error": "تلاش‌های زیاد. کمی بعد دوباره امتحان کنید."}, status=429)

    now = timezone.now()
    try:
        cp = Coupon.objects.select_related("campaign").get(code=code, is_active=True)
    except Coupon.DoesNotExist:
        return _json_bad_request("کد نامعتبر است یا یافت نشد.")

    if not cp.is_running(now):
        return _json_bad_request("کوپن منقضی/غیرفعال است.")
    if cp.campaign and not cp.campaign.is_running(now):
        return _json_bad_request("کمپین متصل به کوپن فعال نیست.")

    coupons = _get_session_coupons(request)
    if code not in coupons:
        coupons.append(code)
        _set_session_coupons(request, coupons)

    return JsonResponse({"ok": True, "coupons": coupons})


@require_POST
@csrf_protect
def remove_coupon(request: HttpRequest, code: str) -> JsonResponse:
    """
    POST (یا DELETE) برای حذف کوپن از سشن.
    """
    if request.method not in ("POST",):
        return HttpResponseNotAllowed(["POST"])

    coupons = _get_session_coupons(request)
    if code in coupons:
        coupons.remove(code)
        _set_session_coupons(request, coupons)
    return JsonResponse({"ok": True, "coupons": coupons})


# ---------- Quote endpoint ----------

@require_POST
@csrf_protect
def quote_pricing(request: HttpRequest) -> JsonResponse:
    """
    POST JSON:
    {
      "channel": "web",
      "lines": [{"pid": 1, "cid": 10, "price": "250000", "qty": 2}, ...]
    }

    - کوپن‌ها فقط از سشن خوانده می‌شوند (نه از بادی).
    - خروجی شامل breakdown کامل و explain است.
    """
    # Parse JSON
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return _json_bad_request("bad json")

    lines_in = payload.get("lines")
    if not isinstance(lines_in, list) or not lines_in:
        return _json_bad_request("lines required")

    channel = payload.get("channel", "web")
    coupons = _get_session_coupons(request)

    # Validate & build lines
    lines: List[PricingLine] = []
    for i in lines_in:
        try:
            pid = int(i["pid"])
            cid = int(i["cid"])
            price = Decimal(str(i["price"]))
            qty = int(i["qty"])
            if qty <= 0 or price < 0:
                raise ValueError("invalid qty/price")
        except (KeyError, ValueError, InvalidOperation):
            return _json_bad_request("invalid line item")

        lines.append(PricingLine(product_id=pid, category_id=cid, unit_price=price, quantity=qty))

    # Evaluate
    res = PricingEngine().evaluate(lines, {"channel": channel, "coupons": coupons})  # :contentReference[oaicite:2]{index=2}

    # Serialize Decimal-friendly response
    data = {
        "subtotal": str(res.subtotal),
        "cart_discount": str(res.cart_discount),
        "shipping_discount": str(res.shipping_discount),
        "total_discount": str(res.total_discount),
        "total": str(res.total),
        "lines": [
            {
                "product_id": l.product_id,
                "category_id": l.category_id,
                "unit_price": str(l.unit_price),
                "quantity": l.quantity,
                "line_subtotal": str(l.line_subtotal),
                "line_discount": str(l.line_discount),
            }
            for l in res.lines
        ],
        "explain": res.explain,
        "coupons": coupons,
        "channel": channel,
    }
    return JsonResponse({"ok": True, "result": data})
