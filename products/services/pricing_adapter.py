from decimal import Decimal
from typing import Iterable, List, Dict
from django.db.models import QuerySet
from promos.services.pricing import PricingEngine, PricingLine

def build_pricing_line_from_product(product, qty: int = 1) -> PricingLine:
    """
    Product → PricingLine
    - category_id: دسته اصلی
    - extra_category_ids: دسته‌های اضافی (برای Ruleهای category_in)
    - brand_id: از brand_fk
    """
    # دسته‌های اضافی (ممکن است خالی باشد)
    extra_cids = list(product.additional_categories.values_list("id", flat=True))
    brand_id = product.brand_fk_id  # ممکن است None باشد

    return PricingLine(
        product_id=product.id,
        category_id=product.category_id,
        unit_price=Decimal(str(product.price)),
        quantity=int(qty),
        brand_id=brand_id,
        extra_category_ids=extra_cids,
    )

def price_single_product(product, qty: int, coupons: list[str] | None = None, channel: str = "web"):
    line = build_pricing_line_from_product(product, qty)
    res = PricingEngine().evaluate([line], {"channel": channel, "coupons": coupons or []})
    return res

def price_cart_items(items: Iterable[Dict], coupons: list[str] | None = None, channel: str = "web"):
    """
    items: iterable از دیکشنری‌های
      {"product": Product, "qty": 2}
    """
    lines: List[PricingLine] = []
    for it in items:
        p, q = it["product"], int(it.get("qty", 1))
        lines.append(build_pricing_line_from_product(p, q))
    engine = PricingEngine()
    return engine.evaluate(lines, {"channel": channel, "coupons": coupons or []})
