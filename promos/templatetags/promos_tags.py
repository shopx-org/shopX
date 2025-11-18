# promos/templatetags/promos_tags.py
from django import template
from decimal import Decimal
from promos.services.pricing import PricingEngine, PricingLine
from products.services.pricing_adapter import price_single_product  # ← استفاده از آداپتر
register = template.Library()
from promos.models import PromoBanner
from django.utils import timezone


# promos/templatetags/promos_tags.py
from django import template
from django.utils import timezone
from promos.models import PromoBanner

register = template.Library()

@register.simple_tag
def promo_banners(position="hero", channel="web", limit=7):
    """
    بنرهای فعال برای یک position خاص را برمی‌گرداند.
    فقط بنرهایی که:
      - is_active=True
      - در بازه زمانی خودشان هستند
      - اگر کمپین دارند، خود کمپین هم is_running باشد
    """
    now = timezone.now()
    qs = PromoBanner.objects.filter(
        position=position,
        channel=channel,
        is_active=True,
    ).select_related("campaign")

    banners = [b for b in qs if b.is_running(now)]
    return banners[:limit]

@register.simple_tag(takes_context=True)
def effective_price(context, product, qty=1, channel="web"):
    """
    استفاده: {% effective_price product 1 "web" %}
    تلاش می‌کند فیلدها را با چند نام مرسوم پیدا کند:
      - id
      - price / final_price / sale_price
      - category_id یا category.id
      - brand_id یا brand.id (اختیاری؛ اگر در PricingLine تعریف کرده‌ای)
    """
    request = context.get("request")
    coupons = request.session.get("coupons", []) if request else []

    pid = _pick_attr(product, "id")
    if pid is None:
        return ""  # یا 0

    # قیمت: ابتدا final_price بعد price
    price = _pick_attr(product, "final_price", "sale_price", "price", default=0)
    try:
        price = Decimal(str(price))
    except Exception:
        price = Decimal("0")

    # دسته: category_id یا category.id
    cid = _pick_attr(product, "category_id", default=None)
    if cid is None:
        cat = _pick_attr(product, "category", default=None)
        cid = getattr(cat, "id", None)

    # برند (اختیاری—اگر در PricingLine فیلد brand_id اضافه کرده‌ای)
    bid = _pick_attr(product, "brand_id", default=None)
    if bid is None:
        brand = _pick_attr(product, "brand", default=None)
        bid = getattr(brand, "id", None)

    # اگر PricingLine شما brand_id ندارد، این پارامتر را حذف کنید
    try:
        line = PricingLine(
            product_id=int(pid),
            category_id=int(cid) if cid is not None else 0,
            unit_price=price,
            quantity=int(qty),
            # brand_id=bid,  ← فقط اگر در PricingLine تعریف کرده‌ای
        )
    except Exception:
        return ""

    res = PricingEngine().evaluate([line], {"channel": channel, "coupons": coupons})
    return res.total

@register.simple_tag(takes_context=True)
def effective_price(context, product, qty=1, channel="web"):
    request = context.get("request")
    coupons = request.session.get("coupons", []) if request else []
    res = price_single_product(product, int(qty), coupons=coupons, channel=channel)
    return res.total