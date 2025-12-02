# search/api_views.py
from django.http import JsonResponse
from django.views import View
from django.core.paginator import Paginator
from decimal import Decimal
from products.models import Product
from .services import ProductSearchService


class SearchResultsAPI(View):
    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        qs = ProductSearchService.search(q)

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
            try: qs = qs.filter(price__gte=Decimal(request.GET.get("min")))
            except: pass
        if request.GET.get("max"):
            try: qs = qs.filter(price__lte=Decimal(request.GET.get("max")))
            except: pass

        paginator = Paginator(qs, 12)
        page = int(request.GET.get("page", 1))
        page_obj = paginator.get_page(page)

        products = []
        for p in page_obj:
            cover = "/static/images/placeholder-600x600.png"
            if hasattr(p, "cover_image") and p.cover_image and p.cover_image.image:
                cover = p.cover_image.image.url
            elif hasattr(p, "image_list") and p.image_list:
                cover = p.image_list[0].image.url

            discount = 0
            if p.compare_at_price and p.compare_at_price > p.price:
                discount = round((p.compare_at_price - p.price) / p.compare_at_price * 100)

            products.append({
                "id": p.id,
                "name": p.name,
                "url": p.get_absolute_url(),
                "price": float(p.price or 0),
                "compare_at_price": float(p.compare_at_price or 0),
                "discount_percent": discount,
                "is_new": getattr(p, "is_new", False),
                "cover": cover,
            })

        return JsonResponse({"products": products})