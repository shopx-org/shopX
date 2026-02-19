# search/api_views.py
from django.http import JsonResponse
from django.views import View
from django.core.paginator import Paginator
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum, Value, IntegerField
from django.db.models.functions import Coalesce
from django.db.models import Prefetch

from products.models import Product, ProductVariant
from .services import ProductSearchService

# ✅ این 3 تا import رو دقیقاً مثل products/views.py خودت تنظیم کن
from promos.services.pricing import PricingEngine
from products.services.pricing_adapter import build_pricing_line_public, build_ephemeral_campaigns_for_lines

D0 = Decimal("0")
D100 = Decimal("100")


class SearchResultsAPI(View):
    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        qs = ProductSearchService.search(q)

        # ✅ لازم برای موجودی و انتخاب بهترین variant (مثل product_list)
        qs = (
            qs.prefetch_related(
                Prefetch(
                    "variants",
                    queryset=ProductVariant.objects.filter(is_active=True).order_by("-stock", "id"),
                    to_attr="_vlist",
                )
            )
            .annotate(stock_total=Coalesce(Sum("variants__stock"), Value(0), output_field=IntegerField()))
            .distinct()
        )

        # دقیقاً همون فیلترها
        if request.GET.get("available") == "1":
            qs = qs.filter(variants__stock__gt=0).distinct()

        if request.GET.get("brand"):
            brands = [int(x) for x in request.GET.get("brand").split(",") if x.isdigit()]
            if brands:
                qs = qs.filter(brand_fk_id__in=brands)

        if request.GET.get("cat", "").isdigit():
            qs = qs.filter(category_id=int(request.GET.get("cat")))

        if request.GET.get("min"):
            try:
                qs = qs.filter(price__gte=Decimal(request.GET.get("min")))
            except:
                pass

        if request.GET.get("max"):
            try:
                qs = qs.filter(price__lte=Decimal(request.GET.get("max")))
            except:
                pass

        paginator = Paginator(qs, 12)
        page = int(request.GET.get("page", 1))
        page_obj = paginator.get_page(page)

        # ✅ اینجا تخفیف‌ها رو با PricingEngine محاسبه می‌کنیم (مثل صفحه اول)
        page_products = list(page_obj.object_list)

        priced_items = []
        product_to_item = {}
        for p in page_products:
            vlist = getattr(p, "_vlist", None) or []
            item = vlist[0] if vlist else p
            priced_items.append(item)
            product_to_item[p.id] = item

        lines = [build_pricing_line_public(item, qty=1) for item in priced_items]

        channel = "web"
        pricing_ctx = {"channel": channel, "coupons": [], "preview": True}
        epis = build_ephemeral_campaigns_for_lines(lines, channel=channel)
        if epis:
            pricing_ctx["ephemeral_campaigns"] = epis

        result = PricingEngine().evaluate(lines, pricing_ctx)

        by_key = {}
        for l in (result.lines or []):
            by_key[(l.product_id, getattr(l, "variant_id", None))] = l

        products = []
        for p in page_products:
            cover = "/static/images/placeholder-600x600.png"
            if hasattr(p, "cover_image") and p.cover_image and p.cover_image.image:
                cover = p.cover_image.image.url
            elif hasattr(p, "image_list") and p.image_list:
                cover = p.image_list[0].image.url

            # ---- موجودی ----
            in_stock = (getattr(p, "stock_total", 0) or 0) > 0

            # ---- تخفیف از PricingEngine ----
            item = product_to_item.get(p.id)
            is_variant = hasattr(item, "product_id")
            vid = item.id if (item and is_variant) else None
            ln = by_key.get((p.id, vid)) or by_key.get((p.id, None))

            base = Decimal(str(getattr(p, "price", 0) or 0))
            disc = D0

            if ln:
                base = Decimal(str(getattr(ln, "line_subtotal", base) or base))
                disc = Decimal(str(getattr(ln, "line_discount", 0) or 0))

            final = base - disc
            if final < 0:
                final = D0

            if base > 0 and disc > 0:
                discount_percent = int((disc * D100 / base).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            else:
                discount_percent = 0

            # برای اینکه JS شما old/new درست نمایش بده:
            price_out = float(final if discount_percent else base)
            compare_out = float(base if discount_percent else (getattr(p, "compare_at_price", 0) or 0))

            products.append({
                "id": p.id,
                "name": p.name,
                "url": p.get_absolute_url(),
                "price": price_out,
                "compare_at_price": compare_out,
                "discount_percent": discount_percent,
                "is_new": getattr(p, "is_new", False),
                "in_stock": in_stock,
                "cover": cover,
            })

        return JsonResponse({"products": products})
