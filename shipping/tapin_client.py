# # shipping/tapin_client.py
# import requests
# from decimal import Decimal
# from shipping.models import TapinConfig, ShippingMethod
#
#
# # -----------------------------
# # محاسبه وزن و ارزش کل از cart
# # -----------------------------
# def compute_order_weight_and_value(cart) -> tuple[int, int]:
#     """
#     خروجی:
#       total_weight (گرم)
#       total_value_rial (ریال)
#     """
#     total_weight = 0
#     total_value_rial = 0
#
#     for row in cart:
#         qty = row.get("quantity", 1)
#         weight_gram = row.get("weight_gram", 0)
#
#         # قیمت واحد به تومان
#         unit_price_toman = Decimal(row.get("unit_price") or 0)
#         unit_price_rial = int(unit_price_toman * 10)  # تبدیل تومان → ریال
#
#         total_weight += weight_gram * qty
#         total_value_rial += unit_price_rial * qty
#
#     return total_weight, total_value_rial
#
#
# # ================================
# #   API — پست سفارشی / پیشتاز
# # ================================
# TAPIN_PUBLIC_CHECK_PRICE_URL = "https://public.api.tapin.ir/api/v1/public/check-price/"
#
#
# class TapinPostError(Exception):
#     pass
#
#
# def tapin_post_check_price(*, cart, shipping_address, method: ShippingMethod) -> int:
#     """
#     method.carrier == "post"
#     method.tapin_post_service_type:
#         0 = سفارشی
#         1 = پیشتاز
#
#     خروجی → هزینه ارسال (ریال)
#     """
#     cfg = TapinConfig.objects.first()
#     if not cfg:
#         raise TapinPostError("TapinConfig تنظیم نشده است.")
#
#     if method.carrier != "post":
#         raise TapinPostError("این روش ارسال از نوع پست نیست.")
#
#     if method.tapin_post_service_type is None:
#         raise TapinPostError("فیلد tapin_post_service_type تنظیم نشده است.")
#
#     order_type = method.tapin_post_service_type  # ۰ یا ۱
#
#     weight, value_rial = compute_order_weight_and_value(cart)
#
#     payload = {
#         "rate_type": "tapin",
#         "price": value_rial,
#         "weight": weight,
#         "order_type": order_type,
#         "pay_type": 1,  # پرداخت آنلاین
#         "to_province": shipping_address.tapin_province_id,
#         "from_province": cfg.from_province_id,
#         "to_city": shipping_address.tapin_city_id,
#         "from_city": cfg.from_city_id,
#         "box_id": cfg.default_box_id,
#     }
#
#     try:
#         resp = requests.post(TAPIN_PUBLIC_CHECK_PRICE_URL, json=payload, timeout=10)
#         resp.raise_for_status()
#     except Exception as e:
#         raise TapinPostError(f"خطا در برقراری ارتباط با تاپین: {e}")
#
#     data = resp.json()
#     returns = data.get("returns") or {}
#
#     if returns.get("status") != 200:
#         raise TapinPostError(returns.get("message", "خطا در استعلام قیمت پست"))
#
#     entries = data.get("entries") or {}
#     total_rial = int(entries.get("total", 0))
#
#     return total_rial
#
#
# # ====================================
# #   API — تیپاکس از طریق تاپین
# # ====================================
# TIPAX_CHECK_PRICE_URL = "https://my.tapin.ir/api/v4/tipax/public/user/order/check-price/"
#
#
# class TapinTipaxError(Exception):
#     pass
#
#
# def tapin_tipax_check_price(*, cart, shipping_address, method: ShippingMethod) -> int:
#     """
#     method.carrier باید 'tipax' باشد.
#     خروجی → هزینه ارسال تیپاکس (ریال)
#     """
#     cfg = TapinConfig.objects.first()
#     if not cfg:
#         raise TapinTipaxError("TapinConfig تنظیم نشده است.")
#
#     if method.carrier != "tipax":
#         raise TapinTipaxError("این روش ارسال از نوع تیپاکس نیست.")
#
#     weight, value_rial = compute_order_weight_and_value(cart)
#
#     # تبدیل cart به ساختار مورد نیاز تاپین
#     products = []
#     for row in cart:
#         qty = row.get("quantity", 1)
#         weight_gram = row.get("weight_gram", 0)
#         unit_price_toman = Decimal(row.get("unit_price") or 0)
#         unit_price_rial = int(unit_price_toman * 10)
#
#         products.append({
#             "count": qty,
#             "count_per_weight": weight_gram,
#             "count_per_amount": unit_price_rial,
#             "count_per_discount": 0,
#         })
#
#     payload = {
#         "id_shop": str(cfg.tipax_shop_id or cfg.shop_id),
#         "id_province_receiver": shipping_address.tapin_province_id,
#         "id_city_receiver": shipping_address.tapin_city_id,
#         "product_type_id": cfg.tipax_product_type_id,
#         "id_type_packing": cfg.tipax_packing_type_id,
#         "type_payment": cfg.tipax_payment_type,
#         "type_service": cfg.tipax_service_type,
#         "type_delivery": cfg.tipax_delivery_type,
#         "type_pickup": cfg.tipax_pickup_type,
#         "length": None,
#         "width": None,
#         "height": None,
#         "products": products,
#         "weight_package": 0,
#     }
#
#     headers = {
#         "Authorization": f"Token {cfg.api_token}",
#         "Content-Type": "application/json",
#     }
#
#     try:
#         resp = requests.post(TIPAX_CHECK_PRICE_URL, json=payload, headers=headers, timeout=10)
#         resp.raise_for_status()
#     except Exception as e:
#         raise TapinTipaxError(f"خطا در ارتباط با تیپاکس/تاپین: {e}")
#
#     data = resp.json()
#     returns = data.get("returns") or {}
#
#     if returns.get("status") not in (200, 20, 21):
#         raise TapinTipaxError(returns.get("message", "خطا در استعلام قیمت تیپاکس"))
#
#     entries = data.get("entries") or {}
#
#     # خروجی معتبر:
#     total_rial = int(
#         entries.get("total_receive_price")
#         or entries.get("price_send_total")
#         or 0
#     )
#
#     return total_rial
