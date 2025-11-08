# products/services/pricing_adapter.py
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from types import SimpleNamespace
from typing import Optional, List

from django.utils import timezone

from products.models import Service
# موتور پرایسینگ را فقط وقتی لازم شد import می‌کنیم تا چرخه‌ی import نشود
# from promos.services.pricing import PricingLine, PricingEngine

# -----------------------------
# Money / parsing helpers
# -----------------------------
_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٬, ", "0123456789,, ")

def _to_money(val, *, fallback: str | int | float = "0") -> Decimal:
    """
    Normalizes None / '' / Persian digits / with comma → Decimal.
    Falls back to `fallback` on error.
    """
    if val is None:
        val = fallback
    s = str(val).strip()
    if s in ("", "None", "nan", "NaN", "NULL"):
        s = str(fallback)
    s = s.translate(_PERSIAN_DIGITS).replace(",", "")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(str(fallback))

# -----------------------------
# Line builders
# -----------------------------
def _is_variant(item) -> bool:
    return hasattr(item, "product_id") and getattr(item, "product_id") is not None

def _build_pricing_line(item, qty: int = 1):
    """
    Returns promos.services.pricing.PricingLine for a product OR variant.
    Fills helper fields used in rules (variant_id, brand_id, extra_category_ids)
    and *_sale_* flags used to generate ephemeral campaigns.
    """
    from promos.services.pricing import PricingLine  # lazy import

    if _is_variant(item):
        variant = item
        product = variant.product

        # unit price: variant price if set, otherwise product price
        raw_unit = getattr(variant, "price", None)
        if raw_unit in ("", None):
            raw_unit = getattr(product, "price", None)
        unit_price = _to_money(raw_unit, fallback=(getattr(product, "price", 0) or 0))

        try:
            extra_cids = list(product.additional_categories.values_list("id", flat=True))
        except Exception:
            extra_cids = []
        brand_id = getattr(product, "brand_fk_id", None)

        line = PricingLine(
            product_id=product.id,
            category_id=product.category_id,
            unit_price=unit_price,
            quantity=int(qty),
        )
        # enrich
        for name, val in (
            ("variant_id", variant.id),
            ("brand_id", brand_id),
            ("extra_category_ids", extra_cids),
        ):
            try:
                setattr(line, name, val)
            except Exception:
                pass

        # variant-level sale flags
        v_active  = bool(getattr(variant, "sale_active_variant", False))
        v_percent = getattr(variant, "sale_percent_variant", None)
        v_amount  = getattr(variant, "sale_amount_variant", None)
        for name, val in (
            ("_variant_sale_active", v_active),
            ("_variant_sale_percent", Decimal(str(v_percent)) if v_percent not in (None, "") else None),
            ("_variant_sale_amount",  Decimal(str(v_amount))  if v_amount  not in (None, "") else None),
        ):
            try:
                setattr(line, name, val)
            except Exception:
                pass

        return line

    # product-level
    product = item
    unit_price = _to_money(getattr(product, "price", None), fallback=0)

    try:
        extra_cids = list(product.additional_categories.values_list("id", flat=True))
    except Exception:
        extra_cids = []
    brand_id = getattr(product, "brand_fk_id", None)

    line = _new_pricing_line(product_id=product.id, category_id=product.category_id,
                             unit_price=unit_price, quantity=int(qty))
    for name, val in (
        ("brand_id", brand_id),
        ("extra_category_ids", extra_cids),
    ):
        try:
            setattr(line, name, val)
        except Exception:
            pass

    # product-level sale flags
    p_active  = bool(getattr(product, "sale_active", False))
    p_percent = getattr(product, "sale_percent", None)
    p_amount  = getattr(product, "sale_amount", None)
    for name, val in (
        ("_product_sale_active", p_active),
        ("_product_sale_percent", Decimal(str(p_percent)) if p_percent not in (None, "") else None),
        ("_product_sale_amount",  Decimal(str(p_amount))  if p_amount  not in (None, "") else None),
    ):
        try:
            setattr(line, name, val)
        except Exception:
            pass

    return line

def _new_pricing_line(*, product_id: int, category_id: int, unit_price: Decimal, quantity: int, **extras):
    """Small helper to instantiate PricingLine with lazy import."""
    from promos.services.pricing import PricingLine  # lazy import
    line = PricingLine(
        product_id=product_id,
        category_id=category_id,
        unit_price=unit_price,
        quantity=int(quantity),
    )
    for k, v in (extras or {}).items():
        try:
            setattr(line, k, v)
        except Exception:
            pass
    return line

# -----------------------------
# Ephemeral campaign builders
# -----------------------------
def _ns_rule(kind: str, payload: dict) -> SimpleNamespace:
    return SimpleNamespace(kind=kind, payload=payload)

def _ns_action(kind: str, scope: str, value: Optional[Decimal] = None, cap: Optional[Decimal] = None) -> SimpleNamespace:
    ns = SimpleNamespace(kind=kind, scope=scope)
    if value is not None:
        setattr(ns, "value", str(value))
    if cap is not None:
        setattr(ns, "cap", str(cap))
    return ns

def _ephemeral_from_variant_line(ln, channel: str) -> Optional[SimpleNamespace]:
    if not getattr(ln, "_variant_sale_active", False):
        return None

    vp = getattr(ln, "_variant_sale_percent", None)
    va = getattr(ln, "_variant_sale_amount", None)

    acts: List[SimpleNamespace] = []
    if vp:
        acts.append(_ns_action("percent_off", "line", vp))
    if va:
        acts.append(_ns_action("amount_off", "line", va))
    if not acts:
        return None

    return SimpleNamespace(
        name=f"VARIANT_SALE_{getattr(ln, 'variant_id', None)}",
        priority=999,
        exclusive=False,
        rules=[_ns_rule("variant_in", {"variant_ids": [getattr(ln, "variant_id", None)]})],
        actions=acts,
        is_active=True,
        starts_at=None,
        ends_at=None,
        channel=channel,
    )
