# search/views.py
# search/views.py
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db.models import Count, Min, Max
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from products.models import Product
from products.models import Brand, Category
from .services import ProductSearchService



def search_results(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()

    # پایه نتایج
    qs = ProductSearchService.search(q)

    # ---------- فیلتر: فقط موجود ----------
    available = request.GET.get("available")
    if available == "1":
        qs = qs.filter(variants__stock__gt=0).distinct()

    # ---------- فیلتر: برند (CSV مثل 1,3,5) ----------
    brand_param = (request.GET.get("brand") or "").strip()
    selected_brands: list[int] = []
    if brand_param:
        for part in brand_param.split(","):
            part = part.strip()
            if part.isdigit():
                selected_brands.append(int(part))

    if selected_brands:
        qs = qs.filter(brand_fk_id__in=selected_brands)

    # ---------- فیلتر: دسته ----------
    cat_id = (request.GET.get("cat") or "").strip()
    selected_cat_id = int(cat_id) if cat_id.isdigit() else None
    if selected_cat_id:
        qs = qs.filter(category_id=selected_cat_id)

    # ---------- فیلتر: بازه قیمت ----------
    min_param = (request.GET.get("min") or "").strip()
    max_param = (request.GET.get("max") or "").strip()

    if min_param:
        try:
            qs = qs.filter(price__gte=Decimal(min_param))
        except InvalidOperation:
            pass

    if max_param:
        try:
            qs = qs.filter(price__lte=Decimal(max_param))
        except InvalidOperation:
            pass

    # ---------- آمار برای سایدبار ----------
    total_count = qs.count()

    brand_facets = (
        qs.values("brand_fk_id", "brand_fk__name")
        .annotate(cnt=Count("id"))
        .order_by("brand_fk__name")
    )
    brand_ids = [b["brand_fk_id"] for b in brand_facets if b["brand_fk_id"]]
    brands = Brand.objects.filter(id__in=brand_ids).order_by("name")

    category_facets = (
        qs.values("category_id", "category__name")
        .annotate(cnt=Count("id"))
        .order_by("category__name")
    )
    cat_ids = [c["category_id"] for c in category_facets if c["category_id"]]
    categories = Category.objects.filter(id__in=cat_ids).order_by("name")

    # بازه واقعی نتایج فعلی (فقط برای متن توضیحی)
    price_stats = qs.aggregate(
        price_min=Min("price"),
        price_max=Max("price"),
    )

    # بازه گلوبال برای اسلایدر (همه محصولات فعال)
    slider_stats = Product.objects.filter(is_active=True).aggregate(
        slider_min=Min("price"),
        slider_max=Max("price"),
    )
    slider_min = slider_stats["slider_min"] or 0
    slider_max = slider_stats["slider_max"] or 0

    # اگر بازه گلوبال هم تهش یکی بود، یک بازه مصنوعی بساز
    if slider_min == slider_max:
        slider_min = 0
        slider_max = slider_max or 1_000_000

    products = qs  # فعلاً بدون صفحه‌بندی

    context = {
        "query": q,
        "products": products,
        "total_count": total_count,

        # فیلترهای فعلی
        "available": available,
        "selected_brands": selected_brands,
        "selected_cat_id": selected_cat_id,
        "min_param": min_param,
        "max_param": max_param,

        # داده‌های سایدبار
        "brands": brands,
        "brand_facets": brand_facets,
        "categories": categories,
        "category_facets": category_facets,
        "price_min": price_stats["price_min"],
        "price_max": price_stats["price_max"],

        # بازه اسلایدر
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