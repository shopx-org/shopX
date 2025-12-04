# # shipping/services.py
# from typing import List, Dict, Any
# from decimal import Decimal
#
# from django.conf import settings
#
# from cart.cart import Cart
# from .models import Address
# from .amadast_client import AmadastAPI, AmadastAPIError
#
#
# def compute_cart_weight_grams(cart: Cart) -> int:
#     total = 0
#     for row in cart.items():
#         product = row.product
#         variant = getattr(row, "variant", None)
#         qty = getattr(row, "qty", 0)
#
#         if getattr(product, "is_digital", False):
#             continue
#
#         if variant is not None and hasattr(variant, "shipping_weight_grams"):
#             w = variant.shipping_weight_grams
#         elif hasattr(product, "get_default_weight_grams"):
#             w = product.get_default_weight_grams()
#         else:
#             w = 0
#
#         w = int(w or 0)
#         total += w * qty
#
#     return total
#
#
# def compute_cart_value_toman(cart: Cart) -> int:
#     pr = cart.pricing_result()
#     return int(pr.total)
#
#
# def get_shipping_quotes_for_cart(cart: Cart, address: Address) -> List[Dict[str, Any]]:
#     weight = compute_cart_weight_grams(cart)
#     value = compute_cart_value_toman(cart)
#
#     if weight <= 0:
#         return [{
#             "code": "digital_only",
#             "name": "بدون ارسال (محصولات دیجیتال)",
#             "price": 0,
#             "eta_days_min": None,
#             "eta_days_max": None,
#         }]
#
#     origin_postal = settings.SHOP_ORIGIN_POSTAL_CODE
#     if not origin_postal:
#         # می‌تونی اینجا هم برای حالت لوکال یه مقدار تستی برگردونی
#         origin_postal = address.postal_code or "0000000000"
#
#     api = AmadastAPI()
#
#     try:
#         raw = api.get_quote(
#             origin_postal_code=origin_postal,
#             dest_postal_code=address.postal_code,
#             weight_grams=weight,
#             value=value,
#         )
#     except AmadastAPIError as e:
#         # ⬅️ اینجا نذاریم ۵۰۰ بده؛ یه خروجی دمو برای تست فرانت
#         if settings.DEBUG:
#             return [
#                 {
#                     "code": "demo_pishtaz",
#                     "name": "پست پیشتاز (دمو)",
#                     "price": 45000,
#                     "eta_days_min": 2,
#                     "eta_days_max": 3,
#                 },
#                 {
#                     "code": "demo_safareshi",
#                     "name": "پست سفارشی (دمو)",
#                     "price": 30000,
#                     "eta_days_min": 4,
#                     "eta_days_max": 6,
#                 },
#             ]
#         return []
#
#     if raw.get("status") != "success":
#         return []
#
#     services = raw.get("data", []) or []
#
#     normalized: List[Dict[str, Any]] = []
#     for s in services:
#         normalized.append(
#             {
#                 "code": s.get("service") or s.get("code"),
#                 "name": s.get("title") or s.get("name"),
#                 "price": int(s.get("price") or 0),
#                 "eta_days_min": s.get("eta_min"),
#                 "eta_days_max": s.get("eta_max"),
#                 "raw": s,
#             }
#         )
#
#     return normalized
