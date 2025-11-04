from __future__ import annotations
import json
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Tuple, Optional

from django.core.management.base import BaseCommand, CommandError
from django.contrib.sessions.models import Session
from django.utils import timezone

from django.http import HttpRequest

from products.models import Product, ProductVariant, Service
from products.services.pricing_adapter import (
    build_pricing_line_public,
    build_service_line_public,
    build_ephemeral_campaigns_for_lines,
)
from promos.services.pricing import PricingEngine

# اگر Cart شما در مسیر دیگری است، این ایمپورت را اصلاح کنید
from cart.cart import Cart as SessionCart  # یا از مسیر درست پروژه‌تان


class DummySession(dict):
    """حداقلِ لازم از interface سشن جنگو برای استفاده داخل Cart"""
    modified: bool = False
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modified = False


class DummyRequest(HttpRequest):
    def __init__(self, session_data: Dict[str, Any]):
        super().__init__()
        self.session = DummySession(session_data)


def _to_number(x: Decimal | int | float | None) -> float:
    if x is None:
        return 0.0
    if isinstance(x, Decimal):
        return float(x)
    return float(x)


def _summary_payload(result) -> Dict[str, float]:
    return {
        "subtotal": _to_number(getattr(result, "subtotal", 0)),
        "total_discount": _to_number(getattr(result, "total_discount", 0)),
        "total": _to_number(getattr(result, "total", 0)),
    }


def _build_lines_with_gids(cart: SessionCart) -> Tuple[List[Any], List[Tuple[str, SimpleNamespace]]]:
    """
    همان منطق ویو cart_detail: برای هر آیتم یک gid می‌سازد تا جمع ردیفی حساب شود.
    خروجی:
      - lines: خطوط ورودی PricingEngine
      - groups: [(gid, item_ns)]
    """
    items: Iterable[SimpleNamespace] = list(cart.items())
    lines: List[Any] = []
    groups: List[Tuple[str, SimpleNamespace]] = []

    for idx, it in enumerate(items):
        gid = f"g{idx}"

        # خط پایه محصول/واریانت
        base = build_pricing_line_public(it.variant or it.product, it.qty)
        if getattr(it, "unit_price", None) is not None:
            base.unit_price = Decimal(str(it.unit_price))  # snapshot
        setattr(base, "_cart_gid", gid)
        lines.append(base)

        # خطوط سرویس‌ها
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


def _aggregate_by_gid(pricing_result) -> Dict[str, Dict[str, Decimal]]:
    """
    خطوط خروجی PricingEngine را به تفکیک gid تجمیع می‌کند.
    """
    from decimal import Decimal as D
    by_gid: Dict[str, Dict[str, D]] = {}
    for ln in getattr(pricing_result, "lines", []) or []:
        gid = getattr(ln, "_cart_gid", None)
        if not gid:
            continue
        g = by_gid.setdefault(gid, {"subtotal": D("0"), "line_discount": D("0")})
        g["subtotal"] += getattr(ln, "line_subtotal", D("0"))
        g["line_discount"] += getattr(ln, "line_discount", D("0"))
    return by_gid


