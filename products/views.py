# products/views.py
from typing import Optional, Iterable
from django.db.models import Q, Count, Sum, Min, Max, Prefetch
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.views.decorators.http import last_modified
from django.views.generic import ListView, DetailView
from dataclasses import asdict, dataclass
import hashlib, json
from typing import Dict, List, Any

from django.db.models import Prefetch, Sum, Q
from django.http import HttpRequest, HttpResponse
from django.utils.http import http_date
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.views.generic import DetailView
from django.utils.text import slugify
from .models import (
    Product, ProductVariant, ProductImage, Color, Brand,
    Category, ProductAttributeValue
)


# ---------- Prefetch Helpers ----------
def attr_prefetch():
    return Prefetch(
        "attr_values",  # نام lookup روی مدل
        queryset=(
            ProductAttributeValue.objects
            .select_related("attribute", "value_choice")
            .prefetch_related("values_multi")
            .order_by("attribute__position", "attribute__id")
        ),
        to_attr="attr_values_list",  # ← اسم جدید که جایی تعریف نشده
    )


def images_prefetch() -> Prefetch:
    return Prefetch(
        "images",
        queryset=ProductImage.objects.select_related("color").order_by("position", "id"),
        to_attr="image_list",
    )


# ---------- Base QuerySet Mixin ----------
class ProductBaseQS:
    """کویری‌ست پایه برای محصولات فعال و قابل نمایش (+prefetch/annotate حرفه‌ای)."""

    def base_qs(self):
        return (
            Product.objects
            .filter(is_active=True, status="pub")  # اگر status نداری، این بخش را حذف کن
            .select_related("category", "brand_fk")
            .prefetch_related(images_prefetch(), attr_prefetch())
            .annotate(_stock_total=Coalesce(Sum("variants__stock"), 0))
            .distinct()
        )


# ---------- Utils ----------
def _resolve_category_by_path(path: str) -> Optional[Category]:
    """
    path مثل: 'electronics/mobile' — به ترتیب، اسلاگ‌ها را با والدشان resolve می‌کند.
    """
    parts = [p for p in (path or "").strip("/").split("/") if p]
    parent = None
    for slug in parts:
        parent = get_object_or_404(Category, slug=slug, parent=parent)
    return parent


