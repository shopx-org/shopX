# products/services/pricing_adapter.py
from decimal import Decimal
from types import SimpleNamespace
from django.utils import timezone
from products.models import Service
from promos.services import pricing
from products.services.service_pricing import compute_service_unit_price  # ← این ایمپورت لازم است
from decimal import Decimal, InvalidOperation

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٬, ", "0123456789,, ")  # کاما/فاصله هم نرمال

def _to_money(val, *, fallback="0"):
    """
    ورودی‌های None/''/'None'/اعداد فارسی/با کاما را امن به Decimal تبدیل می‌کند.
    اگر نتوانست، به fallback می‌افتد.
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

def _is_variant(item) -> bool:
    return hasattr(item, "product_id") and getattr(item, "product_id") is not None

def _build_pricing_line(item, qty: int = 1):
    from promos.services.pricing import PricingLine  # lazy

    if _is_variant(item):
        variant = item
        product = variant.product
        raw_unit = variant.price if getattr(variant, "price", None) not in ("", None) else getattr(product, "price",
                                                                                                   None)
        unit_price = _to_money(raw_unit, fallback=getattr(product, "price", 0) or 0)

        # کتگوری‌های اضافه/برند از محصول
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
        # فیلدهای کمکی
        for name, val in (
            ("variant_id", variant.id),
            ("brand_id", brand_id),
            ("extra_category_ids", extra_cids),
        ):
            try: setattr(line, name, val)
            except Exception: pass

        # فیلدهای SALE واریانت (اگر تعریف کرده‌ای)
        v_active  = getattr(variant, "sale_active_variant", False)
        v_percent = getattr(variant, "sale_percent_variant", None)
        v_amount  = getattr(variant, "sale_amount_variant", None)
        for name, val in (
            ("_variant_sale_active", bool(v_active)),
            ("_variant_sale_percent", Decimal(str(v_percent)) if v_percent not in (None, "") else None),
            ("_variant_sale_amount",  Decimal(str(v_amount))  if v_amount  not in (None, "") else None),
        ):
            try: setattr(line, name, val)
            except Exception: pass

        return line

    # --- Product ---
    product = item
    unit_price = _to_money(getattr(product, "price", None), fallback=0)
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
    for name, val in (
        ("brand_id", brand_id),
        ("extra_category_ids", extra_cids),
    ):
        try: setattr(line, name, val)
        except Exception: pass

    # فیلدهای SALE محصول (اگر داری)
    p_active  = getattr(product, "sale_active", False)
    p_percent = getattr(product, "sale_percent", None)
    p_amount  = getattr(product, "sale_amount", None)
    for name, val in (
        ("_product_sale_active", bool(p_active)),
        ("_product_sale_percent", Decimal(str(p_percent)) if p_percent not in (None, "") else None),
        ("_product_sale_amount",  Decimal(str(p_amount))  if p_amount  not in (None, "") else None),
    ):
        try: setattr(line, name, val)
        except Exception: pass

    return line


def _ephemeral_from_variant_line(line):
    active = getattr(line, "_variant_sale_active", False)
    pct = getattr(line, "_variant_sale_percent", None)
    amt = getattr(line, "_variant_sale_amount", None)
    if not active or (pct in (None, "") and amt in (None, "")):
        return None
    acts = [SimpleNamespace(kind=("percent_off" if pct is not None else "amount_off"),
                            scope="line", value=pct if pct is not None else amt, cap=None)]
    rules = [SimpleNamespace(kind="product_in", payload={"product_ids": [line.product_id]})]
    return SimpleNamespace(
        id=f"variant-sale-{getattr(line,'variant_id','x')}",
        name=f"VariantSale({getattr(line,'variant_id','x')})",
        is_active=True, starts_at=timezone.now(), ends_at=timezone.now(),
        exclusive=False, priority=10000, channel="web",
        actions=acts, rules=rules,
    )


def _ephemeral_from_product_line(line):
    active = getattr(line, "_product_sale_active", False)
    pct = getattr(line, "_product_sale_percent", None)
    amt = getattr(line, "_product_sale_amount", None)
    if not active or (pct in (None, "") and amt in (None, "")):
        return None
    acts = [SimpleNamespace(kind=("percent_off" if pct is not None else "amount_off"),
                            scope="line", value=pct if pct is not None else amt, cap=None)]
    rules = [SimpleNamespace(kind="product_in", payload={"product_ids": [line.product_id]})]
    return SimpleNamespace(
        id=f"product-sale-{line.product_id}",
        name=f"ProductSale({line.product_id})",
        is_active=True, starts_at=timezone.now(), ends_at=timezone.now(),
        exclusive=False, priority=9999, channel="web",
        actions=acts, rules=rules,
    )


def price_single_product(item, qty: int = 1, coupons=None, channel="web"):
    from promos.services.pricing import PricingEngine  # lazy

    line = _build_pricing_line(item, qty)
    ctx = {"channel": channel, "coupons": coupons or []}

    # اولویت با فروشِ واریانت؛ اگر نبود، فروشِ محصول
    epi = _ephemeral_from_variant_line(line) or _ephemeral_from_product_line(line)
    if epi:
        ctx["ephemeral_campaigns"] = [epi]

    return PricingEngine().evaluate([line], ctx)

from decimal import Decimal

def compute_service_unit_price(*, service, item_unit_price: Decimal) -> Decimal:
    """
    قیمت سرویس را از یکی از این دو منبع می‌خواند:
      1) service.prices (اگر مدل ServicePrice دارید)
      2) فیلدهای ساده روی خود Service: price_type, amount (اگر تعریف کرده باشید)
    خروجی: قیمت واحد سرویس (بدون ضرب در qty آیتم)
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

    # 1) اگر Service.prices دارید (RelatedManager)
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

    # 2) فیلدهای ساده روی خود Service (اگر داری: price_type, amount)
    price_type = getattr(service, "price_type", None)
    amount = getattr(service, "amount", None)
    if price_type is not None and amount is not None:
        val = _calc(price_type, amount)
        if val is not None:
            return val.quantize(Decimal("1."))

    return Decimal("0")

