# cart/context_processors.py
from decimal import Decimal

from .cart import Cart
from .views import _build_lines_with_gids, _pricing_ctx_for, _row_payload, _summary_payload, _first_image_url
from promos.services.pricing import PricingEngine
from products.services.pricing_adapter import build_ephemeral_campaigns_for_lines


def cart_badge(request):
    try:
        return {"cart_count": Cart(request).items_count()}
    except Exception:
        return {"cart_count": 0}


def mini_cart(request):
    """
    مینی‌کارت هدر: لیست آیتم‌ها + قیمت نهایی + درصد تخفیف
    """
    try:
        cart = Cart(request)

        # داشتن خطوط پرایسینگ همراه gid برای هر ردیف
        lines, groups = _build_lines_with_gids(cart)

        ctx = _pricing_ctx_for(request)
        eps = build_ephemeral_campaigns_for_lines(lines, channel=ctx.get("channel", "web"))
        if eps:
            ctx["ephemeral_campaigns"] = eps

        result = PricingEngine().evaluate(lines, ctx)

        # خلاصه‌ی سبد برای مجموع
        summary = _summary_payload(result, request)
        total = summary.get("total", 0.0)

        items = []

        for gid, it in groups:
            row_sum = _row_payload(result, gid) or {
                "subtotal": 0.0,
                "discount": 0.0,
                "total": 0.0,
                "discount_percent": 0,
            }

            qty = getattr(it, "qty", 1) or 1

            # قیمت واحد قبل و بعد از تخفیف
            sub = Decimal(str(row_sum["subtotal"]))
            tot = Decimal(str(row_sum["total"]))

            unit_before = (sub / qty).quantize(Decimal("1."))   # قیمت قبل (برای خط زدن/نمایش درصد)
            unit_after  = (tot / qty).quantize(Decimal("1."))   # قیمت نهایی بعد از تخفیف

            product_obj = it.variant or it.product

            # عکس
            # برای عکس، همیشه از خود Product استفاده کن
            base_product = getattr(product_obj, "product", product_obj)
            color_name = ""
            color_code = ""

            variant = getattr(it, "variant", None)
            if variant is not None:
                # اگر واریانت فیلدی به اسم color یا color_group دارد
                color_obj = getattr(variant, "color", None) or getattr(variant, "color_group", None)
                if color_obj:
                    # name از مدل Color
                    color_name = getattr(color_obj, "name", "")
                    # hex_code همون فیلدی که در مدل Color تعریف کردی
                    color_code = getattr(color_obj, "hex_code", "") or ""

            try:
                image_url = _first_image_url(base_product) or ""
            except Exception:
                image_url = ""
            # لینک محصول
            url = ""
            try:
                if hasattr(product_obj, "get_absolute_url"):
                    url = product_obj.get_absolute_url()
            except Exception:
                pass

            discount_percent = int(row_sum.get("discount_percent") or 0)
            items.append({
                "name": getattr(product_obj, "name", str(product_obj)),
                "qty": qty,
                "image": image_url,
                "url": url,
                "color_name": color_name,
                "color_code": color_code,
                "unit_price_before": unit_before,
                "unit_price_after": unit_after,
                "discount_percent": discount_percent,
            })

        return {
            "mini_cart_items": items,
            "mini_cart_total": total,
        }

    except Exception:
        # اگر هر مشکلی بود، سبد خالی
        return {
            "mini_cart_items": [],
            "mini_cart_total": 0,
        }