# ---------- Views ----------
class ProductListView(ProductBaseQS, ListView):
    model = Product
    template_name = "products/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    # -- Category resolver (از ?category=<id> یا از CategoryProductListView با kwargs['path'])
    def get_category(self) -> Optional[Category]:
        path = self.kwargs.get("path")
        if path:
            return _resolve_category_by_path(path)

        cat_id = self.request.GET.get("category")
        if cat_id:
            try:
                return Category.objects.get(id=cat_id)
            except Category.DoesNotExist:
                return None
        return None

    def get_queryset(self):
        qs = self.base_qs()

        # فیلتر: دسته و زیردسته‌ها (+ دسته‌های اضافی در صورت وجود رابطه)
        category = self.get_category()
        if category:
            tree_ids = list(
                category.get_descendants(include_self=True).values_list("id", flat=True)
            )
            if hasattr(Product, "additional_categories"):
                qs = qs.filter(Q(category_id__in=tree_ids) | Q(additional_categories__in=tree_ids))
            else:
                qs = qs.filter(category_id__in=tree_ids)

        # فیلتر: برند (brand=1,2,5)
        brand_str = self.request.GET.get("brand", "").strip()
        if brand_str:
            try:
                ids: Iterable[int] = [int(x) for x in brand_str.split(",") if x]
                if ids:
                    qs = qs.filter(brand_fk_id__in=ids)
            except ValueError:
                pass

        # فیلتر: بازه قیمت (?min=&max=)
        price_min = self.request.GET.get("min")
        price_max = self.request.GET.get("max")
        if price_min:
            try:
                qs = qs.filter(price__gte=int(price_min))
            except ValueError:
                pass
        if price_max:
            try:
                qs = qs.filter(price__lte=int(price_max))
            except ValueError:
                pass

        # فیلتر: جستجو (در صورت اضافه‌کردن input با name=q)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(short_description__icontains=q) |
                Q(description__icontains=q)
            )

        # مرتب‌سازی
        sort = self.request.GET.get("sort", "pop")
        if sort == "new":
            qs = qs.order_by("-created_at", "-id")
        elif sort == "price_asc":
            qs = qs.order_by("price", "id")
        elif sort == "price_desc":
            qs = qs.order_by("-price", "-id")
        elif sort == "name":
            qs = qs.order_by("name")
        else:
            # «محبوب‌ترین» اگر فیلد views داری:
            qs = qs.order_by("-views", "-id") if hasattr(Product, "views") else qs.order_by("-created_at", "-id")

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        category = self.get_category()
        ctx["category"] = category
        ctx["ancestors"] = list(category.get_ancestors(include_self=True)) if category else []

        ctx["related_categories"] = (
            list(category.get_children()) if category
            else Category.objects.filter(parent__isnull=True).order_by("position", "name")
        )

        # ⬅️ به‌جای object_list (که sliced است)، از qs کامل فیلترشده استفاده کن
        full_qs = self.get_queryset().order_by()  # order_by() خالی = پاک‌کردن مرتب‌سازی برای انعطاف

        # فیسِت برند بر اساس کل نتایج فیلترشده (بدون اسلایس)
        brand_facets = (
            full_qs.values("brand_fk_id", "brand_fk__name")
            .annotate(cnt=Count("id"))
            .order_by("brand_fk__name")
        )
        ctx["brand_facets"] = brand_facets

        # برندهای قابل انتخاب برای سایدبار
        ctx["brands"] = Brand.objects.filter(products__is_active=True).distinct().order_by("position", "name")

        # بازه قیمت روی کل نتایج فیلترشده
        agg = full_qs.aggregate(minp=Min("price"), maxp=Max("price"))
        ctx["price_min"] = agg["minp"]
        ctx["price_max"] = agg["maxp"]

        # انتخاب‌های فعلی
        b = self.request.GET.get("brand", "")
        try:
            ctx["selected_brands"] = {int(x) for x in b.split(",") if x}
        except ValueError:
            ctx["selected_brands"] = set()

        ctx["q"] = self.request.GET.get("q", "").strip()
        ctx["current_sort"] = self.request.GET.get("sort", "pop")

        # تعداد واقعی کل نتایج (نه فقط صفحه جاری)
        ctx["total_count"] = full_qs.count()

        return ctx


class CategoryProductListView(ProductListView):
    """
    همان لیست، اما دسته از مسیر درختی /c/<path>/ می‌آید.
    فقط get_category را از والد override می‌کنیم تا از kwargs['path'] استفاده کند.
    """

    def get_category(self) -> Optional[Category]:
        path = self.kwargs.get("path", "")
        return _resolve_category_by_path(path)


