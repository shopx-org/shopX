# products/api_views.py
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views import View
from .views import ProductListView

class ProductListAPI(View):
    paginate_by = 12

    def get(self, request):
        # استفاده از همون کوئری‌ست فیلتر شده ویو اصلی
        view = ProductListView()
        view.request = request
        view.kwargs = {}
        qs = view.get_queryset()

        page = int(request.GET.get("page", 1))
        paginator = Paginator(qs, self.paginate_by)
        page_obj = paginator.get_page(page)

        products_json = []
        for p in page_obj:
            # محاسبه درصد تخفیف
            discount_percent = 0
            if p.compare_at_price and p.compare_at_price > p.price > 0:
                discount_percent = round(((p.compare_at_price - p.price) / p.compare_at_price) * 100)

            # کاور تصویر با اولویت بالا
            cover = "/static/images/placeholder-600x600.png"
            if getattr(p, "cover_image", None) and p.cover_image and p.cover_image.image:
                cover = p.cover_image.image.url
            elif hasattr(p, "image_list") and p.image_list:
                cover = p.image_list[0].image.url

            products_json.append({
                "id": p.id,
                "name": p.name,
                "url": p.get_absolute_url(),
                "price": float(p.price or 0),
                "compare_at_price": float(p.compare_at_price or 0),
                "discount_percent": discount_percent,
                "is_new": getattr(p, "is_new", False),
                "cover": cover,
                "stock": getattr(p, "stock", 0),  # اگر داری
                "colors": [
                    {"id": c["id"], "name": c["name"], "slug": c["slug"], "hex": c["hex"]}
                    for c in getattr(p, "colors_list", [])
                ],
            })

        return JsonResponse({
            "products": products_json,
            "has_next": page_obj.has_next(),
            "page": page,
        })