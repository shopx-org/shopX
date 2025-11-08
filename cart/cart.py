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

    # ---------- pricing ----------
    def _build_pricing_lines(self):
        lines = []
        for it in self.items():
            base = build_pricing_line_public(it.variant or it.product, it.qty)
            if it.unit_price is not None:
                base.unit_price = Decimal(str(it.unit_price))  # snapshot
            lines.append(base)

            for svc in it.services:
                svc_line = build_service_line_public(
                    service=svc, base_line=base,
                    item_unit_price=base.unit_price, qty=it.qty,
                )
                lines.append(svc_line)
        return lines

    def pricing_result(self):
        lines = self._build_pricing_lines()
        ctx = {"channel": "web", "coupons": [self.get_coupon()] if self.get_coupon() else []}
        return PricingEngine().evaluate(lines, ctx)