# Micro tools
def _float(v) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def _json(data: Any) -> str:
    return mark_safe(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def _etag_for_product(p: Product) -> str:
    basis = f"{p.slug} | {p.updated_at.isoformat()} | {p.images.count()} | {p.variants.count()}"
    return hashlib.md5(basis.encode("utf-8")).hexdigest()


@dataclass
class OfferDTO:
    price: float
    price_currency: str
    availability: str  # "https://schema.org/InStock" یا OutOfStock
    sku: str | None = None


def _float(v) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def _json(data: Any) -> str:
    # اگر قبلاً داری همون رو استفاده کن
    import json
    from django.utils.safestring import mark_safe
    return mark_safe(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def _jsonld(self, product: Product) -> str:
    # تصاویر
    imgs = [img.image.url for img in product.images.all() if getattr(img, "image", None)]

    # برند (اختیاری)
    brand = {"@type": "Brand", "name": product.brand_fk.name} if product.brand_fk_id else None

    # Offerها از واریانت‌ها
    offers: list[OfferDTO] = []
    for v in product.variants.all():
        offers.append(
            OfferDTO(
                price=_float(v.get_price()),
                price_currency="IRR",  # ← snake_case مطابق dataclass
                availability=("https://schema.org/InStock" if v.stock > 0 else "https://schema.org/OutOfStock"),
                sku=v.sku or None,
            )
        )

    # اگر واریانت نبود، از خود محصول یکی بساز
    if not offers:
        offers.append(
            OfferDTO(
                price=_float(product.price),
                price_currency="IRR",
                availability="https://schema.org/InStock",
                sku=getattr(product, "sku", None) or None,
            )
        )

    # ساخت دایرکتِ JSON-LD (بدون dataclass با کلیدهای @)
    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.name,
        "description": product.short_description or product.meta_description or (product.description or "")[:160],
        "image": imgs[:10],
        "brand": brand,
        "sku": getattr(product, "sku", None) or None,
        "offers": [
            {
                "@type": "Offer",
                "price": f"{o.price:.0f}",
                "priceCurrency": o.price_currency,  # ← اینجا camelCase در خروجی JSON
                "availability": o.availability,
                **({"sku": o.sku} if o.sku else {}),
            }
            for o in offers
        ],
    }

    # حذف مقادیر تهی برای خروجی تمیز
    data = {k: v for k, v in data.items() if v not in (None, [], {})}

    return _json(data)  # ensure_ascii=False + mark_safe در همین تابع رعایت شود


class ProductDetailView(DetailView):
    model = Product
    template_name = "products/product_detail.html"
    context_object_name = "product"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True, status="pub")
            .select_related("category", "brand_fk")
            .prefetch_related(
                Prefetch(
                    "images",
                    queryset=ProductImage.objects.order_by("position", "id"),
                ),
                Prefetch(
                    "variants",  # variants color
                    queryset=ProductVariant.objects.select_related("color").filter(is_active=True),
                ),
                Prefetch(
                    "attr_values",
                    queryset=ProductAttributeValue.objects.select_related(
                        "attribute", "value_choice"
                    ).order_by("attribute__position", "attribute__id"),
                ),
            )
        )

    def render_to_response(self, context, **response_kwargs):
        resp: HttpResponse = super().render_to_response(context, **response_kwargs)
        p: Product = self.object

        last_modified = p.updated_at or now()
        resp.headers["Last-Modified"] = http_date(last_modified.timestamp())

        etag = _etag_for_product(p)
        resp.headers["ETag"] = etag

        resp.headers.setdefault("Cache-Control", "public, max-age=300")

        resp.headers.setdefault("Link", f'<{p.get_absolute_url()}>; rel="canonical"')

        return resp

    def _variant_matrix(self, product: Product) -> Dict[str, Dict[str, Any]]:
        matrix: Dict[str, Dict[str, Any]] = {}
        for v in product.variants.all():
            ckey = str(v.color_id or 0)
            size_key = v.size or "OS"
            matrix.setdefault(ckey, {})
            matrix[ckey][size_key] = {
                "price": _float(v.get_price()),
                "stock": int(v.stock),
                "sku": v.sku or None
            }
        return matrix

    def low_stock_flag(self, product):
        """
        وضعیت «کمبود موجودی» برای نمایش پیام هشدار.
        منطق: کمترین موجودی بین واریانت‌ها یا مجموع موجودی‌ها بررسی می‌شود.
        """
        try:
            variants = list(product.variants.all())
        except Exception:
            variants = []

        if variants:
            total = sum(int(getattr(v, "stock", 0)) for v in variants)
            min_stock = min((int(getattr(v, "stock", 0)) for v in variants), default=0)
        else:
            # اگر واریانت نداری، از فیلد stock خود محصول (اگر داری) استفاده کن
            total = int(getattr(product, "stock", 0) or 0)
            min_stock = total

        return {
            "total_stock": total,
            "min_stock": min_stock,
            "is_low": (0 < min_stock <= 5) or (0 < total <= 5),
        }

    def _price_history(self, product: Product) -> dict:
        """
        TODO: در آینده از مدل واقعی تاریخچهٔ قیمت یا سرویس گزارشگیری بخوان.
        فعلاً دادهٔ نمونه برای Chart.js
        """
        labels = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور"]
        data = [68_800_000, 66_500_000, 64_900_000, 63_200_000, 62_200_000, 61_880_000]
        return {"labels": labels, "data": data, "currency": "تومان"}

    def _jsonld(self, product: Product) -> str:
        # تصاویر
        imgs = [img.image.url for img in product.images.all() if getattr(img, "image", None)]

        # برند (اختیاری)
        brand = {"@type": "Brand", "name": product.brand_fk.name} if product.brand_fk_id else None

        # Offerها از واریانت‌ها
        offers: list[OfferDTO] = []
        for v in product.variants.all():
            offers.append(
                OfferDTO(
                    price=_float(v.get_price()),
                    price_currency="IRR",  # ← snake_case مطابق dataclass
                    availability=("https://schema.org/InStock" if v.stock > 0 else "https://schema.org/OutOfStock"),
                    sku=v.sku or None,
                )
            )

        # اگر واریانت نبود، از خود محصول یکی بساز
        if not offers:
            offers.append(
                OfferDTO(
                    price=_float(product.price),
                    price_currency="IRR",
                    availability="https://schema.org/InStock",
                    sku=getattr(product, "sku", None) or None,
                )
            )

        # ساخت دایرکتِ JSON-LD (بدون dataclass با کلیدهای @)
        data = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": product.name,
            "description": product.short_description or product.meta_description or (product.description or "")[:160],
            "image": imgs[:10],
            "brand": brand,
            "sku": getattr(product, "sku", None) or None,
            "offers": [
                {
                    "@type": "Offer",
                    "price": f"{o.price:.0f}",
                    "priceCurrency": o.price_currency,  # ← اینجا camelCase در خروجی JSON
                    "availability": o.availability,
                    **({"sku": o.sku} if o.sku else {}),
                }
                for o in offers
            ],
        }

        # حذف مقادیر تهی برای خروجی تمیز
        data = {k: v for k, v in data.items() if v not in (None, [], {})}

        return _json(data)  # ensure_ascii=False + mark_safe در همین تابع رعایت شود

    def _breadcrumbs(self, product: Product) -> list[dict]:
        cat = product.category
        if not isinstance(cat, Category):
            return []
        items = []
        for c in cat.get_ancestors(include_self=True):
            items.append({"name": c.name, "url": c.get_absolute_url()})
        return items

    def _related(self, product: Product):
        # ساده: هم‌دسته‌ای‌ها؛ قابل ارتقاء به محبوبیت/فروش/برد کرامب چندسطحی
        return (
            Product.objects.filter(
                is_active=True, status="pub",
                category=product.category
            )
            .exclude(id=product.id)
            .select_related("brand_fk")
            .prefetch_related("images")
            [:8]
        )

    # ---- Context ----
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        p: Product = self.object

        # گالری (برای ساخت تامب‌ها و استیج)
        ctx["gallery_images"] = [
            {
                "id": img.id,
                "url": getattr(img.image, "url", ""),
                "alt": img.alt or p.name,
                "color_id": img.color_id,
                "is_primary": img.is_primary,
            }
            for img in p.images.all()
        ]

        # رنگ‌ها برای سواچ (با مدل Color از واریانت‌ها و تصاویر)
        ctx["colors"] = p.colors

        # ماتریس واریانت برای JS (قیمت/موجودی/sku برحسب رنگ/سایز)
        ctx["variant_matrix_json"] = _json(self._variant_matrix(p))

        # نمودار قیمت
        ctx["price_chart_json"] = _json(self._price_history(p))

        # وضعیت موجودی برای پیام "تنها X عدد باقی مانده"
        ctx["stock_info"] = self.low_stock_flag(p)

        # محصولات مرتبط
        ctx["related_products"] = self._related(p)

        # بردکرامپ + سئو
        ctx["breadcrumbs"] = self._breadcrumbs(p)
        ctx["meta_title"] = p.meta_title or p.name
        ctx["meta_description"] = p.meta_description or (p.short_description or p.description[:160])
        ctx["canonical_url"] = p.get_absolute_url()

        # JSON-LD
        ctx["product_jsonld"] = self._jsonld(p)

        return ctx
