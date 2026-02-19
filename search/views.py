# search/views.py
# search/views.py
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.core.paginator import Paginator
from django.db.models import Count, Min, Max
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from products.models import Product, Brand, Category
from .services import ProductSearchService

# ✅ این 3 تا رو دقیقاً مطابق importهای products/views.py خودت تنظیم کن
from promos.services.pricing import PricingEngine
from products.services.pricing_adapter import build_pricing_line_public, build_ephemeral_campaigns_for_lines

from django.db.models import Sum, Value, IntegerField
from django.db.models.functions import Coalesce
from django.db.models import Prefetch
from products.models import ProductVariant


D0 = Decimal("0")
D100 = Decimal("100")


def search_results(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()

    # پایه نتایج
    qs = ProductSearchService.search(q)
    qs = (
        qs.select_related("category", "brand_fk")
        .prefetch_related(
            Prefetch(
                "variants",
                queryset=ProductVariant.objects.filter(is_active=True).order_by("-stock", "id"),
                to_attr="_vlist",
            )
        )
        .annotate(stock_total=Coalesce(Sum("variants__stock"), Value(0), output_field=IntegerField()))
        .distinct()
    )

    # ---------- فیلترها ----------
    if request.GET.get("available") == "1":
        qs = qs.filter(variants__stock__gt=0).distinct()

    brand_param = (request.GET.get("brand") or "").strip()
    selected_brands = [int(x) for x in brand_param.split(",") if x.isdigit()]
    if selected_brands:
        qs = qs.filter(brand_fk_id__in=selected_brands)

    cat_id = request.GET.get("cat", "").strip()
    selected_cat_id = int(cat_id) if cat_id.isdigit() else None
    if selected_cat_id:
        qs = qs.filter(category_id=selected_cat_id)

    min_param = request.GET.get("min", "").strip()
    max_param = request.GET.get("max", "").strip()

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

    # ---------- سایدبار ----------
    total_count = qs.count()

    brand_facets = (
        qs.values("brand_fk_id", "brand_fk__name")
        .annotate(cnt=Count("id", distinct=True))
        .order_by("brand_fk__name")
    )
    brand_ids = [b["brand_fk_id"] for b in brand_facets if b["brand_fk_id"]]
    brands = Brand.objects.filter(id__in=brand_ids).order_by("name")

    category_facets = (
        qs.values("category_id", "category__name")
        .annotate(cnt=Count("id", distinct=True))
        .order_by("category__name")
    )
    cat_ids = [c["category_id"] for c in category_facets if c["category_id"]]
    categories = Category.objects.filter(id__in=cat_ids).order_by("name")

    price_stats = qs.aggregate(price_min=Min("price"), price_max=Max("price"))

    slider_stats = Product.objects.filter(is_active=True).aggregate(
        slider_min=Min("price"),
        slider_max=Max("price"),
    )
    slider_min = slider_stats["slider_min"] or 0
    slider_max = slider_stats["slider_max"] or 1_000_000

    # صفحه‌بندی — مهم!
    paginator = Paginator(qs, 12)
    page_number = request.GET.get("page")
    try:
        page_number = int(page_number) if page_number else 1
    except (ValueError, TypeError):
        page_number = 1

    page_obj = paginator.get_page(page_number)

    # ✅ ---------- attach تخفیف و موجودی روی محصولات همین صفحه (مثل product_list) ----------
    page_products = list(page_obj.object_list)
    if page_products:
        priced_items = []
        product_to_item = {}  # product_id -> (variant or product)

        for p in page_products:
            vlist = getattr(p, "_vlist", None) or []
            item = vlist[0] if vlist else p
            priced_items.append(item)
            product_to_item[p.id] = item

        lines = [build_pricing_line_public(item, qty=1) for item in priced_items]

        channel = "web"
        pricing_ctx = {
            "channel": channel,
            "coupons": [],
            "preview": True,
        }

        epis = build_ephemeral_campaigns_for_lines(lines, channel=channel)
        if epis:
            pricing_ctx["ephemeral_campaigns"] = epis

        result = PricingEngine().evaluate(lines, pricing_ctx)

        by_key = {}
        for l in (result.lines or []):
            by_key[(l.product_id, getattr(l, "variant_id", None))] = l

        for p in page_products:
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
                percent = (disc * D100 / base).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            else:
                percent = Decimal("0")

            p.price_base = base
            p.price_final = final
            p.has_discount = disc > 0
            p.discount_percent = percent

            st = int(getattr(p, "stock_total", 0) or 0)
            p.in_stock = st > 0

        # مهم: page_obj رو با object_list جدید replace کنیم تا template همین رو ببینه
        page_obj.object_list = page_products

    context = {
        "query": q,
        "products": page_obj,
        "total_count": total_count,
        "paginator": paginator,
        "page_obj": page_obj,
        "is_paginated": paginator.num_pages > 1,
        "max_scroll_pages": 2,  # بعداً بکن 10

        # فیلترهای فعلی
        "available": request.GET.get("available"),
        "selected_brands": selected_brands,
        "selected_cat_id": selected_cat_id,
        "min_param": min_param,
        "max_param": max_param,

        # سایدبار
        "brands": brands,
        "brand_facets": brand_facets,
        "categories": categories,
        "category_facets": category_facets,
        "price_min": price_stats.get("price_min"),
        "price_max": price_stats.get("price_max"),
        "slider_min": slider_min,
        "slider_max": slider_max,
    }

    return render(request, "search/search_results.html", context)




# def search_results(request: HttpRequest) -> HttpResponse:
#     q = (request.GET.get("q") or "").strip()
#
#     # پایه نتایج
#     qs = ProductSearchService.search(q)
#
#     # ---------- فیلتر: فقط موجود ----------
#     available = request.GET.get("available")
#     if available == "1":
#         # محصولاتی که حداقل یک واریانت با موجودی > 0 دارند
#         qs = qs.filter(variants__stock__gt=0).distinct()
#
#     # ---------- فیلتر: برند (CSV مثل 1,3,5) ----------
#     brand_param = (request.GET.get("brand") or "").strip()
#     selected_brands: list[int] = []
#     if brand_param:
#         for part in brand_param.split(","):
#             part = part.strip()
#             if part.isdigit():
#                 selected_brands.append(int(part))
#
#     if selected_brands:
#         qs = qs.filter(brand_fk_id__in=selected_brands)
#
#     # ---------- فیلتر: دسته ----------
#     cat_id = (request.GET.get("cat") or "").strip()
#     selected_cat_id = int(cat_id) if cat_id.isdigit() else None
#     if selected_cat_id:
#         qs = qs.filter(category_id=selected_cat_id)
#
#     # ---------- فیلتر: بازه قیمت ----------
#     min_param = (request.GET.get("min") or "").strip()
#     max_param = (request.GET.get("max") or "").strip()
#
#     if min_param:
#         try:
#             qs = qs.filter(price__gte=Decimal(min_param))
#         except InvalidOperation:
#             pass
#
#     if max_param:
#         try:
#             qs = qs.filter(price__lte=Decimal(max_param))
#         except InvalidOperation:
#             pass
#
#     # ---------- آمار برای سایدبار ----------
#     total_count = qs.count()
#
#     brand_facets = (
#         qs.values("brand_fk_id", "brand_fk__name")
#         .annotate(cnt=Count("id"))
#         .order_by("brand_fk__name")
#     )
#     brand_ids = [b["brand_fk_id"] for b in brand_facets if b["brand_fk_id"]]
#     brands = Brand.objects.filter(id__in=brand_ids).order_by("name")
#
#     category_facets = (
#         qs.values("category_id", "category__name")
#         .annotate(cnt=Count("id"))
#         .order_by("category__name")
#     )
#     cat_ids = [c["category_id"] for c in category_facets if c["category_id"]]
#     categories = Category.objects.filter(id__in=cat_ids).order_by("name")
#
#     price_stats = qs.aggregate(
#         price_min=Min("price"),
#         price_max=Max("price"),
#     )
#
#     # فعلاً بدون صفحه‌بندی (هرچی هست نشان بده)
#     products = qs
#
#     context = {
#         "query": q,
#         "products": products,
#         "total_count": total_count,
#
#         # فیلترهای فعلی
#         "available": available,
#         "selected_brands": selected_brands,
#         "selected_cat_id": selected_cat_id,
#         "min_param": min_param,
#         "max_param": max_param,
#
#         # داده‌های سایدبار
#         "brands": brands,
#         "brand_facets": brand_facets,
#         "categories": categories,
#         "category_facets": category_facets,
#         "price_min": price_stats["price_min"],
#         "price_max": price_stats["price_max"],
#     }
#     return render(request, "search/search_results.html", context)


def search_suggest(request: HttpRequest) -> JsonResponse:
    if request.headers.get("x-requested-with") != "XMLHttpRequest":
        return JsonResponse({"categories": []})

    q = (request.GET.get("q") or "").strip()
    categories = ProductSearchService.suggest(q)
    return JsonResponse({"categories": categories})