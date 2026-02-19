# products/views.py

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Any
from dataclasses import dataclass
from django.db.models import Sum, Q, IntegerField
from django.db.models.functions import Coalesce
from django.db.models import Sum, IntegerField, Value
from django.db.models.functions import Coalesce
from django.db.models import Q, Count, Sum, Min, Max, Prefetch, Avg
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import http_date
from django.utils.timezone import now
from django.views import View
from django.views.generic import ListView, DetailView, TemplateView
from django.templatetags.static import static
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from products.services.pricing_adapter import build_pricing_line_public
from products.models import Product
from promos.services.pricing import PricingEngine
from products.services.pricing_adapter import build_pricing_line_public
from .models import (
    Product, ProductVariant, ProductImage, Color, Brand, Category,
    ProductAttributeValue, Service, CategoryService, ProductService,
    PriceHistory,
)
from promos.models import Campaign
from .services.pricing_adapter import price_single_product
from products.services.service_pricing import compute_service_unit_price
from Core.models import Comment
from Core.forms import CommentForm
from products.services.pricing_adapter import build_pricing_line_public, build_ephemeral_campaigns_for_lines
from decimal import Decimal, InvalidOperation
from django.db.models import Count, Min, Max


# ---------------- Utils (single source of truth) ---------------- #


def _normalize_unit_price(obj):
    """
    Normalize the price of an object:
    - If obj.price is invalid or empty, fallback to its product's price.
    - If still invalid, set price = 0 to avoid Decimal errors.
    """
    try:
        p = getattr(obj, "price", None)
        if p in (None, "", " ", "None"):
            base = getattr(obj, "product", None)
            fallback = getattr(base, "price", None) if base else None
            setattr(obj, "price", fallback or 0)
        else:
            # Clean string prices with comma
            if isinstance(p, str):
                pp = p.replace(",", "").strip()
                setattr(obj, "price", float(pp) if pp else 0)
    except Exception:
        try:
            setattr(obj, "price", float(getattr(obj, "product", None).price or 0))
        except Exception:
            setattr(obj, "price", 0)


def compute_pricing_for_item(item, request=None, qty: int = 1, channel: str = "web"):
    from decimal import Decimal
    _normalize_unit_price(item)

    coupons = []
    if request is not None and hasattr(request, "session"):
        coupons = request.session.get("coupons", [])

    pres = price_single_product(item, qty=qty, coupons=coupons, channel=channel)

    subtotal = pres.subtotal or Decimal("0")
    total = pres.total or Decimal("0")
    discount_amount = pres.total_discount or Decimal("0")

    if subtotal <= 0:
        discount_percent = Decimal("0")
    else:
        discount_percent = (discount_amount / subtotal) * Decimal("100")

    return {
        "result": pres,
        "price_base": subtotal,
        "price_final": total,
        "discount_amount": discount_amount,
        "discount_percent": discount_percent,
    }


def _float(v):
    try:
        return float(v)
    except Exception:
        return 0.0


