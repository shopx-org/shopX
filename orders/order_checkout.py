# orders/order_checkout.py
from decimal import Decimal
from typing import Optional

from django.contrib.auth import get_user_model

from cart.cart import Cart
from products.models import Product, ProductVariant
from promos.services.pricing import PricingEngine
from .models import Order, OrderItem
from shipping.models import ShippingMethod, Address

User = get_user_model()


def create_order_from_cart(
    *,
    cart: Cart,
    user: Optional[User],
    address: Address,
    shipping_method: Optional[ShippingMethod] = None,
    shipping_price: Decimal = Decimal("0"),
) -> Order:
    """
    سبد فعلی + نتیجه‌ی موتور قیمت‌گذاری را می‌گیرد
    و یک Order + OrderItem ها را می‌سازد.

    نکته: فعلاً فیلدهای خود Order همون subtotal / total_discount / total هست.
    total = total(بعد از تخفیف) + هزینه‌ی ارسال
    """

    # --- 1) گرفتن نتیجه‌ی قیمت‌گذاری از خود Cart ---
    pricing_result = cart.pricing_result()  # نوع: PricingResult

    subtotal = pricing_result.subtotal
    total_discount = pricing_result.total_discount
    total_after_discounts = pricing_result.total   # مجموع بعد از تخفیف‌های پرومو
    shipping_price = Decimal(shipping_price or 0)

    order = Order.objects.create(
        user=user if (user and getattr(user, "is_authenticated", False)) else None,
        address=address,
        shipping_method=shipping_method,
        shipping_price=shipping_price,
        subtotal=subtotal,
        total_discount=total_discount,
        total=total_after_discounts + shipping_price,
    )

    # --- 3) ساخت OrderItem ها بر اساس خطوط PricingResult ---
    # pricing_result.lines لیست PricingLine است.
    for line in pricing_result.lines:
        # اگر یک روز سرویس‌های خاص (بدون product_id) اضافه کردی، اینجا می‌تونی ردشون کنی
        if not line.product_id:
            continue

        product = Product.objects.get(id=line.product_id)
        variant = None
        if line.variant_id:
            variant = ProductVariant.objects.filter(id=line.variant_id).first()

        qty = line.quantity
        unit_price = line.unit_price
        line_discount = line.line_discount
        line_total = line.line_subtotal - line_discount

        OrderItem.objects.create(
            order=order,
            product=product,
            variant=variant,
            qty=qty,
            unit_price=unit_price,
            discount=line_discount,
            total=line_total,
            product_name=product.name,  # اسنپ‌شات
        )

    return order