def _ephemeral_from_product_line(ln, channel: str) -> Optional[SimpleNamespace]:
    if not getattr(ln, "_product_sale_active", False):
        return None
    pp = getattr(ln, "_product_sale_percent", None)
    pa = getattr(ln, "_product_sale_amount", None)

    acts: List[SimpleNamespace] = []
    if pp:
        acts.append(_ns_action("percent_off", "line", pp))
    if pa:
        acts.append(_ns_action("amount_off", "line", pa))
    if not acts:
        return None

    return SimpleNamespace(
        name=f"PRODUCT_SALE_{getattr(ln,'product_id', None)}",
        priority=998,
        exclusive=False,
        rules=[_ns_rule("product_in", {"product_ids": [getattr(ln, "product_id", None)]})],
        actions=acts,
        is_active=True,
        starts_at=None,
        ends_at=None,
        channel=channel,
    )

def build_ephemeral_campaigns_for_lines(lines, channel: str = "web") -> List[SimpleNamespace]:
    """
    Build ephemeral campaigns from per-line sale flags.
    Variant sales use `variant_in`, product sales use `product_in`.
    """
    camps: List[SimpleNamespace] = []
    for ln in lines:
        epi = _ephemeral_from_variant_line(ln, channel) or _ephemeral_from_product_line(ln, channel)
        if epi:
            camps.append(epi)
    return camps

# -----------------------------
# Services pricing
# -----------------------------
def compute_service_unit_price(*, service: Service, item_unit_price: Decimal) -> Decimal:
    """
    Derives the service unit price by either:
      1) Service.prices related table (tiered / fixed / percent_of_item)
      2) Simple fields on Service (price_type, amount)
    """
    def _calc(price_type: str, amount, lo=None, hi=None):
        pt = (price_type or "").strip()
        amt = Decimal(str(amount or "0"))
        if pt == "tiered_by_item_price":
            lo = Decimal(str(lo or "0"))
            hi = Decimal(str(hi or "999999999"))
            return amt if lo <= item_unit_price <= hi else None
        if pt in ("fixed", "per_unit_fixed"):
            return amt
        if pt == "percent_of_item":
            return (item_unit_price * amt / Decimal("100"))
        return None

    prices = getattr(service, "prices", None)
    if prices is not None:
        try:
            qs = prices.all() if hasattr(prices, "all") else list(prices)
        except Exception:
            qs = []
        tiered = [p for p in qs if getattr(p, "is_active", True) and getattr(p, "price_type", "") == "tiered_by_item_price"]
        others = [p for p in qs if getattr(p, "is_active", True) and getattr(p, "price_type", "") != "tiered_by_item_price"]

        for p in tiered:
            val = _calc(getattr(p, "price_type", ""), getattr(p, "amount", 0),
                        getattr(p, "item_price_min", None), getattr(p, "item_price_max", None))
            if val is not None:
                return val.quantize(Decimal("1."))
        for p in others:
            val = _calc(getattr(p, "price_type", ""), getattr(p, "amount", 0))
            if val is not None:
                return val.quantize(Decimal("1."))

    price_type = getattr(service, "price_type", None)
    amount = getattr(service, "amount", None)
    if price_type is not None and amount is not None:
        val = _calc(price_type, amount)
        if val is not None:
            return val.quantize(Decimal("1."))

    return Decimal("0")

def _build_service_line(*, service: Service, base_line, item_unit_price: Decimal, qty: int):
    """
    Creates a PricingLine for a service; excluded from discounts.
    """
    svc_unit = compute_service_unit_price(service=service, item_unit_price=item_unit_price) or Decimal("0")
    svc_unit = Decimal(str(svc_unit))

    per_item = getattr(service, "per_item", True)
    svc_qty = qty if per_item else 1

    return _new_pricing_line(
        product_id=getattr(base_line, "product_id"),
        category_id=getattr(base_line, "category_id"),
        unit_price=svc_unit,
        quantity=int(svc_qty),
        variant_id=getattr(base_line, "variant_id", None),
        brand_id=getattr(base_line, "brand_id", None),
        extra_category_ids=getattr(base_line, "extra_category_ids", []),
        _exclude_from_discounts=True,
    )

# -----------------------------
# Public wrappers
# -----------------------------
def build_pricing_line_public(item, qty: int = 1):
    return _build_pricing_line(item, qty)

def build_service_line_public(*, service, base_line, item_unit_price, qty: int):
    return _build_service_line(service=service, base_line=base_line,
                               item_unit_price=item_unit_price, qty=qty)
def price_single_product(item, qty: int = 1, coupons=None, channel: str = "web"):
    """
    Build one PricingLine for a product/variant, attach ephemeral sales,
    and evaluate with PricingEngine.
    """
    from promos.services.pricing import PricingEngine  # lazy import

    line = _build_pricing_line(item, qty)
    ctx = {"channel": channel, "coupons": coupons or []}

    # attach ephemeral campaigns (variant_in / product_in)
    epis = build_ephemeral_campaigns_for_lines([line], channel=channel)
    if epis:
        ctx["ephemeral_campaigns"] = epis

    return PricingEngine().evaluate([line], ctx)

