from __future__ import annotations

from typing import List, Dict

from django.db.models import Q, QuerySet

from products.models import Product


class ProductSearchService:
    """
    سرویس مرکزی جستجوی محصول برای ShopX.

    - الان از icontains استفاده می‌کنیم (برای MVP)
    - بعداً همین کلاس را به PostgreSQL Full-Text + Trigram ارتقا می‌دیم
      بدون اینکه view / template عوض بشه.
    """

    BASE_FILTER = Q(is_active=True, status="pub")  # فقط محصولات فعال و منتشر شده

    @classmethod
    def base_queryset(cls) -> QuerySet[Product]:
        return (
            Product.objects
            .select_related("category", "brand_fk")
            .filter(cls.BASE_FILTER)
        )

    @classmethod
    def search(cls, query: str) -> QuerySet[Product]:
        """
        سرچ صفحه اصلی نتایج (/search/?q=...).
        فیلدهای هدف:
        - نام محصول
        - توضیح کوتاه
        - توضیحات
        - نام برند
        - نام دسته
        """
        q = (query or "").strip()
        if not q:
            return Product.objects.none()

        qs = (
            cls.base_queryset()
            .filter(
                Q(name__icontains=q)
                | Q(short_description__icontains=q)
                | Q(description__icontains=q)
                | Q(brand_fk__name__icontains=q)
                | Q(category__name__icontains=q)
            )
            .order_by("-created_at")
        )
        return qs

    @classmethod
    def suggest(
        cls,
        query: str,
        per_category: int = 5,
        max_results: int = 50,
    ) -> List[Dict]:
        """
        داده‌ی مناسب برای اتوکامپلیت هدر:
        [
          {
            "id": cat_id,
            "name": cat_name,
            "products": [
              {
                "id": ...,
                "name": ...,
                "url": ...,
                "thumbnail": ...,
                "brand": ...,
              },
              ...
            ]
          },
          ...
        ]
        """
        q = (query or "").strip()
        if not q:
            return []

        base_qs = (
            cls.base_queryset()
            .filter(
                Q(name__icontains=q)
                | Q(brand_fk__name__icontains=q)
                | Q(category__name__icontains=q)
            )
            .order_by("-created_at")[:max_results]
        )

        cat_map: dict[int, dict] = {}
        for p in base_qs:
            cat = p.category
            if not cat:
                continue

            cid = cat.id
            if cid not in cat_map:
                cat_map[cid] = {
                    "id": cid,
                    "name": cat.name,
                    "products": [],
                }

            # محدودیت تعداد آیتم در هر کتگوری
            if len(cat_map[cid]["products"]) >= per_category:
                continue

            cover = p.cover_image
            thumb_url = cover.image.url if cover and getattr(cover, "image", None) else ""

            cat_map[cid]["products"].append(
                {
                    "id": p.id,
                    "name": p.name,
                    "url": p.get_absolute_url(),
                    "thumbnail": thumb_url,
                    "brand": p.brand_fk.name if p. brand_fk_id else "",
                }
            )

        return list(cat_map.values())