#
# # products/views.py
# from django.db.models import Q, Count, Sum
# from django.db.models.functions import Coalesce
# from django.shortcuts import get_object_or_404, render
# from django.views.generic import ListView, DetailView
# from django.db.models import Prefetch
# from typing import Optional, Iterable
# from .models import Product, Category, Brand, ProductImage, ProductVariant, ProductAttributeValue, AttributeChoice
# from django.db.models import Q, Count, Min, Max
#
# # Prefetch برای ویژگی‌ها
# def attr_prefetch():
#     return Prefetch(
#         "attr_values",
#         queryset=(
#             ProductAttributeValue.objects
#             .select_related("attribute", "value_choice")
#             .prefetch_related("values_multi")
#             .order_by("attribute__position", "attribute__id")
#         ),
#         to_attr="attr_values",  # روی شیء محصول لیست می‌نشیند
#     )
#
# def images_prefetch():
#     return Prefetch(
#         "images",
#         queryset=ProductImage.objects.select_related("color").order_by("position", "id"),
#         to_attr="image_list",
#     )
#
# class ProductBaseQS:
#     def base_qs(self):
#         return (
#             Product.objects.filter(is_active=True)  # به انتخاب خودت: status="pub" هم اضافه کن
#             .select_related("category", "brand_fk")
#             .prefetch_related(images_prefetch(), attr_prefetch())
#             .annotate(_stock_total=Coalesce(Sum("variants__stock"), 0))
#             .distinct()
#         )
#
# def _resolve_category_by_path(path: str) -> Optional[Category]:
#     """
#     path مثل: 'electronics/mobile'
#     به ترتیب اسلاگ‌ها را با والدشان resolve می‌کند.
#     """
#     parts = [p for p in (path or "").strip("/").split("/") if p]
#     parent = None
#     for slug in parts:
#         parent = get_object_or_404(Category, slug=slug, parent=parent)
#     return parent
#
# class ProductListView(ListView):
#     model = Product
#     template_name = "products/product_list.html"  # همین تمپلیت شما، فقط جایش را این بگذار
#     context_object_name = "products"
#     paginate_by = 12
#
#     def _base_qs(self):
#         return (
#             Product.objects.filter(is_active=True, status="pub")
#             .select_related("category", "brand_fk")
#             .prefetch_related("images")
#             .distinct()
#         )
#
#     def get_category(self) -> Optional[Category]:
#         path = self.kwargs.get("path")
#         if not path:
#             # همچنین ?category=<id> را هم ساپورت کنیم
#             cat_id = self.request.GET.get("category")
#             if cat_id:
#                 try:
#                     return Category.objects.get(id=cat_id)
#                 except Category.DoesNotExist:
#                     return None
#             return None
#         return _resolve_category_by_path(path)
#
#     def get_queryset(self):
#         qs = self._base_qs()
#
#         # فیلتر بر اساس دسته و زیردسته‌ها
#         category = self.get_category()
#         if category:
#             tree_ids = list(category.get_descendants(include_self=True).values_list("id", flat=True))
#             if hasattr(Product, "additional_categories"):
#                 qs = qs.filter(Q(category_id__in=tree_ids) | Q(additional_categories__in=tree_ids))
#             else:
#                 qs = qs.filter(category_id__in=tree_ids)
#
#         # فیلتر برند (brand=1,2,5)
#         brand_str = self.request.GET.get("brand", "").strip()
#         if brand_str:
#             ids: Iterable[int] = []
#             try:
#                 ids = [int(x) for x in brand_str.split(",") if x]
#             except ValueError:
#                 ids = []
#             if ids:
#                 qs = qs.filter(brand_fk_id__in=ids)
#
#         # فیلتر قیمت (min/max)
#         try:
#             price_min = self.request.GET.get("min")
#             price_max = self.request.GET.get("max")
#             if price_min:
#                 qs = qs.filter(price__gte=price_min)
#             if price_max:
#                 qs = qs.filter(price__lte=price_max)
#         except Exception:
#             pass
#
#         # مرتب‌سازی
#         sort = self.request.GET.get("sort", "pop")  # پیش‌فرض «محبوب‌ترین» (اینجا نمایشی است)
#         if sort == "new":
#             qs = qs.order_by("-created_at", "-id")
#         elif sort == "price_asc":
#             qs = qs.order_by("price", "id")
#         elif sort == "price_desc":
#             qs = qs.order_by("-price", "-id")
#         elif sort == "name":
#             qs = qs.order_by("name")
#         else:
#             # «محبوب‌ترین» نداریم؛ فعلاً جدیدترین شبیه‌سازی می‌کنیم
#             qs = qs.order_by("-created_at", "-id")
#
#         return qs
#
#     def get_context_data(self, **kwargs):
#         ctx = super().get_context_data(**kwargs)
#
#         category = self.get_category()
#         ctx["category"] = category
#         ctx["ancestors"] = list(category.get_ancestors(include_self=True)) if category else []
#
#         # دسته‌های مرتبط (برای باکس «دسته بندی های مرتبط»): فرزندان دستهٔ فعلی
#         ctx["related_categories"] = list(category.get_children()) if category else Category.objects.filter(parent__isnull=True).order_by("position","name")
#
#         # برندها با شمارش محصول
#         qs = self.object_list
#         brand_counts = (
#             qs.values("brand_fk_id", "brand_fk__name")
#               .annotate(cnt=Count("id"))
#               .order_by("brand_fk__name")
#         )
#         ctx["brand_facets"] = brand_counts
#         selected_brands = set()
#         b = self.request.GET.get("brand", "")
#         if b:
#             try:
#                 selected_brands = {int(x) for x in b.split(",") if x}
#             except ValueError:
#                 selected_brands = set()
#         ctx["selected_brands"] = selected_brands
#
#         # بازه‌ی قیمت برای اسلایدر/گزینه‌ها (از کل نتایج فعلی)
#         agg = qs.aggregate(minp=Min("price"), maxp=Max("price"))
#         ctx["price_min"] = agg["minp"]
#         ctx["price_max"] = agg["maxp"]
#
#         # برای تولباکس (تعداد)
#         ctx["total_count"] = self.get_queryset().count()
#
#         # برای انتخاب «مرتب‌سازی»
#         ctx["current_sort"] = self.request.GET.get("sort", "pop")
#
#         return ctx
#
#
#     def get_context_data(self, **kwargs):
#         ctx = super().get_context_data(**kwargs)
#         # برندها برای فیلتر سایدبار
#         ctx["brands"] = Brand.objects.filter(products__is_active=True).distinct().order_by("position", "name")
#         ctx["current_sort"] = self.request.GET.get("sort", "")
#         ctx["q"] = self.request.GET.get("q", "")
#         return ctx
#
# class CategoryProductListView(ProductListView):
#     """
#     همان لیست با فیلتر دسته‌بندی مسیر-درختی
#     """
#     def dispatch(self, request, *args, **kwargs):
#         path = kwargs.get("path", "").rstrip("/")
#         self.category = get_object_or_404(Category, slug=self._last_slug(path))
#         return super().dispatch(request, *args, **kwargs)
#
#     @staticmethod
#     def _last_slug(path):
#         return path.split("/")[-1] if path else ""
#
#     def get_queryset(self):
#         qs = super().get_queryset()
#         # همه‌ی نودهای زیرمجموعه‌ی این کتگوری
#         cats = self.category.get_descendants(include_self=True)
#         return qs.filter(category__in=cats)
#
#     def get_context_data(self, **kwargs):
#         ctx = super().get_context_data(**kwargs)
#         ctx["category"] = self.category
#         ctx["breadcrumbs"] = self.category.get_ancestors(include_self=True)
#         return ctx
#
# class ProductDetailView(ProductBaseQS, DetailView):
#     template_name = "products/product_detail.html"
#     model = Product
#     slug_field = "slug"
#     slug_url_kwarg = "slug"
#
#     def get_queryset(self):
#         return self.base_qs()
#
#     def get_context_data(self, **kwargs):
#         ctx = super().get_context_data(**kwargs)
#         p: Product = self.object
#         ctx["images"] = getattr(p, "image_list", [])
#         ctx["variants"] = (
#             ProductVariant.objects.filter(product=p, is_active=True)
#             .select_related("color").order_by("id")
#         )
#         ctx["breadcrumbs"] = p.category.get_ancestors(include_self=True)
#         # محصولات مرتبط (ساده: هم‌دسته)
#         ctx["related"] = (
#             Product.objects.filter(category=p.category, is_active=True)
#             .exclude(id=p.id)
#             .select_related("brand_fk")
#             .prefetch_related(images_prefetch())
#             .order_by("-created_at")[:8]
#         )
#         return ctx
#
#
#