class Command(BaseCommand):
    help = "Inspect current cart session and pricing breakdown."

    def add_arguments(self, parser):
        parser.add_argument("--session", dest="session_key", required=True,
                            help="Django session_key (cookie 'sessionid').")
        parser.add_argument("--json", dest="as_json", action="store_true",
                            help="Output as JSON.")
        parser.add_argument("--show-lines", dest="show_lines", action="store_true",
                            help="Also dump individual pricing lines.")

    def handle(self, *args, **options):
        session_key: str = options["session_key"]
        as_json: bool = options["as_json"]
        show_lines: bool = options["show_lines"]

        # 1) خواندن سشن از دیتابیس سشن‌ها
        try:
            s: Session = Session.objects.get(session_key=session_key, expire_date__gt=timezone.now())
            decoded = s.get_decoded()  # dict
        except Session.DoesNotExist:
            raise CommandError("Session not found or expired. Cookie/KEY درست است؟")

        # 2) ساخت request جعلی برای استفاده از Cart موجود
        req = DummyRequest(decoded)

        # 3) جمع‌کردن دیتا برای PricingEngine
        cart = SessionCart(req)

        lines, groups = _build_lines_with_gids(cart)

        ctx = {"channel": "web"}
        coupon = cart.get_coupon()
        if coupon:
            ctx["coupons"] = [coupon]

        eps = build_ephemeral_campaigns_for_lines(lines, channel=ctx.get("channel", "web"))
        if eps:
            ctx["ephemeral_campaigns"] = eps

        result = PricingEngine().evaluate(lines, ctx)
        by_gid = _aggregate_by_gid(result)

        # 4) آماده‌سازی خروجی
        rows_out: List[Dict[str, Any]] = []
        for gid, it in groups:
            agg = by_gid.get(gid, {"subtotal": Decimal("0"), "line_discount": Decimal("0")})
            line_subtotal: Decimal = agg["subtotal"]
            line_discount: Decimal = agg["line_discount"]
            line_total: Decimal = (line_subtotal - line_discount).quantize(Decimal("0.01"))

            product = it.product
            variant = getattr(it, "variant", None)
            rows_out.append({
                "product_id": product.id,
                "variant_id": (variant.id if variant else None),
                "title": product.name if not variant else f"{product.name}",
                "qty": getattr(it, "qty", 1),
                "unit_price": str(getattr(it, "unit_price", "")),
                "subtotal": float(line_subtotal),
                "discount": float(line_discount),
                "total": float(line_total),
                "services": [
                    {"id": getattr(s, "id", None), "name": getattr(s, "name", str(s))}
                    for s in (getattr(it, "services", []) or [])
                ],
            })

        out = {
            "coupon": coupon or "",
            "summary": _summary_payload(result),
            "rows": rows_out,
        }

        if show_lines:
            # Dump خطوط خام PricingEngine (در حد امکان بدون آبجکت‌های پیچیده)
            safe_lines = []
            for ln in getattr(result, "lines", []) or []:
                safe_lines.append({
                    "gid": getattr(ln, "_cart_gid", None),
                    "sku": getattr(ln, "sku", None),
                    "qty": float(getattr(ln, "qty", 0) or 0),
                    "unit_price": _to_number(getattr(ln, "unit_price", 0)),
                    "line_subtotal": _to_number(getattr(ln, "line_subtotal", 0)),
                    "line_discount": _to_number(getattr(ln, "line_discount", 0)),
                    "line_total": _to_number(getattr(ln, "line_total", 0)),
                    "tags": list(getattr(ln, "tags", []) or []),
                    "meta": dict(getattr(ln, "meta", {}) or {}),
                })
            out["pricing_lines"] = safe_lines

        # 5) چاپ
        if as_json:
            self.stdout.write(json.dumps(out, ensure_ascii=False, indent=2))
            return

        # human-readable
        self.stdout.write("\n== Cart Summary ==")
        self.stdout.write(f"Coupon: {out['coupon'] or '-'}")
        sm = out["summary"]
        self.stdout.write(f"Subtotal      : {sm['subtotal']:.2f}")
        self.stdout.write(f"Total Discount: {sm['total_discount']:.2f}")
        self.stdout.write(f"Total         : {sm['total']:.2f}")

        self.stdout.write("\n== Rows ==")
        for r in out["rows"]:
            self.stdout.write(f"- [{r['product_id']} / {r['variant_id'] or '-'}] {r['title']}")
            self.stdout.write(f"  qty={r['qty']} unit={r['unit_price'] or '-'}  "
                              f"subtotal={r['subtotal']:.2f}  discount={r['discount']:.2f}  total={r['total']:.2f}")
            if r["services"]:
                self.stdout.write("  services: " + ", ".join(f"{s['name']}#{s['id']}" for s in r["services"]))
        if show_lines:
            self.stdout.write("\n== Raw Pricing Lines ==")
            for i, ln in enumerate(out.get("pricing_lines", []), 1):
                self.stdout.write(f"{i:02d}. gid={ln['gid']} sku={ln['sku']} "
                                  f"qty={ln['qty']} unit={ln['unit_price']:.2f} "
                                  f"sub={ln['line_subtotal']:.2f} disc={ln['line_discount']:.2f} tot={ln['line_total']:.2f}")