def _build_service_line(*, service: Service, base_line, item_unit_price: Decimal, qty: int):
    """
    base_line = همون PricingLine مربوط به محصول/واریانت برای ارث گرفتن category_id/brand_id
    """
    from promos.services.pricing import PricingLine  # lazy

    svc_unit = compute_service_unit_price(service=service, item_unit_price=item_unit_price) or Decimal("0")
    svc_unit = Decimal(str(svc_unit))
    if svc_unit is None:
        svc_unit = Decimal("0")

    # اگر سرویس per_item است، تعداد برابر qty؛ وگرنه 1 (می‌تونی از خود Service بخوانی)
    per_item = getattr(service, "per_item", True)
    svc_qty = qty if per_item else 1

    # category_id را مشابه محصول می‌گذاریم (برای گزارش/تحلیل). تخفیف روی آن پخش نمی‌شود چون exclude=True
    return PricingLine(
        product_id=base_line.product_id,
        category_id=base_line.category_id,
        unit_price=svc_unit,
        quantity=int(svc_qty),
        variant_id=getattr(base_line, "variant_id", None),
        brand_id=getattr(base_line, "brand_id", None),
        extra_category_ids=getattr(base_line, "extra_category_ids", []),
        _exclude_from_discounts=True,  # سرویس‌ها از تخفیف خطی سهم نگیرند
    )


# --- public wrappers so callers don't touch "protected" names ---
def build_pricing_line_public(item, qty: int = 1):
    return _build_pricing_line(item, qty)

def build_service_line_public(*, service, base_line, item_unit_price, qty: int):
    return _build_service_line(service=service, base_line=base_line,
                               item_unit_price=item_unit_price, qty=qty)

def build_ephemeral_campaigns_for_lines(lines, channel="web"):
    """
    برای هر خط، اگر فیلدهای _variant_sale_* یا _product_sale_* فعال باشند،
    یک کمپین موقتی معادل می‌سازیم تا PricingEngine همان‌طور که در صفحه‌ی
    دیتیل عمل می‌کند، اینجا هم تخفیف را اعمال کند.
    """
    camps = []
    for ln in lines:
        epi = _ephemeral_from_variant_line(ln) or _ephemeral_from_product_line(ln)
        if epi:
            # اطمینان از کانال
            try:
                setattr(epi, "channel", channel)
            except Exception:
                pass
            camps.append(epi)
    return camps