def _json(data: Any) -> str:
    import json
    from django.utils.safestring import mark_safe
    return mark_safe(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def _etag_for_product(p: Product) -> str:
    import hashlib
    src = f"{p.pk}:{p.updated_at.isoformat() if p.updated_at else ''}"
    return hashlib.md5(src.encode("utf-8")).hexdigest()


def _resolve_category_by_path(path: str) -> Optional[Category]:
    parts = [p for p in (path or "").strip("/").split("/") if p]
    parent = None
    for slug in parts:
        parent = get_object_or_404(Category, slug=slug, parent=parent)
    return parent


def images_prefetch() -> Prefetch:
    return Prefetch(
        "images",
        queryset=ProductImage.objects.select_related("color").order_by("position", "id"),
        to_attr="image_list",
    )


def attr_prefetch_list() -> Prefetch:
    return Prefetch(
        "attr_values",
        queryset=(
            ProductAttributeValue.objects
            .select_related("attribute", "value_choice")
            .prefetch_related("values_multi")
            .order_by("attribute__position", "attribute__id")
        ),
        to_attr="attr_values_list",
    )


#
# def compute_pricing_for_item(item, request=None, qty: int = 1, channel: str = "web"):
#     """
#     یک آبجکت محصول یا واریانت را می‌گیرد، قیمت مؤثر را با موتور پرایسینگ
#     حساب می‌کند و چهار مقدار استاندارد برمی‌گرداند:
#     - price_base         قیمت قبل از تخفیف
#     - price_final        قیمت بعد از تخفیف
#     - discount_amount    مبلغ تخفیف
#     - discount_percent   درصد تخفیف
#     به‌اضافه‌ی خود PricingResult برای دیباگ/ریپورت.
#     """
#     from decimal import Decimal  # برای اطمینان داخل خود تابع
#     _normalize_unit_price(item)
#
#     coupons = []
#     if request is not None and hasattr(request, "session"):
#         coupons = request.session.get("coupons", [])
#
#     pres = price_single_product(item, qty=qty, coupons=coupons, channel=channel)
#
#     subtotal = pres.subtotal or Decimal("0")
#     total = pres.total or Decimal("0")
#     discount_amount = pres.total_discount or Decimal("0")
#
#     if subtotal <= 0:
#         discount_percent = Decimal("0")
#     else:
#         discount_percent = (discount_amount / subtotal) * Decimal("100")
#
#     return {
#         "result": pres,
#         "price_base": subtotal,
#         "price_final": total,
#         "discount_amount": discount_amount,
#         "discount_percent": discount_percent,
#     }

# ---------------- Base QuerySet / ListView ---------------- #

class ProductBaseQS:
    def get_queryset(self):
        return (
            Product.objects
            .filter(is_active=True, status="pub")
            .select_related("category", "brand_fk")
            .annotate(_stock_total=Coalesce(Sum("variants__stock", distinct=True), 0))
            .distinct()
        )

#
#
# class ProductListView(ListView):
#     template_name = "products/product_list.html"
#     context_object_name = "products"
#     paginate_by = 24
#     def base_queryset(self):
#         return Product.objects.all()
#     def get_queryset(self):
#         qs = self.base_queryset()
#         # اینجا فیلترهای معمول خودت: search/sort/category/... #
#         # qs = self.apply_filters(qs)
#         return qs
# #



D100 = Decimal("100")
D0 = Decimal("0")
D1 = Decimal("1")

class ProductListView(ListView):
    template_name = "products/product_list.html"
    context_object_name = "products"
    paginate_by = 24

    def base_queryset(self):
        return (
            Product.objects.all()
            .select_related("category")
            .prefetch_related(
                Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True).order_by("-stock", "id"),
                         to_attr="_vlist")
            )
            .annotate(stock_total=Coalesce(Sum("variants__stock"), Value(0), output_field=IntegerField()))
            .order_by("-id")
        )

    def apply_campaign_filter(self, qs):
        cid = (self.request.GET.get("campaign_id") or "").strip()
        if not cid:
            self._active_campaign = None
            return qs

        campaign = get_object_or_404(Campaign, pk=cid, is_active=True)
        self._active_campaign = campaign

        allowed_q = Q()
        has_scope_rule = False

        for r in campaign.rules.all():
            p = r.payload or {}

            if r.kind == "product_in":
                ids = p.get("product_ids") or []
                if ids:
                    has_scope_rule = True
                    allowed_q |= Q(id__in=ids)

            elif r.kind == "variant_in":
                vids = p.get("variant_ids") or []
                if vids:
                    has_scope_rule = True
                    # فرض: related_name واریانت‌ها "variants" است (تو base_queryset همین را prefetch کردی)
                    allowed_q |= Q(variants__id__in=vids)

            elif r.kind == "brand_in":
                bids = p.get("brand_ids") or []
                if bids:
                    has_scope_rule = True
                    # allowed_q |= Q(brand_id__in=bids)
                    allowed_q |= Q(brand_fk_id__in=bids)

            elif r.kind == "category_in":
                cids = p.get("category_ids") or []
                if cids:
                    has_scope_rule = True
                    allowed_q |= Q(category_id__in=cids)

        # اگر کمپین هیچ rule محدودکننده محصول نداشت، یعنی “عمومی” است => همه محصولات
        if not has_scope_rule:
            return qs

        return qs.filter(allowed_q).distinct()

    # def apply_filters(self, qs):
    #     # فیلترهای خودت
    #     return qs

    def apply_filters(self, qs):
        GET = self.request.GET

        # ---------- فیلترها (مثل search) ----------
        available = (GET.get("available") or "").strip()
        if available == "1":
            qs = qs.filter(variants__stock__gt=0).distinct()

        brand_param = (GET.get("brand") or "").strip()
        selected_brands = [int(x) for x in brand_param.split(",") if x.isdigit()]
        if selected_brands:
            qs = qs.filter(brand_fk_id__in=selected_brands)

        cat_id = (GET.get("cat") or "").strip()
        selected_cat_id = int(cat_id) if cat_id.isdigit() else None
        if selected_cat_id:
            qs = qs.filter(category_id=selected_cat_id)

        min_param = (GET.get("min") or "").strip()
        max_param = (GET.get("max") or "").strip()

        if min_param:
            try:
                qs = qs.filter(price__gte=Decimal(min_param))
            except (InvalidOperation, ValueError, TypeError):
                pass

        if max_param:
            try:
                qs = qs.filter(price__lte=Decimal(max_param))
            except (InvalidOperation, ValueError, TypeError):
                pass

        # ---------- مرتب‌سازی ----------
        sort = (GET.get("sort") or "new").strip()
        self.current_sort = sort  # برای selected شدن dropdown در template

        if sort == "pop":
            # اگر فعلاً معیار محبوبیت نداری، همین fallback امنه
            qs = qs.order_by("-id")
        elif sort == "new":
            # اگر created_at نداری، همین خط رو به "-id" تغییر بده
            qs = qs.order_by("-created_at", "-id")
        elif sort == "price_asc":
            qs = qs.order_by("price", "id")
        elif sort == "price_desc":
            qs = qs.order_by("-price", "-id")
        elif sort == "name":
            qs = qs.order_by("name", "id")
        else:
            qs = qs.order_by("-created_at", "-id")

        # برای اینکه template دقیقاً مثل سرچ فیلدها رو داشته باشه:
        self._filters_ctx = {
            "available": available,
            "selected_brands": selected_brands,
            "selected_cat_id": selected_cat_id,
            "min_param": min_param,
            "max_param": max_param,
            "current_sort": sort,
        }
        return qs


    def get_queryset(self):
        qs = self.base_queryset()
        qs = self.apply_campaign_filter(qs)   # ✅ اول کمپین
        qs = self.apply_filters(qs)           # ✅ بعد فیلترهای فعلی
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # ---------- 0) campaign in context (برای نوار بالای template) ----------
        # فرض: در get_queryset یا قبل‌تر self._active_campaign ست می‌شود
        ctx["campaign"] = getattr(self, "_active_campaign", None)

        # ---------- 1) total_count (عدد واقعی نتایج با فیلترها) ----------
        try:
            # paginator.count دقیق‌ترین عدد برای queryset نهاییِ همین صفحه است
            ctx["total_count"] = getattr(ctx.get("paginator"), "count", None)
        except Exception:
            ctx["total_count"] = None

        page_products = list(ctx.get("products") or [])

        # ✅ (اضافه شد) فیلترهای فعلی + sort برای template (همون چیزی که گفتی)
        f = getattr(self, "_filters_ctx", {})
        ctx.update(f)
        ctx.setdefault("current_sort", "new")

        # ✅ (اضافه شد) برندها + فست‌ها + آمار قیمت (مثل سرچ)
        # نکته: self.object_list کوئری نهایی بعد از apply_filters است (نه فقط همین صفحه)
        qs = getattr(self, "object_list", None)
        if qs is not None:
            # --- برندها مثل سرچ ---
            brand_facets = (
                qs.values("brand_fk_id", "brand_fk__name")
                .annotate(cnt=Count("id", distinct=True))
                .order_by("brand_fk__name")
            )

            brand_ids = [b["brand_fk_id"] for b in brand_facets if b.get("brand_fk_id")]
            ctx["brands"] = Brand.objects.filter(id__in=brand_ids).order_by("name")
            ctx["brand_facets"] = brand_facets

            # --- آمار قیمت نتایج (برای متن/نمایش) ---
            price_stats = qs.aggregate(price_min=Min("price"), price_max=Max("price"))
            ctx["price_min"] = price_stats.get("price_min")
            ctx["price_max"] = price_stats.get("price_max")

        # --- مین/مکس کل سایت برای track اسلایدر (بدون توجه به فیلتر) ---
        slider_stats = Product.objects.filter(is_active=True, status="pub").aggregate(
            slider_min=Min("price"),
            slider_max=Max("price"),
        )
        ctx["slider_min"] = slider_stats.get("slider_min") or 0
        ctx["slider_max"] = slider_stats.get("slider_max") or 1_000_000

        if not page_products:
            # اگر محصولی نیست، همین کانتکست کافی است
            return ctx

        # ---------- 2) انتخاب آیتم قیمت‌گذاری برای هر محصول (variant یا product) ----------
        priced_items = []
        product_to_item = {}  # product_id -> (variant or product)

        for p in page_products:
            vlist = getattr(p, "_vlist", None) or []
            # base_queryset شما order_by("-stock", "id") دارد؛ پس vlist[0] بهترین گزینه است
            item = vlist[0] if vlist else p
            priced_items.append(item)
            product_to_item[p.id] = item

        # ---------- 3) ساخت lines ----------
        lines = [build_pricing_line_public(item, qty=1) for item in priced_items]

        # ---------- 4) pricing ctx + ephemeral ----------
        channel = "web"
        pricing_ctx = {
            "channel": channel,
            "coupons": [],
            "preview": True,  # برای لیست، preview بهتر است
        }

        epis = build_ephemeral_campaigns_for_lines(lines, channel=channel)
        if epis:
            pricing_ctx["ephemeral_campaigns"] = epis

        # ---------- 5) evaluate ----------
        result = PricingEngine().evaluate(lines, pricing_ctx)

        # ---------- 6) index خطوط نتیجه با کلید استاندارد ----------
        # کلید: (product_id, variant_id_or_None)
        by_key = {}
        for l in (result.lines or []):
            by_key[(l.product_id, getattr(l, "variant_id", None))] = l

        # ---------- 7) attach computed fields روی هر محصول ----------
        for p in page_products:
            item = product_to_item.get(p.id)

            # اگر item واریانت باشد، معمولاً product_id دارد
            is_variant = hasattr(item, "product_id")
            vid = item.id if (item and is_variant) else None

            ln = by_key.get((p.id, vid)) or by_key.get((p.id, None))

            # fallback قیمت پایه از خود محصول (اگر خط قیمت‌گذاری نیامد)
            base = Decimal(str(getattr(p, "price", 0) or 0))
            disc = D0

            if ln:
                # line_subtotal بهتره چون شامل qty و قیمت پایه برای همان line است
                base = Decimal(str(getattr(ln, "line_subtotal", base) or base))
                disc = Decimal(str(getattr(ln, "line_discount", 0) or 0))

            final = base - disc
            if final < 0:
                final = D0

            if base > 0 and disc > 0:
                percent = (disc * D100 / base).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            else:
                percent = Decimal("0")

            # فیلدهای قابل استفاده در template
            p.price_base = base
            p.price_final = final
            p.has_discount = disc > 0
            p.discount_percent = percent

            st = int(getattr(p, "stock_total", 0) or 0)
            p.in_stock = st > 0
            p.low_stock = p.in_stock and (st <= 3)
            p.stock_total = st

        # محصولات همین صفحه (با فیلدهای attach شده)
        ctx["products"] = page_products

        return ctx

    # def get_context_data(self, **kwargs):
    #     ctx = super().get_context_data(**kwargs)
    #
    #     # ---------- 0) campaign in context (برای نوار بالای template) ----------
    #     # فرض: در get_queryset یا قبل‌تر self._active_campaign ست می‌شود
    #     ctx["campaign"] = getattr(self, "_active_campaign", None)
    #
    #     # ---------- 1) total_count (عدد واقعی نتایج با فیلترها) ----------
    #     try:
    #         # paginator.count دقیق‌ترین عدد برای queryset نهاییِ همین صفحه است
    #         ctx["total_count"] = getattr(ctx.get("paginator"), "count", None)
    #     except Exception:
    #         ctx["total_count"] = None
    #
    #     page_products = list(ctx.get("products") or [])
    #     if not page_products:
    #         # اگر محصولی نیست، همین کانتکست کافی است
    #         return ctx
    #
    #     # ---------- 2) انتخاب آیتم قیمت‌گذاری برای هر محصول (variant یا product) ----------
    #     priced_items = []
    #     product_to_item = {}  # product_id -> (variant or product)
    #
    #     for p in page_products:
    #         vlist = getattr(p, "_vlist", None) or []
    #         # base_queryset شما order_by("-stock", "id") دارد؛ پس vlist[0] بهترین گزینه است
    #         item = vlist[0] if vlist else p
    #         priced_items.append(item)
    #         product_to_item[p.id] = item
    #
    #     # ---------- 3) ساخت lines ----------
    #     lines = [build_pricing_line_public(item, qty=1) for item in priced_items]
    #
    #     # ---------- 4) pricing ctx + ephemeral ----------
    #     channel = "web"
    #     pricing_ctx = {
    #         "channel": channel,
    #         "coupons": [],
    #         "preview": True,  # برای لیست، preview بهتر است
    #     }
    #
    #     epis = build_ephemeral_campaigns_for_lines(lines, channel=channel)
    #     if epis:
    #         pricing_ctx["ephemeral_campaigns"] = epis
    #
    #     # ---------- 5) evaluate ----------
    #     result = PricingEngine().evaluate(lines, pricing_ctx)
    #
    #     # ---------- 6) index خطوط نتیجه با کلید استاندارد ----------
    #     # کلید: (product_id, variant_id_or_None)
    #     by_key = {}
    #     for l in (result.lines or []):
    #         by_key[(l.product_id, getattr(l, "variant_id", None))] = l
    #
    #     # ---------- 7) attach computed fields روی هر محصول ----------
    #     for p in page_products:
    #         item = product_to_item.get(p.id)
    #
    #         # اگر item واریانت باشد، معمولاً product_id دارد
    #         is_variant = hasattr(item, "product_id")
    #         vid = item.id if (item and is_variant) else None
    #
    #         ln = by_key.get((p.id, vid)) or by_key.get((p.id, None))
    #
    #         # fallback قیمت پایه از خود محصول (اگر خط قیمت‌گذاری نیامد)
    #         base = Decimal(str(getattr(p, "price", 0) or 0))
    #         disc = D0
    #
    #         if ln:
    #             # line_subtotal بهتره چون شامل qty و قیمت پایه برای همان line است
    #             base = Decimal(str(getattr(ln, "line_subtotal", base) or base))
    #             disc = Decimal(str(getattr(ln, "line_discount", 0) or 0))
    #
    #         final = base - disc
    #         if final < 0:
    #             final = D0
    #
    #         if base > 0 and disc > 0:
    #             percent = (disc * D100 / base).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    #         else:
    #             percent = Decimal("0")
    #
    #         # فیلدهای قابل استفاده در template
    #         p.price_base = base
    #         p.price_final = final
    #         p.has_discount = disc > 0
    #         p.discount_percent = percent
    #
    #         st = int(getattr(p, "stock_total", 0) or 0)
    #         p.in_stock = st > 0
    #         p.low_stock = p.in_stock and (st <= 3)
    #         p.stock_total = st
    #
    #     # محصولات همین صفحه (با فیلدهای attach شده)
    #     ctx["products"] = page_products
    #     f = getattr(self, "_filters_ctx", {})
    #     ctx.update(f)
    #
    #     # اگر current_sort ست نشد، پیش‌فرض new
    #     ctx.setdefault("current_sort", "new")
    #
    #     return ctx


