#   products/services/service_pricing.py
from __future__ import annotations
from decimal import Decimal

D0 = Decimal("0")
D100 = Decimal("100")
BIG = Decimal("999999999")

def compute_service_unit_price(*, service, item_unit_price: Decimal) -> Decimal:
    """
    قیمت «یک واحد» سرویس را محاسبه می‌کند (بدون ضرب در qty آیتم).
    از دو مسیر پشتیبانی می‌کند:
      1) service.prices  (ServicePrice با price_type: fixed / per_unit_fixed / percent_of_item / tiered_by_item_price)
      2) فیلدهای ساده روی خود Service: price_type, amount (و اختیاری per_item)
    """
    def _calc(pt: str, amount, lo=None, hi=None) -> Decimal | None:
        pt = (pt or "").strip()
        amt = Decimal(str(amount or "0"))
        if pt == "tiered_by_item_price":
            lo = Decimal(str(lo or "0")); hi = Decimal(str(hi or BIG))
            return amt if lo <= item_unit_price <= hi else None
        if pt in ("fixed", "per_unit_fixed"):
            return amt
        if pt == "percent_of_item":
            return (item_unit_price * amt / D100)
        return None

    # 1) اگر Service.prices داری
    prices_rel = getattr(service, "prices", None)
    if prices_rel is not None:
        try:
            prices = list(prices_rel.all()) if hasattr(prices_rel, "all") else list(prices_rel)
        except Exception:
            prices = []

        # تفکیک رکوردها بر اساس نوع قیمت‌گذاری
        tiered = [
            x for x in prices
            if getattr(x, "is_active", True)
               and getattr(x, "price_type", "") == "tiered_by_item_price"
        ]
        others = [
            x for x in prices
            if getattr(x, "is_active", True)
               and getattr(x, "price_type", "") != "tiered_by_item_price"
        ]

        # اول پلکانی‌ها (tiered)
        for p in tiered:
            val = _calc(
                getattr(p, "price_type", ""),
                getattr(p, "amount", 0),
                getattr(p, "item_price_min", None),
                getattr(p, "item_price_max", None),
            )
            if val is not None:
                return val.quantize(Decimal("1."))

        # سپس سایر انواع (fixed / percent / per_unit_fixed)
        for p in others:
            val = _calc(
                getattr(p, "price_type", ""),
                getattr(p, "amount", 0),
            )
            if val is not None:
                return val.quantize(Decimal("1."))

    # ---- مسیر 2: فیلدهای ساده روی خود Service (Fallback) ----
    price_type = getattr(service, "price_type", None)
    amount = getattr(service, "amount", None)
    if price_type is not None and amount is not None:
        val = _calc(price_type, amount)
        if val is not None:
            return val.quantize(Decimal("1."))

    # اگر هیچ قاعده‌ای نبود، پیش‌فرض صفر
    return D0