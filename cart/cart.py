# cart/cart.py
from __future__ import annotations
from typing import Any, Dict, Generator, Iterable, Optional, List
from decimal import Decimal
from types import SimpleNamespace

from products.models import Product, ProductVariant, Service
from products.services.pricing_adapter import (
    build_pricing_line_public,
    build_service_line_public,
)
from promos.services.pricing import PricingEngine

CartRow = Dict[str, Any]
CartStore = Dict[str, CartRow]

class Cart:
    KEY_DATA   = "cart.v1"
    KEY_COUPON = "cart.coupon"

    def __init__(self, request):
        self.session = request.session
        raw = self.session.get(self.KEY_DATA, {})
        self._data: CartStore = dict(raw) if isinstance(raw, dict) else {}


        # ---------- helpers for per-row access ----------

    def get(self, *, product_id: int, variant_id: Optional[int]):
        key = self._key(product_id=product_id, variant_id=variant_id)
        return dict(self._data.get(key) or {})

    def set_services(self, *, product_id: int, variant_id: Optional[int], service_ids: Iterable[int]):
        key = self._key(product_id=product_id, variant_id=variant_id)
        row = self._data.get(key)
        if not row:
            return
        row["services"] = list({int(s) for s in service_ids})
        self._data[key] = row
        self._save()

    def toggle_service(self, *, product_id: int, variant_id: Optional[int], service_id: int):
        key = self._key(product_id=product_id, variant_id=variant_id)
        row = self._data.get(key)
        if not row:
            return
        cur = set(int(s) for s in row.get("services", []))
        s = int(service_id)
        if s in cur:
            cur.remove(s)
        else:
            cur.add(s)
        row["services"] = list(cur)
        self._data[key] = row
        self._save()

    # ---------- session ----------
    def _save(self) -> None:
        self.session[self.KEY_DATA] = self._data
        self.session.modified = True

    def set_coupon(self, code: Optional[str]) -> None:
        if code:
            self.session[self.KEY_COUPON] = code.strip()
        else:
            self.session.pop(self.KEY_COUPON, None)
        self.session.modified = True

    def clear_coupon(self) -> None:
        self.set_coupon(None)

    def get_coupon(self) -> Optional[str]:
        return self.session.get(self.KEY_COUPON)

    # ---------- API ----------
    @staticmethod
    def _key(*, product_id: int, variant_id: Optional[int]) -> str:
        return f"{product_id}:{variant_id or 'none'}"

    def add(self, *, product_id: int, variant_id: Optional[int] = None,
            qty: int = 1, services: Optional[Iterable[int]] = None,
            unit_price: Optional[Decimal] = None) -> None:
        key = self._key(product_id=product_id, variant_id=variant_id)
        row: CartRow = self._data.get(key, {"pid": product_id, "vid": variant_id, "qty": 0, "services": [], "unit_price": None})
        row["qty"] = int(row.get("qty", 0)) + int(qty or 1)
        if services:
            cur = set(int(s) for s in row.get("services", []))
            cur.update(int(s) for s in services)
            row["services"] = list(cur)
        if unit_price is not None:
            row["unit_price"] = str(unit_price)
        self._data[key] = row
        self._save()

    def remove(self, *, product_id: int, variant_id: Optional[int]) -> None:
        key = self._key(product_id=product_id, variant_id=variant_id)
        if key in self._data:
            self._data.pop(key)
            self._save()

    def clear(self, *, keep_coupon: bool = False) -> None:
        """
        خالی کردن کامل سبد خرید.
        اگر keep_coupon=False باشد، کوپن هم پاک می‌شود.
        """
        # همه‌ی آیتم‌ها را خالی کن
        self._data = {}
        self._save()

        # در صورت نیاز کوپن را هم پاک کن
        if not keep_coupon:
            self.session.pop(self.KEY_COUPON, None)
            self.session.modified = True
    # ---------- iteration ----------
    def items(self) -> Generator[SimpleNamespace, None, None]:
        for row in self._data.values():
            pid = int(row.get("pid"))
            vid = row.get("vid")
            qty = int(row.get("qty", 1))

            product = Product.objects.get(id=pid)
            variant: Optional[ProductVariant] = None
            if vid is not None:
                try:
                    variant = ProductVariant.objects.select_related("product").get(id=int(vid))
                    product = variant.product
                except ProductVariant.DoesNotExist:
                    variant = None

            svc_objs: List[Service] = []
            for sid in row.get("services", []):
                try:
                    svc_objs.append(Service.objects.get(id=int(sid)))
                except Service.DoesNotExist:
                    pass

            snap = row.get("unit_price")
            if snap not in (None, ""):
                unit_price = Decimal(str(snap))
            else:
                unit_price = Decimal(str((variant.price if (variant and variant.price is not None) else product.price)))

            yield SimpleNamespace(product=product, variant=variant, qty=qty, services=svc_objs, unit_price=unit_price)

    def get_total(self) -> Decimal:
        """
        مبلغ نهایی قابل پرداخت (بعد از تخفیف‌ها)، برای استفاده در هدر/مینی‌کارت.
        منطقش با _summary_payload در cart/views.py هماهنگ است.
        """
        try:
            result = self.pricing_result()
        except Exception:
            return Decimal("0")

        lines = getattr(result, "lines", []) or []

        sub_exclusive = Decimal("0")  # جمع خطوطی که تخفیف می‌خورند (کالاها)
        services_total = Decimal("0")  # جمع سرویس‌ها (exclude شده)
        line_disc = Decimal("0")  # جمع تخفیف‌های خطی

        for ln in lines:
            line_sub = getattr(ln, "line_subtotal", Decimal("0"))
            if getattr(ln, "_exclude_from_discounts", False):
                services_total += line_sub
            else:
                sub_exclusive += line_sub

            line_disc += getattr(ln, "line_discount", Decimal("0"))

        cart_disc = getattr(result, "cart_discount", Decimal("0"))
        total_discount = line_disc + cart_disc

        payable = (sub_exclusive - total_discount) + services_total
        return payable

    # ---------- pricing ----------
    def _build_pricing_lines(self):
        lines = []
        for it in self.items():
            base = build_pricing_line_public(it.variant or it.product, it.qty)

            if it.unit_price is not None:
                base.unit_price = Decimal(str(it.unit_price))  # snapshot
                base.line_subtotal = base.unit_price * base.quantity  # ✅ خیلی مهم

            lines.append(base)

            for svc in it.services:
                svc_line = build_service_line_public(
                    service=svc, base_line=base,
                    item_unit_price=base.unit_price, qty=it.qty,
                )
                # برای اطمینان (اگر build_service_line_public قیمت داد، خودش subtotal رو ساخته)
                svc_line.line_subtotal = svc_line.unit_price * svc_line.quantity  # ✅ safe
                lines.append(svc_line)

        return lines
    # def _build_pricing_lines(self):
    #     lines = []
    #     for it in self.items():
    #         base = build_pricing_line_public(it.variant or it.product, it.qty)
    #         if it.unit_price is not None:
    #             base.unit_price = Decimal(str(it.unit_price))  # snapshot
    #         lines.append(base)
    #
    #         for svc in it.services:
    #             svc_line = build_service_line_public(
    #                 service=svc, base_line=base,
    #                 item_unit_price=base.unit_price, qty=it.qty,
    #             )
    #             lines.append(svc_line)
    #     return lines

    def pricing_result(self):
        lines = self._build_pricing_lines()
        ctx = {"channel": "web", "coupons": [self.get_coupon()] if self.get_coupon() else []}
        return PricingEngine().evaluate(lines, ctx)

    def items_count(self, distinct: bool = False) -> int:
        """
        اگر distinct=True باشد تعداد ردیف‌های سبد (اقلام متمایز) را برمی‌گرداند،
        وگرنه جمع qty همه‌ی اقلام (پیشنهادی برای بج هدر) را.
        """
        data = getattr(self, "_data", {}) or {}
        if distinct:
            return len(data)
        total = 0
        for row in data.values():
            try:
                total += int(row.get("qty", 1))
            except Exception:
                total += 1
        return total