# ---------------- Category Product List ---------------- #

class CategoryProductListView(ProductListView):
    def get_category(self) -> Optional[Category]:
        path = self.kwargs.get("path", "")
        return _resolve_category_by_path(path)


# ---------------- Variant Price API ----------------
class VariantPriceView(View):
    http_method_names = ["get"]

    def get(self, request, slug):
        product = get_object_or_404(
            Product.objects.filter(is_active=True, status="pub")
            .select_related("category", "brand_fk"),
            slug=slug
        )

        vid_str = request.GET.get("variant")
        if not vid_str:
            return JsonResponse({"ok": False, "error": "variant param required"}, status=400)

        try:
            vid = int(str(vid_str).strip())
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "invalid variant id"}, status=400)

        variant = get_object_or_404(
            product.variants.filter(is_active=True)
            .select_related("product", "color", "size"),
            id=vid
        )

        # ← اینجا باشد (داخل تابع و بعد از به‌دست آوردن variant)
        _normalize_unit_price(variant)

        # محاسبه قیمت
        res = price_single_product(
            variant, qty=1, coupons=request.session.get("coupons", []), channel="web"
        )
        subtotal = _float(res.subtotal or 0.0)
        total = _float(res.total or 0.0)
        discount_amount = _float(res.total_discount or 0.0)
        discount_percent = (discount_amount / subtotal * 100.0) if subtotal else 0.0

        return JsonResponse({
            "ok": True,
            "variant_id": variant.id,
            "sku": variant.sku,
            "stock": int(variant.stock or 0),
            "price_base": subtotal,
            "price_final": total,
            "discount_amount": discount_amount,
            "discount_percent": discount_percent,
        })


