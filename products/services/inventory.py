# products/services/inventory.py
from __future__ import annotations
from django.db.models import Sum
from django.db import transaction
from django.db.models import F

from cart.cart import Cart
from products.models import Product, ProductVariant

@transaction.atomic
def consume_stock_for_cart(cart: Cart) -> None:
    """
    بعد از پرداخت موفق، برای هر آیتم سبد موجودی را کم می‌کند.

    - اگر واریانت وجود داشته باشد -> از Variant.stock کم می‌کند.
    - اگر محصول ساده‌ای باشد که خود Product.stock دارد -> از آن کم می‌کند.
    """
    for it in cart.items():  # it: SimpleNamespace(product, variant, qty, services, unit_price, ...)
        qty = int(getattr(it, "qty", 1) or 1)
        if qty <= 0:
            continue

        variant = getattr(it, "variant", None)
        product = getattr(it, "product", None)

        # ۱) محصول واریانت‌دار → از موجودی همان واریانت کم کن
        if variant is not None and hasattr(variant, "stock"):
            updated = (
                ProductVariant.objects
                .filter(pk=variant.pk, stock__gte=qty)  # جلوگیری از منفی شدن
                .update(stock=F("stock") - qty)
            )
            if updated == 0:
                # این‌جا می‌تونی به‌جای Exception، لاگ کنی یا پیام خطا ذخیره کنی
                raise ValueError(f"Not enough stock for variant id={variant.pk}")

        # ۲) محصول بدون واریانت → اگر Product.stock داری، از خودش کم کن
        elif product is not None and hasattr(product, "stock"):
            updated = (
                Product.objects
                .filter(pk=product.pk, stock__gte=qty)
                .update(stock=F("stock") - qty)
            )
            if updated == 0:
                raise ValueError(f"Not enough stock for product id={product.pk}")




def is_product_in_stock(product: Product) -> bool:
    """
    True اگر:
    - محصول واریانت دارد و مجموع stock واریانت‌ها > 0 باشد
    - یا محصول ساده است و Product.stock > 0 باشد
    """
    # اگر واریانت دارد
    if hasattr(product, "variants"):
        total = product.variants.aggregate(s=Sum("stock"))["s"] or 0
        return total > 0

    # محصول ساده
    if hasattr(product, "stock"):
        return (product.stock or 0) > 0
    return True