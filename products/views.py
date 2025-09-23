from django.views.generic import TemplateView

# products/views.py
from django.db.models import Q, Count, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render
from django.views.generic import ListView, DetailView
from django.db.models import Prefetch
from typing import Optional, Iterable
from .models import Product, Category, Brand, ProductImage, ProductVariant, ProductAttributeValue, AttributeChoice
from django.db.models import Q, Count, Min, Max

# Prefetch برای ویژگی‌ها
def attr_prefetch():
    return Prefetch(
        "attr_values",
        queryset=(
            ProductAttributeValue.objects
            .select_related("attribute", "value_choice")
            .prefetch_related("values_multi")
            .order_by("attribute__position", "attribute__id")
        ),
        to_attr="attr_values",  # روی شیء محصول لیست می‌نشیند
    )

def images_prefetch():
    return Prefetch(
        "images",
        queryset=ProductImage.objects.select_related("color").order_by("position", "id"),
        to_attr="image_list",
    )

class ProductBaseQS:
    def base_qs(self):
        return (
            Product.objects.filter(is_active=True)  # به انتخاب خودت: status="pub" هم اضافه کن
            .select_related("category", "brand_fk")
            .prefetch_related(images_prefetch(), attr_prefetch())
            .annotate(_stock_total=Coalesce(Sum("variants__stock"), 0))
            .distinct()
        )

def _resolve_category_by_path(path: str) -> Optional[Category]:
    """
    path مثل: 'electronics/mobile'
    به ترتیب اسلاگ‌ها را با والدشان resolve می‌کند.
    """
    parts = [p for p in (path or "").strip("/").split("/") if p]
    parent = None
    for slug in parts:
        parent = get_object_or_404(Category, slug=slug, parent=parent)
    return parent

class ProductListView(ListView):
    model = Product
    template_name = "products/product_list.html"  # همین تمپلیت شما، فقط جایش را این بگذار
    context_object_name = "products"
    paginate_by = 12

    def _base_qs(self):
        return (
            Product.objects.filter(is_active=True, status="pub")
            .select_related("category", "brand_fk")
            .prefetch_related("images")
            .distinct()
        )

    def get_category(self) -> Optional[Category]:
        path = self.kwargs.get("path")
        if not path:
            # همچنین ?category=<id> را هم ساپورت کنیم
            cat_id = self.request.GET.get("category")
            if cat_id:
                try:
                    return Category.objects.get(id=cat_id)
                except Category.DoesNotExist:
                    return None
            return None
        return _resolve_category_by_path(path)

    def get_queryset(self):
        qs = self._base_qs()

        # فیلتر بر اساس دسته و زیردسته‌ها
        category = self.get_category()
        if category:
            tree_ids = list(category.get_descendants(include_self=True).values_list("id", flat=True))
            if hasattr(Product, "additional_categories"):
                qs = qs.filter(Q(category_id__in=tree_ids) | Q(additional_categories__in=tree_ids))
            else:
                qs = qs.filter(category_id__in=tree_ids)

        # فیلتر برند (brand=1,2,5)
        brand_str = self.request.GET.get("brand", "").strip()
        if brand_str:
            ids: Iterable[int] = []
            try:
                ids = [int(x) for x in brand_str.split(",") if x]
            except ValueError:
                ids = []
            if ids:
                qs = qs.filter(brand_fk_id__in=ids)

        # فیلتر قیمت (min/max)
        try:
            price_min = self.request.GET.get("min")
            price_max = self.request.GET.get("max")
            if price_min:
                qs = qs.filter(price__gte=price_min)
            if price_max:
                qs = qs.filter(price__lte=price_max)
        except Exception:
            pass

        # مرتب‌سازی
        sort = self.request.GET.get("sort", "pop")  # پیش‌فرض «محبوب‌ترین» (اینجا نمایشی است)
        if sort == "new":
            qs = qs.order_by("-created_at", "-id")
        elif sort == "price_asc":
            qs = qs.order_by("price", "id")
        elif sort == "price_desc":
            qs = qs.order_by("-price", "-id")
        elif sort == "name":
            qs = qs.order_by("name")
        else:
            # «محبوب‌ترین» نداریم؛ فعلاً جدیدترین شبیه‌سازی می‌کنیم
            qs = qs.order_by("-created_at", "-id")

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        category = self.get_category()
        ctx["category"] = category
        ctx["ancestors"] = list(category.get_ancestors(include_self=True)) if category else []

        # دسته‌های مرتبط (برای باکس «دسته بندی های مرتبط»): فرزندان دستهٔ فعلی
        ctx["related_categories"] = list(category.get_children()) if category else Category.objects.filter(parent__isnull=True).order_by("position","name")

        # برندها با شمارش محصول
        qs = self.object_list
        brand_counts = (
            qs.values("brand_fk_id", "brand_fk__name")
              .annotate(cnt=Count("id"))
              .order_by("brand_fk__name")
        )
        ctx["brand_facets"] = brand_counts
        selected_brands = set()
        b = self.request.GET.get("brand", "")
        if b:
            try:
                selected_brands = {int(x) for x in b.split(",") if x}
            except ValueError:
                selected_brands = set()
        ctx["selected_brands"] = selected_brands

        # بازه‌ی قیمت برای اسلایدر/گزینه‌ها (از کل نتایج فعلی)
        agg = qs.aggregate(minp=Min("price"), maxp=Max("price"))
        ctx["price_min"] = agg["minp"]
        ctx["price_max"] = agg["maxp"]

        # برای تولباکس (تعداد)
        ctx["total_count"] = self.get_queryset().count()

        # برای انتخاب «مرتب‌سازی»
        ctx["current_sort"] = self.request.GET.get("sort", "pop")

        return ctx


    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # برندها برای فیلتر سایدبار
        ctx["brands"] = Brand.objects.filter(products__is_active=True).distinct().order_by("position", "name")
        ctx["current_sort"] = self.request.GET.get("sort", "")
        ctx["q"] = self.request.GET.get("q", "")
        return ctx

class CategoryProductListView(ProductListView):
    """
    همان لیست با فیلتر دسته‌بندی مسیر-درختی
    """
    def dispatch(self, request, *args, **kwargs):
        path = kwargs.get("path", "").rstrip("/")
        self.category = get_object_or_404(Category, slug=self._last_slug(path))
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def _last_slug(path):
        return path.split("/")[-1] if path else ""

    def get_queryset(self):
        qs = super().get_queryset()
        # همه‌ی نودهای زیرمجموعه‌ی این کتگوری
        cats = self.category.get_descendants(include_self=True)
        return qs.filter(category__in=cats)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["category"] = self.category
        ctx["breadcrumbs"] = self.category.get_ancestors(include_self=True)
        return ctx

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


def product_detail_view(request):
    return render(request, "products/product_detail.html")