# ---------------- Product Detail ----------------
@dataclass
class OfferDTO:
    price: float
    price_currency: str
    availability: str
    sku: str | None = None


class ProductDetailView(DetailView):
    model = Product
    template_name = "products/product_detail.html"
    context_object_name = "product"
    slug_url_kwarg = "slug"

    # Querying (برای دیتیل: attr_values را بدون to_attr می‌آوریم)
    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True, status="pub")
            .select_related("category", "brand_fk")
            .prefetch_related(
                Prefetch("images", queryset=ProductImage.objects.order_by("position", "id")),  # gallery
                Prefetch("variants",
                         queryset=ProductVariant.objects.select_related("color", "size").filter(is_active=True)),
                Prefetch(  # این یکی برای جدول مشخصات لازم است
                    "attr_values",
                    queryset=(
                        ProductAttributeValue.objects
                        .select_related("attribute", "value_choice")
                        .prefetch_related("values_multi")
                        .order_by("attribute__position", "attribute__id")
                    ),
                ),
            )
        )

    # Headers
    def render_to_response(self, context, **response_kwargs):
        resp: HttpResponse = super().render_to_response(context, **response_kwargs)
        p: Product = self.object
        last_modified = p.updated_at or now()
        resp.headers["Last-Modified"] = http_date(last_modified.timestamp())
        resp.headers["ETag"] = _etag_for_product(p)
        resp.headers.setdefault("Cache-Control", "public, max-age=300")
        resp.headers.setdefault("Link", f'<{p.get_absolute_url()}>; rel="canonical"')
        return resp

    # Helpers
    def _pav_value_display(self, pav) -> str:
        k = pav.attribute.kind
        unit = (pav.attribute.unit or "").strip()

        def _add_unit(txt):
            return f"{txt} {unit}" if unit else txt

        if k == "text": return pav.value_text or ""
        if k == "int":  return _add_unit(f"{pav.value_int:,}") if pav.value_int is not None else ""
        if k == "decimal":
            v = pav.value_decimal
            return _add_unit((f"{v:.2f}".rstrip("0").rstrip("."))) if v is not None else ""
        if k == "bool": return "بلی" if pav.value_bool else "خیر"
        if k == "choice": return pav.value_choice.label if pav.value_choice_id else ""
        if k == "multi":  return "، ".join([c.label for c in pav.values_multi.all()])
        return ""

    def _spec_summary(self, product: Product, limit: int = 6) -> list[dict]:
        items: list[dict] = []
        if product.brand_fk_id:
            items.append({"label": "برند", "value": product.brand_fk.name})
        for pav in list(product.attr_values.all()):
            val = self._pav_value_display(pav)
            if not val:
                continue
            items.append({"label": pav.attribute.name, "value": val})
            if len(items) >= limit:
                break
        return items[:limit]

    def _price_history(self, product: Product) -> dict:
        """
        خروجی برای Chart.js:
        {
          "labels": ["2025-11-01", ...],
          "min_prices": [ ... ],
          "avg_prices": [ ... ],
          "currency": "تومان",
          "meta": {
              "min_overall": ...,
              "max_overall": ...,
              ...
          }
        }
        """
        from django.utils.timezone import now
        from decimal import Decimal

        today = now().date()

        # می‌تونی بازه‌ رو محدود کنی به مثلا ۶۰ یا ۹۰ روز:
        qs = (
            PriceHistory.objects
            .filter(product=product, date__lte=today)
            .values("date")  # گروه‌بندی بر اساس تاریخ
            .annotate(
                min_price=Min("price"),
                avg_price=Avg("price"),
            )
            .order_by("date")
        )

        labels = []
        min_prices = []
        avg_prices = []

        for row in qs:
            labels.append(row["date"].isoformat())
            min_prices.append(int(row["min_price"]))
            avg_prices.append(int(row["avg_price"]))

        if not labels:
            return {
                "labels": [],
                "min_prices": [],
                "avg_prices": [],
                "currency": "تومان",
                "meta": {},
            }

        all_vals = min_prices + avg_prices
        min_overall = min(all_vals)
        max_overall = max(all_vals)

        # کمی پدینگ برای بالا/پایین نمودار
        min_y = int(min_overall * Decimal("0.97"))
        max_y = int(max_overall * Decimal("1.03"))

        meta = {
            "min_overall": min_overall,
            "max_overall": max_overall,
            "min_y": min_y,
            "max_y": max_y,
            "points": len(labels),
        }

        return {
            "labels": labels,
            "min_prices": min_prices,
            "avg_prices": avg_prices,
            "currency": "تومان",
            "meta": meta,
        }

    def _jsonld(self, product: Product) -> str:
        imgs = [img.image.url for img in product.images.all() if getattr(img, "image", None)]
        brand = {"@type": "Brand", "name": product.brand_fk.name} if product.brand_fk_id else None

        offers: list[OfferDTO] = [
            OfferDTO(
                price=_float(v.get_price()),
                price_currency="IRR",
                availability=("https://schema.org/InStock" if v.stock > 0 else "https://schema.org/OutOfStock"),
                sku=v.sku or None,
            )
            for v in product.variants.all()
        ]
        if not offers:
            offers.append(OfferDTO(price=_float(product.price), price_currency="IRR",
                                   availability="https://schema.org/InStock", sku=getattr(product, "sku", None)))

        data = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": product.name,
            "description": product.short_description or product.meta_description or (product.description or "")[:160],
            "image": imgs[:10],
            "brand": brand,
            "sku": getattr(product, "sku", None) or None,
            "offers": [
                {"@type": "Offer", "price": f"{o.price:.0f}", "priceCurrency": o.price_currency,
                 "availability": o.availability, **({"sku": o.sku} if o.sku else {})}
                for o in offers
            ],
        }
        data = {k: v for k, v in data.items() if v not in (None, [], {})}
        return _json(data)

    def _variant_matrix(self, product: Product) -> dict[str, dict[str, Any]]:
        matrix: dict[str, dict[str, Any]] = {}
        size_meta: dict[str, dict] = {}
        for v in product.variants.all().select_related("color", "size"):
            ckey = str(v.color_id or 0)
            skey = str(v.size_id or "OS")
            matrix.setdefault(ckey, {})
            matrix[ckey][skey] = {
                "variant_id": v.id,
                "price": _float(v.get_price()),  # قیمت پایه واریانت (قبل از موتور)
                "stock": int(v.stock or 0),
                "sku": v.sku or None,
            }
            if v.size_id and skey not in size_meta:
                size_meta[skey] = {
                    "id": v.size_id,
                    "label": getattr(v.size, "label", None) or getattr(v.size, "name", str(v.size)),
                    "code": getattr(v.size, "code", None),
                }
        return {"matrix": matrix, "sizes": size_meta}

    def _price_result_for(self, item, qty: int = 1):
        _normalize_unit_price(item)  # ← اضافه شد
        request = getattr(self, "request", None)
        coupons = (request.session.get("coupons", []) if request and hasattr(request, "session") else [])
        return price_single_product(item, qty=qty, coupons=coupons, channel="web")

    # Context
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        p: Product = self.object

        # واریانت فعال از روی ?variant
        variant_id = self.request.GET.get("variant")
        active_variant = None

        if variant_id:
            try:
                active_variant = p.variants.get(id=variant_id, is_active=True)
            except ProductVariant.DoesNotExist:
                active_variant = None

        # اگر variant در URL نبود، یک واریانت پیش‌فرض انتخاب کن تا قیمت اولیه با UI یکی باشد
        if not active_variant:
            active_variant = (
                p.variants.filter(is_active=True)
                .select_related("color", "size")
                .order_by("-stock", "id")  # اول موجودترین/اولین
                .first()
            )

        v_stock = int(getattr(active_variant, "stock", 0) or 0) if active_variant else 0
        ctx["in_stock"] = v_stock > 0
        ctx["stock_qty"] = v_stock

        priced_item = active_variant or p
        # # واریانت فعال از روی ?variant
        # variant_id = self.request.GET.get("variant")
        # active_variant = None
        # if variant_id:
        #     try:
        #         active_variant = p.variants.get(id=variant_id, is_active=True)
        #     except ProductVariant.DoesNotExist:
        #         active_variant = None
        # priced_item = active_variant or p

        # قیمت مؤثر با موتور
        pres = self._price_result_for(priced_item, qty=1)
        subtotal = pres.subtotal
        total = pres.total
        discount_amount = pres.total_discount
        discount_percent = (Decimal("0") if not subtotal or subtotal <= 0
                            else (discount_amount / subtotal) * Decimal("100"))

        ctx.update({
            "eff_price": total,
            "price_base": subtotal,
            "price_final": total,
            "discount_amount": discount_amount,
            "discount_percent": discount_percent,
            "pricing_explain": pres.explain,
            "active_variant": active_variant,
            "initial_variant_id": active_variant.id if active_variant else "",
        })

        # گالری (با fallback)
        images = list(p.images.all())
        ctx["gallery_images"] = [
            {"id": img.id,
             "url": getattr(img.image, "url", "") or static("images/broken-image.png"),
             "alt": img.alt or p.name,
             "color_id": img.color_id, "is_primary": img.is_primary}
            for img in images
        ]

        # رنگ‌ها
        colors, seen = [], set()
        for v in p.variants.all().select_related("color"):
            c = getattr(v, "color", None)
            if c and c.id not in seen:
                colors.append({
                    "id": c.id,
                    "name": c.name,
                    "hex_code": getattr(c, "hex_code", "#ccc"),
                    "slug": getattr(c, "slug", "")
                })
                seen.add(c.id)
        if not colors:
            for v in p.variants.all().select_related("color"):
                c = getattr(v, "color", None)
                if c and c.id not in seen:
                    colors.append({
                        "id": c.id,
                        "name": c.name,
                        "hex_code": getattr(c, "hex_code", "#ccc"),
                        "slug": getattr(c, "slug", "")
                    })
                    seen.add(c.id)
        colors.sort(key=lambda x: (x["name"] or "").strip())
        ctx["colors"] = colors

        # سایزهای یکتا (برای <select id="size">)
        sizes_qs = (
            p.variants.filter(is_active=True)
            .exclude(size__isnull=True)
            .values_list("size_id", flat=True).distinct().order_by("size_id")
        )
        ctx["sizes"] = list(sizes_qs)

        # ماتریس و قیمت واریانت‌ها
        ctx["variant_matrix_json"] = _json(self._variant_matrix(p))
        variant_prices = {}

        for v in p.variants.all().select_related("product"):
            _normalize_unit_price(v)  # ← اضافه شد
            try:
                vres = self._price_result_for(v, qty=1)
                variant_prices[str(v.id)] = {
                    "price": _float(vres.total),
                    "compare_at": _float(vres.subtotal),
                    "stock": int(getattr(v, "stock", 0) or 0),
                    "sku": v.sku or None,
                }


            except Exception:
                raw = _float(
                    getattr(v, "price", getattr(v, "product", None).price if getattr(v, "product", None) else 0))
                variant_prices[str(v.id)] = {
                    "price": raw,
                    "compare_at": raw,  # ✅ اینم اضافه کن
                    "stock": int(getattr(v, "stock", 0) or 0),
                    "sku": v.sku or None,
                }

            #
            #     # اگر باز هم مشکلی بود، حداقل قیمت خام یا 0 نمایش بده
            #
            #     variant_prices[str(v.id)] = {
            #         "price": _float(
            #             getattr(v, "price", getattr(v, "product", None).price if getattr(v, "product", None) else 0)),
            #         "stock": int(getattr(v, "stock", 0) or 0),
            #         "sku": v.sku or None,
            #     }
        try:
            item_unit_price = pres.lines[0].unit_price  # Decimal
        except Exception:
            # fallback اگر pres نداشت
            item_unit_price = Decimal(str(getattr(priced_item, "price", p.price)))

        anc = p.category.get_ancestors(include_self=True)
        cat_links = (CategoryService.objects
                     .filter(category__in=anc)
                     .select_related("service")
                     .prefetch_related("service__prices"))  # اگر ServicePrice دارید
        prd_links = (ProductService.objects
                     .filter(product=p)
                     .select_related("service")
                     .prefetch_related("service__prices"))

        # 3) ادغام یکتا با اولویت سطح محصول
        by_id = {}
        for link in prd_links:
            s = link.service
            if not getattr(s, "is_active", True):
                continue
            if getattr(s, "kind", "") != "warranty":
                continue
            by_id[s.id] = {"service": s, "is_default_on": bool(getattr(link, "is_default_on", False))}
        for link in cat_links:
            s = link.service
            if not getattr(s, "is_active", True):
                continue
            if getattr(s, "kind", "") != "warranty":
                continue
            # فقط اگر قبلاً از محصول override نشده
            if s.id not in by_id:
                by_id[s.id] = {"service": s, "is_default_on": bool(getattr(link, "is_default_on", False))}

        # 4) محاسبه قیمت واحد هر سرویس (preview)
        services_insurance = []
        for s_id, payload in by_id.items():
            s = payload["service"]
            try:
                unit = compute_service_unit_price(service=s, item_unit_price=item_unit_price)  # Decimal
            except Exception:
                unit = Decimal("0")
            services_insurance.append({
                "id": s.id,
                "name": s.name,
                "unit_price": unit,  # Decimal - در تمپلیت فرمت می‌کنی
                "is_default_on": payload["is_default_on"],
                "exclusive_group": getattr(s, "exclusive_group", "") or "",
                "per_item": getattr(s, "per_item", True),
            })

        # مرتب‌سازی دلخواه (پلان‌های پیش‌فرض اول)
        services_insurance.sort(key=lambda x: (not x["is_default_on"], x["name"]))

        ctx["services_insurance"] = services_insurance
        ctx["show_insurance"] = bool(services_insurance)
        ctx["variant_prices"] = variant_prices

        # پرچم‌های UI
        vqs = p.variants.filter(is_active=True)
        auto_has_color = vqs.filter(color_id__isnull=False).exists() or any(
            getattr(im, "color_id", None) for im in images)
        auto_has_size = vqs.filter(size__isnull=False).exists()
        cat = getattr(p, "category", None)
        MOBILE_SLUGS = {"mobile", "smartphone", "phone", "گوشی-موبایل", "موبایل"}
        is_mobile = bool(cat and cat.get_ancestors(include_self=True).filter(slug__in=MOBILE_SLUGS).exists())
        show_color = auto_has_color
        show_size = (not is_mobile) and auto_has_size
        ui_flags = getattr(cat, "ui_flags", None)
        if isinstance(ui_flags, dict):
            if "show_color" in ui_flags: show_color = bool(ui_flags["show_color"])
            if "show_size" in ui_flags: show_size = bool(ui_flags["show_size"])
        ctx["ui"] = {"show_color": show_color, "show_size": show_size, "show_size_guide": show_size and not is_mobile}

        # انتخاب اولیه
        if active_variant:
            ctx["selected_color_id"] = getattr(active_variant, "color_id", None)
            ctx["selected_size_id"] = getattr(active_variant, "size_id", None)
        else:
            ctx["selected_color_id"] = colors[0]["id"] if colors else None
            ctx["selected_size_id"] = (ctx["sizes"][0] if ctx.get("sizes") else None)

        # مشخصات/SEO و JSON-LD
        ctx["spec_summary"] = self._spec_summary(p, limit=6)
        ctx["spec_total"] = (1 if p.brand_fk_id else 0) + p.attr_values.count()
        ctx["price_chart_json"] = _json(self._price_history(p))
        ctx.setdefault("FALLBACK_IMG", static("images/products/single/1.jpg"))
        ctx.setdefault("FALLBACK_THUMB", static("images/products/single/1-small.jpg"))
        ctx["meta_title"] = p.meta_title or p.name
        ctx["meta_description"] = p.meta_description or (p.short_description or (p.description or "")[:160])
        ctx["canonical_url"] = p.get_absolute_url()
        ctx["product_jsonld"] = self._jsonld(p)

        # مرتبط‌ها (اگر لازم داری)
        # ctx["related_products"] = (
        #     Product.objects.filter(is_active=True, status="pub", category=p.category)
        #     .exclude(id=p.id).select_related("brand_fk").prefetch_related("images")[:8]
        # )
        # مرتبط‌ها (برای کارت شبیه صفحه اول: قیمت/تخفیف/رنگ/موجودی)
        related_qs = (
            Product.objects
            .filter(is_active=True, status="pub", category=p.category)
            .exclude(id=p.id)
            .select_related("category", "brand_fk")
            .prefetch_related(
                Prefetch(
                    "variants",
                    queryset=(
                        ProductVariant.objects
                        .filter(is_active=True)
                        .select_related("color")
                        .only("id", "product_id", "stock", "color_id",
                              "color__id", "color__name", "color__hex_code", "color__slug")
                    ),
                    to_attr="_prefetch_variants",
                ),
                Prefetch("images", queryset=ProductImage.objects.order_by("position", "id")),
            )
            .order_by("-created_at", "-id")[:8]
        )

        related_products = list(related_qs)

        for r in related_products:
            # قیمت/تخفیف مثل Home
            pricing = compute_pricing_for_item(r, request=self.request, qty=1)
            r.price_base = pricing.get("price_base")
            r.price_final = pricing.get("price_final")
            r.discount_amount = pricing.get("discount_amount")
            r.discount_percent = pricing.get("discount_percent") or 0
            r.has_discount = (r.discount_percent or 0) > 0

            # موجودی از روی واریانت‌ها
            pref = getattr(r, "_prefetch_variants", []) or []
            stock_total = sum((getattr(v, "stock", 0) or 0) for v in pref)
            r.stock_total = int(stock_total or 0)
            r.in_stock = r.stock_total > 0

            # رنگ‌ها مثل Home
            uniq = {}
            for v in pref:
                c = getattr(v, "color", None)
                if c and c.id not in uniq:
                    uniq[c.id] = {"id": c.id, "name": c.name, "hex": c.hex_code, "slug": c.slug}
            r.colors_list = list(uniq.values())

        ctx["related_products"] = related_products

        # breadcrumbs (اگر لازم داری)
        if isinstance(p.category, Category):
            ctx["breadcrumbs"] = [{"name": c.name, "url": c.get_absolute_url()}
                                  for c in p.category.get_ancestors(include_self=True)]
        else:
            ctx["breadcrumbs"] = []

        ctx["variant_prices_json"] = _json(variant_prices)  # ← JSON معتبر

        content_type = ContentType.objects.get_for_model(p)

        comments = Comment.objects.filter(
            content_type=content_type,
            object_id=p.id,
            is_approved=True,  # 🔥 این مهمه
            parent__isnull=True
        ).select_related("user").prefetch_related("replies__user")

        ctx["comments"] = comments
        ctx["comment_form"] = CommentForm()

        return ctx


