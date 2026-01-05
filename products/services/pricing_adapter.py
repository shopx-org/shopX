# products/services/pricing_adapter.py
from __future__ import annotations
from decimal import Decimal
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace
from typing import Optional, List
from django.utils import timezone

from products.models import Service
# موتور پرایسینگ را فقط وقتی لازم شد import می‌کنیم تا چرخه‌ی import نشود
from promos.services.pricing import PricingLine, PricingEngine
#
# -----------------------------
# Money / parsing helpers
# -----------------------------

def _is_within_window(starts_at, ends_at) -> bool:
    now = timezone.now()
    if starts_at and now < starts_at:
        return False
    if ends_at and now > ends_at:
        return False
    return True
#
# def _is_within_window(starts_at, ends_at) -> bool:
#     now = timezone.now()
#
#     def _aware(dt):
#         if not dt:
#             return None
#         # اگر naive بود، aware کن
#         if timezone.is_naive(dt):
#             return timezone.make_aware(dt, timezone.get_current_timezone())
#         return dt
#
#     starts_at = _aware(starts_at)
#     ends_at = _aware(ends_at)
#
#     if starts_at and now < starts_at:
#         return False
#     if ends_at and now > ends_at:
#         return False
#     return True


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
    This MUST match PricingLine dataclass in promos/services/pricing.py
    """

    # ------------------------
    # Variant branch
    # ------------------------
    if _is_variant(item):
        variant = item
        product = variant.product

        unit_price = _to_money(
            getattr(variant, "price", None) or getattr(product, "price", 0),
            fallback=0
        )

        # helpers for rules (safe)
        try:
            extra_cids = list(product.additional_categories.values_list("id", flat=True))
        except Exception:
            extra_cids = []

        # ✅ در پروژه‌ی تو اسم درست برند اینه:
        brand_id = getattr(product, "brand_fk_id", None)

        # ✅ PricingLine را فقط یکبار و استاندارد بساز
        line = _new_pricing_line(
            product_id=product.id,
            category_id=getattr(product, "category_id", None) or 0,
            unit_price=unit_price,
            quantity=int(qty or 1),
            variant_id=variant.id,
            brand_id=brand_id,
            extra_category_ids=extra_cids,
        )

        # --- Variant-level sale flags (✅ مطابق مدل تو) ---
        v_active = bool(getattr(variant, "sale_active_variant", False))
        v_percent_raw = getattr(variant, "sale_percent_variant", None)
        v_amount_raw  = getattr(variant, "sale_amount_variant", None)

        v_percent = Decimal(str(v_percent_raw)) if v_percent_raw not in (None, "") else None
        v_amount  = Decimal(str(v_amount_raw))  if v_amount_raw  not in (None, "") else None

        # اگر فیلد تاریخ برای variant نداری، همین None بمونه
        v_starts = getattr(variant, "sale_starts_at_variant", None)
        v_ends   = getattr(variant, "sale_ends_at_variant", None)

        for k, v in (
            ("_variant_sale_active", v_active),
            ("_variant_sale_percent", v_percent),
            ("_variant_sale_amount", v_amount),
            ("_variant_sale_starts_at", v_starts),
            ("_variant_sale_ends_at", v_ends),
        ):
            try:
                setattr(line, k, v)
            except Exception:
                pass

        # --- Product-level sale flags (✅ لازم برای fallback وقتی واریانت تخفیف ندارد) ---
        p_active = bool(getattr(product, "sale_active", False))
        p_percent_raw = getattr(product, "sale_percent", None)
        p_amount_raw  = getattr(product, "sale_amount", None)

        p_percent = Decimal(str(p_percent_raw)) if p_percent_raw not in (None, "") else None
        p_amount  = Decimal(str(p_amount_raw))  if p_amount_raw  not in (None, "") else None

        p_starts = getattr(product, "sale_starts_at", None)
        p_ends   = getattr(product, "sale_ends_at", None)

        for k, v in (
            ("_product_sale_active", p_active),
            ("_product_sale_percent", p_percent),
            ("_product_sale_amount", p_amount),
            ("_product_sale_starts_at", p_starts),
            ("_product_sale_ends_at", p_ends),
        ):
            try:
                setattr(line, k, v)
            except Exception:
                pass

        return line

    # ------------------------
    # Product branch
    # ------------------------
    product = item

    unit_price = _to_money(getattr(product, "price", None), fallback=0)

    try:
        extra_cids = list(product.additional_categories.values_list("id", flat=True))
    except Exception:
        extra_cids = []

    brand_id = getattr(product, "brand_fk_id", None)

    line = _new_pricing_line(
        product_id=product.id,
        category_id=getattr(product, "category_id", None) or 0,
        unit_price=unit_price,
        quantity=int(qty or 1),
        brand_id=brand_id,
        extra_category_ids=extra_cids,
    )

    # Product-level sale flags
    p_active = bool(getattr(product, "sale_active", False))
    p_percent_raw = getattr(product, "sale_percent", None)
    p_amount_raw  = getattr(product, "sale_amount", None)

    p_percent = Decimal(str(p_percent_raw)) if p_percent_raw not in (None, "") else None
    p_amount  = Decimal(str(p_amount_raw))  if p_amount_raw  not in (None, "") else None

    p_starts = getattr(product, "sale_starts_at", None)
    p_ends   = getattr(product, "sale_ends_at", None)

    for k, v in (
        ("_product_sale_active", p_active),
        ("_product_sale_percent", p_percent),
        ("_product_sale_amount", p_amount),
        ("_product_sale_starts_at", p_starts),
        ("_product_sale_ends_at", p_ends),
    ):
        try:
            setattr(line, k, v)
        except Exception:
            pass

    return line

def _new_pricing_line(
    *,
    product_id: int,
    category_id: int | None,
    unit_price: Decimal,
    quantity: int,
    variant_id: int | None = None,
    brand_id: int | None = None,
    extra_category_ids: list[int] | None = None,
    **extras,
):
    """
    Instantiate promos.services.pricing.PricingLine (dataclass) in a safe/consistent way.
    """

    from promos.services.pricing import PricingLine  # lazy import

    # normalize
    q = int(quantity or 1)
    if q < 1:
        q = 1

    cid = int(category_id or 0)

    # unit_price must be Decimal
    if not isinstance(unit_price, Decimal):
        unit_price = Decimal(str(unit_price or "0"))

    ecids = list(extra_category_ids or [])

    line = PricingLine(
        product_id=int(product_id),
        category_id=cid,
        unit_price=unit_price,
        quantity=q,
        variant_id=int(variant_id) if variant_id else None,
        brand_id=int(brand_id) if brand_id else None,
        extra_category_ids=ecids,
    )

    # allow attaching any extra runtime fields safely (e.g. sale flags timestamps)
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
        _is_ephemeral=True,
    )
def _ephemeral_from_product_line(ln, channel: str) -> Optional[SimpleNamespace]:
    if not getattr(ln, "_product_sale_active", False):
        return None

    if getattr(ln, "_variant_sale_active", False):
        return None
    starts_at = getattr(ln, "_product_sale_starts_at", None)
    ends_at   = getattr(ln, "_product_sale_ends_at", None)

    if not _is_within_window(starts_at, ends_at):
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
        starts_at=starts_at,
        ends_at=ends_at,
        channel=channel,
        _is_ephemeral=True,
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

