# promos/templatetags/promos_tags.py
from django import template
from django.utils import timezone
from django.db.models import Q

from promos.models import PromoBanner
from products.services.pricing_adapter import price_single_product

register = template.Library()


@register.simple_tag
def promo_banners(position="hero", channel="web", limit=7):
    """
    بنرهای فعال برای یک position خاص را برمی‌گرداند.
    - is_active=True
    - در بازه زمانی خودشان باشند
    - اگر کمپین دارند، کمپین هم is_running باشد (با is_running چک می‌شود)
    - بر اساس priority (کمتر=بالاتر) مرتب می‌شود
    """
    now = timezone.now()
    limit = int(limit)

    qs = (
        PromoBanner.objects.select_related("campaign")
        .filter(position=position, channel=channel, is_active=True)
        .filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now))
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gte=now))
        .order_by("priority", "-updated_at")
    )

    # چون is_running کمپین را هم چک می‌کند، این لایه را نگه می‌داریم
    banners = []
    # کمی بیشتر می‌گیریم که اگر چندتا به خاطر کمپین رد شدن، باز هم limit پر بشه
    prefetch_n = max(limit * 3, 20)
    for b in qs[:prefetch_n]:
        if b.is_running(now):
            banners.append(b)
            if len(banners) >= limit:
                break

    return banners


@register.simple_tag(takes_context=True)
def effective_price(context, product, qty=1, channel="web"):
    """
    استفاده: {% effective_price product 1 "web" %}
    قیمت موثر را با Pricing Adapter پروژه برمی‌گرداند (بهترین و تمیزترین حالت).
    """
    request = context.get("request")
    coupons = request.session.get("coupons", []) if request else []
    res = price_single_product(product, int(qty), coupons=coupons, channel=channel)
    return res.total


#
# register = template.Library()
#
# @register.simple_tag
# def promo_banners(position="hero", channel="web", limit=7):
#     """
#     بنرهای فعال برای یک position خاص را برمی‌گرداند.
#     فقط بنرهایی که:
#       - is_active=True
#       - در بازه زمانی خودشان هستند
#       - اگر کمپین دارند، خود کمپین هم is_running باشد
#     """
#     now = timezone.now()
#     qs = PromoBanner.objects.filter(
#         position=position,
#         channel=channel,
#         is_active=True,
#     ).select_related("campaign")
#
#     banners = [b for b in qs if b.is_running(now)]
#     return banners[:limit]
#
# @register.simple_tag(takes_context=True)
# def effective_price(context, product, qty=1, channel="web"):
#     """
#     استفاده: {% effective_price product 1 "web" %}
#     تلاش می‌کند فیلدها را با چند نام مرسوم پیدا کند:
#       - id
#       - price / final_price / sale_price
#       - category_id یا category.id
#       - brand_id یا brand.id (اختیاری؛ اگر در PricingLine تعریف کرده‌ای)
#     """
#     request = context.get("request")
#     coupons = request.session.get("coupons", []) if request else []
#
#     pid = _pick_attr(product, "id")
#     if pid is None:
#         return ""  # یا 0
#
#     # قیمت: ابتدا final_price بعد price
#     price = _pick_attr(product, "final_price", "sale_price", "price", default=0)
#     try:
#         price = Decimal(str(price))
#     except Exception:
#         price = Decimal("0")
#
#     # دسته: category_id یا category.id
#     cid = _pick_attr(product, "category_id", default=None)
#     if cid is None:
#         cat = _pick_attr(product, "category", default=None)
#         cid = getattr(cat, "id", None)
#
#     # برند (اختیاری—اگر در PricingLine فیلد brand_id اضافه کرده‌ای)
#     bid = _pick_attr(product, "brand_id", default=None)
#     if bid is None:
#         brand = _pick_attr(product, "brand", default=None)
#         bid = getattr(brand, "id", None)
#
#     # اگر PricingLine شما brand_id ندارد، این پارامتر را حذف کنید
#     try:
#         line = PricingLine(
#             product_id=int(pid),
#             category_id=int(cid) if cid is not None else 0,
#             unit_price=price,
#             quantity=int(qty),
#             # brand_id=bid,  ← فقط اگر در PricingLine تعریف کرده‌ای
#         )
#     except Exception:
#         return ""
#
#     res = PricingEngine().evaluate([line], {"channel": channel, "coupons": coupons})
#     return res.total
#
# @register.simple_tag(takes_context=True)
# def effective_price(context, product, qty=1, channel="web"):
#     request = context.get("request")
#     coupons = request.session.get("coupons", []) if request else []
#     res = price_single_product(product, int(qty), coupons=coupons, channel=channel)
#     return res.total