# ---------------- Compare Products -----------------

def add_to_compare(request, product_id):
    compare_list = request.session.get("compare_list", [])
    product = get_object_or_404(Product, id=product_id)

    # محدودیت ۳ محصول
    if len(compare_list) >= 3:
        messages.warning(request, "شما نمی‌توانید بیش از ۳ محصول را برای مقایسه انتخاب کنید.")
        return redirect("products:compare_list")

    # بررسی دسته‌بندی
    if compare_list:
        first_product = Product.objects.filter(id=compare_list[0]).first()
        if first_product.category_id != product.category_id:
            messages.warning(request, "شما فقط می‌توانید محصولات یک دسته‌بندی را مقایسه کنید.")
            return redirect("products:compare_list")

    # اضافه کردن محصول
    if product_id not in compare_list:
        compare_list.append(product_id)
        request.session["compare_list"] = compare_list
        request.session.modified = True
        messages.success(request, f"محصول {product.name} به لیست مقایسه اضافه شد.")

    return redirect("products:compare_list")


def remove_from_compare(request, product_id):
    compare_list = request.session.get("compare_list", [])
    if product_id in compare_list:
        compare_list.remove(product_id)
    request.session["compare_list"] = compare_list
    request.session.modified = True
    return redirect("products:compare_list")


def compare_list(request):
    ids = request.session.get("compare_list", [])

    products = Product.objects.filter(id__in=ids).prefetch_related(
        "images", "variants", "attr_values__attribute"
    )

    # مرتب کردن طبق session
    products_dict = {p.id: p for p in products}
    ordered_products = [products_dict[pid] for pid in ids if pid in products_dict]

    for p in ordered_products:
        # موجودی کل
        p.total_stock = p.variants.aggregate(total=Sum("stock"))["total"] or 0

        # رنگ‌ها و سایز‌ها از variant یا رنگ اصلی محصول
        # رنگ‌ها را به شکل لیستی از hex_code بسازیم
        p.color_list = sorted({v.color.hex_code for v in p.variants.all() if v.color})
        p.size_list = sorted({v.size for v in p.variants.all() if v.size})

    return render(request, "products/compare_list.html", {
        "products": ordered_products
    })
