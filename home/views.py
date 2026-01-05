# home/views.py
from __future__ import annotations
from django.shortcuts import render
from django.db.models import Prefetch
from django.utils import timezone
from django.views.generic import TemplateView
from .models import *
from products.models import Category, Product, ProductVariant, ProductImage
from products.views import compute_pricing_for_item
from promos.models import PromoBanner
# home/views.py
from django.shortcuts import render


class Home(TemplateView):
    template_name = "home/index.html"

    MINI_COL_LIMIT = 3
    TAB_COUNT = 3
    ITEMS_PER_TAB = 18
    BRAND_BANNERS_COUNT = 3

    # -----------------------------
    # Pricing decorator for templates
    # -----------------------------
    def _decorate_products_for_card(self, products: list[Product]) -> list[Product]:
        """
        Adds:
          - price_base, price_final
          - discount_amount, discount_percent, has_discount
          - colors_list (unique colors from prefetched variants)
          - in_stock (computed from prefetched variants stock)
        """
        for p in products:
            pricing = compute_pricing_for_item(p, request=self.request, qty=1)

            p.price_base = pricing.get("price_base")
            p.price_final = pricing.get("price_final")
            p.discount_amount = pricing.get("discount_amount")
            p.discount_percent = pricing.get("discount_percent") or 0
            p.has_discount = (p.discount_percent or 0) > 0

            # ✅ اضافه شد: موجودی برای بج ناموجود
            pref = getattr(p, "_prefetch_variants", [])
            if pref:
                # محصول واریانت‌دار: اگر حداقل یک واریانت stock>0 داشت → موجود
                p.in_stock = any((getattr(v, "stock", 0) or 0) > 0 for v in pref)
            else:
                # fallback (اگر محصول ساده stock دارد)
                p.in_stock = (getattr(p, "stock", 0) or 0) > 0

            uniq = {}
            for v in pref:
                c = getattr(v, "color", None)
                if c and c.id not in uniq:
                    uniq[c.id] = {"id": c.id, "name": c.name, "hex": c.hex_code, "slug": c.slug}
            p.colors_list = list(uniq.values())

        return products

    # -----------------------------
    # Shared prefetches / base qs
    # -----------------------------
    def _variants_prefetch(self) -> Prefetch:
        return Prefetch(
            "variants",
            queryset=(
                ProductVariant.objects
                .filter(is_active=True)
                .select_related("color")
                .only(
                    "id", "product_id", "color_id",
                    "color__id", "color__name", "color__hex_code", "color__slug",
                    "stock",  # ✅ اضافه شد
                )
            ),
            to_attr="_prefetch_variants",
        )

    def _images_prefetch(self) -> Prefetch:
        # اگر related_name تصاویرت "images" نیست، همینجا تغییرش بده
        return Prefetch(
            "images",
            queryset=(
                ProductImage.objects
                .order_by("-is_primary", "position", "id")
                .select_related("color")
                .only(
                    "id", "product_id", "color_id",
                    "image", "is_primary", "position",
                    "color__id", "color__name", "color__hex_code", "color__slug",
                )
            ),
            to_attr="image_list",
        )

    def _base_products_qs(self):
        return (
            Product.objects
            .filter(is_active=True, status="pub")
            .select_related("category", "brand_fk")
            .prefetch_related(self._variants_prefetch(), self._images_prefetch())
        )

    # -----------------------------
    # Sections builders
    # -----------------------------
    def _get_video_banner(self):
        return (
            HomeVideoBanner.objects
            .filter(is_active=True)
            .only("title_small", "title_big", "video_file")
            .first()
        )

    def _get_brand_banners(self):
        return (
            HomeBrandBanner.objects
            .select_related("brand", "category")
            .filter(is_active=True)
            .order_by("position")[: self.BRAND_BANNERS_COUNT]
        )

    def _get_tabs(self):
        # ریشه‌ها
        roots = list(
            Category.objects
            .filter(is_active=True, parent__isnull=True)
            .order_by("position", "name")[: self.TAB_COUNT]
        )

        base = self._base_products_qs()
        tabs = []

        for c in roots:
            cat_ids = list(c.get_descendants(include_self=True).values_list("id", flat=True))

            qs = (
                base.filter(category_id__in=cat_ids)
                .order_by("-created_at", "-id")[: self.ITEMS_PER_TAB]
            )

            products = list(qs)
            self._decorate_products_for_card(products)

            tabs.append({
                "key": f"cat-{c.id}",
                "title": c.name,
                "category": c,
                "products": products,
            })

        return tabs

    def _get_festival_banner_and_countdown(self):
        now = timezone.now()

        banners = (
            PromoBanner.objects
            .filter(is_active=True, channel="web", position="home_festival_hero")
            .select_related("campaign")
            .order_by("priority", "-updated_at")
        )

        picked = None
        for b in banners:
            if b.is_running(now):
                picked = b
                break

        countdown_ms = None
        if picked and picked.campaign:
            payload = picked.payload or {}
            mode = payload.get("countdown_mode") or "starts_at"  # starts_at | ends_at

            countdown_to = picked.campaign.ends_at if mode == "ends_at" else picked.campaign.starts_at
            if countdown_to:
                countdown_ms = int(countdown_to.timestamp() * 1000)

        return picked, countdown_ms

    def _get_home_mini_lists(self):
        """
        For your template:
          - home/templates/home/home_mini_product_lists.html
        Uses the same pricing decorator so p.price_final works.
        """
        base = self._base_products_qs()

        # 1) جدیدترین‌ها
        new_products = list(base.order_by("-created_at", "-id")[: self.MINI_COL_LIMIT])
        self._decorate_products_for_card(new_products)

        # 2) پرفروش‌ها (fallback)
        # TODO: اگر OrderItem داری، اینجا annotate پرفروش واقعی می‌زنیم
        if hasattr(Product, "views"):
            best_products = list(base.order_by("-views", "-id")[: self.MINI_COL_LIMIT])
        else:
            best_products = list(base.order_by("-created_at", "-id")[: self.MINI_COL_LIMIT])
        self._decorate_products_for_card(best_products)

        # 3) ویژه‌ها (fallback: محصولات sale_active)
        special_products = list(
            base.filter(sale_active=True).order_by("-updated_at", "-id")[: self.MINI_COL_LIMIT]
        )
        self._decorate_products_for_card(special_products)

        # کلاس‌ها را ساده و استاندارد گذاشتم تا پخش‌وپلا نشه
        col = "col-12 col-md-6 col-lg-4 mb-2"

        return [
            {"title": "محصولات جدید", "more_url": "/products/?sort=new", "col_class": col, "products": new_products},
            {"title": "محصولات پُرفروش", "more_url": "/products/?sort=pop", "col_class": col, "products": best_products},
            {"title": "محصولات ویژه", "more_url": "/products/?has_discount=1", "col_class": col, "products": special_products},
        ]

    # -----------------------------
    # Context
    # -----------------------------
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["video_banner"] = self._get_video_banner()
        context["home_brand_banners"] = self._get_brand_banners()

        # tabs (۱۸ تایی)
        context["home_product_tabs"] = self._get_tabs()

        # mini lists (۳×۳)
        context["home_mini_lists"] = self._get_home_mini_lists()

        # festival banner + countdown
        festival, countdown_ms = self._get_festival_banner_and_countdown()
        context["festival_banner"] = festival
        context["festival_countdown_ms"] = countdown_ms

        return context

# class Home(TemplateView):
#     template_name = "home/index.html"
#
#     MINI_COL_LIMIT = 3
#     TAB_COUNT = 3
#     ITEMS_PER_TAB = 18
#     BRAND_BANNERS_COUNT = 3
#
#     # -----------------------------
#     # Pricing decorator for templates
#     # -----------------------------
#     def _decorate_products_for_card(self, products: list[Product]) -> list[Product]:
#         """
#         Adds:
#           - price_base, price_final
#           - discount_amount, discount_percent, has_discount
#           - colors_list (unique colors from prefetched variants)
#         """
#         for p in products:
#             pricing = compute_pricing_for_item(p, request=self.request, qty=1)
#
#             p.price_base = pricing.get("price_base")
#             p.price_final = pricing.get("price_final")
#             p.discount_amount = pricing.get("discount_amount")
#             p.discount_percent = pricing.get("discount_percent") or 0
#             p.has_discount = (p.discount_percent or 0) > 0
#
#             uniq = {}
#             for v in getattr(p, "_prefetch_variants", []):
#                 c = getattr(v, "color", None)
#                 if c and c.id not in uniq:
#                     uniq[c.id] = {"id": c.id, "name": c.name, "hex": c.hex_code, "slug": c.slug}
#             p.colors_list = list(uniq.values())
#
#         return products
#
#     # -----------------------------
#     # Shared prefetches / base qs
#     # -----------------------------
#     def _variants_prefetch(self) -> Prefetch:
#         return Prefetch(
#             "variants",
#             queryset=(
#                 ProductVariant.objects
#                 .filter(is_active=True)
#                 .select_related("color")
#                 .only(
#                     "id", "product_id", "color_id",
#                     "color__id", "color__name", "color__hex_code", "color__slug",
#                 )
#             ),
#             to_attr="_prefetch_variants",
#         )
#
#     def _images_prefetch(self) -> Prefetch:
#         # اگر related_name تصاویرت "images" نیست، همینجا تغییرش بده
#         return Prefetch(
#             "images",
#             queryset=(
#                 ProductImage.objects
#                 .order_by("-is_primary", "position", "id")
#                 .select_related("color")
#                 .only(
#                     "id", "product_id", "color_id",
#                     "image", "is_primary", "position",
#                     "color__id", "color__name", "color__hex_code", "color__slug",
#                 )
#             ),
#             to_attr="image_list",
#         )
#
#     def _base_products_qs(self):
#         return (
#             Product.objects
#             .filter(is_active=True, status="pub")
#             .select_related("category", "brand_fk")
#             .prefetch_related(self._variants_prefetch(), self._images_prefetch())
#         )
#
#     # -----------------------------
#     # Sections builders
#     # -----------------------------
#     def _get_video_banner(self):
#         return (
#             HomeVideoBanner.objects
#             .filter(is_active=True)
#             .only("title_small", "title_big", "video_file")
#             .first()
#         )
#
#     def _get_brand_banners(self):
#         return (
#             HomeBrandBanner.objects
#             .select_related("brand", "category")
#             .filter(is_active=True)
#             .order_by("position")[: self.BRAND_BANNERS_COUNT]
#         )
#
#     def _get_tabs(self):
#         # ریشه‌ها
#         roots = list(
#             Category.objects
#             .filter(is_active=True, parent__isnull=True)
#             .order_by("position", "name")[: self.TAB_COUNT]
#         )
#
#         base = self._base_products_qs()
#         tabs = []
#
#         for c in roots:
#             cat_ids = list(c.get_descendants(include_self=True).values_list("id", flat=True))
#
#             qs = (
#                 base.filter(category_id__in=cat_ids)
#                 .order_by("-created_at", "-id")[: self.ITEMS_PER_TAB]
#             )
#
#             products = list(qs)
#             self._decorate_products_for_card(products)
#
#             tabs.append({
#                 "key": f"cat-{c.id}",
#                 "title": c.name,
#                 "category": c,
#                 "products": products,
#             })
#
#         return tabs
#
#     def _get_festival_banner_and_countdown(self):
#         now = timezone.now()
#
#         banners = (
#             PromoBanner.objects
#             .filter(is_active=True, channel="web", position="home_festival_hero")
#             .select_related("campaign")
#             .order_by("priority", "-updated_at")
#         )
#
#         picked = None
#         for b in banners:
#             if b.is_running(now):
#                 picked = b
#                 break
#
#         countdown_ms = None
#         if picked and picked.campaign:
#             payload = picked.payload or {}
#             mode = payload.get("countdown_mode") or "starts_at"  # starts_at | ends_at
#
#             countdown_to = picked.campaign.ends_at if mode == "ends_at" else picked.campaign.starts_at
#             if countdown_to:
#                 countdown_ms = int(countdown_to.timestamp() * 1000)
#
#         return picked, countdown_ms
#
#     def _get_home_mini_lists(self):
#         """
#         For your template:
#           - home/templates/home/home_mini_product_lists.html
#         Uses the same pricing decorator so p.price_final works.
#         """
#         base = self._base_products_qs()
#
#         # 1) جدیدترین‌ها
#         new_products = list(base.order_by("-created_at", "-id")[: self.MINI_COL_LIMIT])
#         self._decorate_products_for_card(new_products)
#
#         # 2) پرفروش‌ها (fallback)
#         # TODO: اگر OrderItem داری، اینجا annotate پرفروش واقعی می‌زنیم
#         if hasattr(Product, "views"):
#             best_products = list(base.order_by("-views", "-id")[: self.MINI_COL_LIMIT])
#         else:
#             best_products = list(base.order_by("-created_at", "-id")[: self.MINI_COL_LIMIT])
#         self._decorate_products_for_card(best_products)
#
#         # 3) ویژه‌ها (fallback: محصولات sale_active)
#         special_products = list(
#             base.filter(sale_active=True).order_by("-updated_at", "-id")[: self.MINI_COL_LIMIT]
#         )
#         self._decorate_products_for_card(special_products)
#
#         # کلاس‌ها را ساده و استاندارد گذاشتم تا پخش‌وپلا نشه
#         col = "col-12 col-md-6 col-lg-4 mb-2"
#
#         return [
#             {"title": "محصولات جدید", "more_url": "/products/?sort=new", "col_class": col, "products": new_products},
#             {"title": "محصولات پُرفروش", "more_url": "/products/?sort=pop", "col_class": col, "products": best_products},
#             {"title": "محصولات ویژه", "more_url": "/products/?has_discount=1", "col_class": col, "products": special_products},
#         ]
#
#     # -----------------------------
#     # Context
#     # -----------------------------
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#
#         context["video_banner"] = self._get_video_banner()
#         context["home_brand_banners"] = self._get_brand_banners()
#
#         # tabs (۱۸ تایی)
#         context["home_product_tabs"] = self._get_tabs()
#
#         # mini lists (۳×۳)
#         context["home_mini_lists"] = self._get_home_mini_lists()
#
#         # festival banner + countdown
#         festival, countdown_ms = self._get_festival_banner_and_countdown()
#         context["festival_banner"] = festival
#         context["festival_countdown_ms"] = countdown_ms
#
#         return context


class Terms(TemplateView):
    template_name = "home/terms.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["terms"] = TermsAndConditions.objects.first()
        return context



def page404(request, exception=None):
    return render(request, "home/404.html", status=404)

def page500(request):
    # exception ندارد
    return render(request, "home/500.html", status=500)

def page403(request, exception=None):
    return render(request, "home/403.html", status=403)

def page400(request, exception=None):
    return render(request, "home/400.html", status=400)

# این هندلر رسمی Django نیست، ولی صفحه‌اش را می‌سازیم برای وب‌سرور
def page504(request):
    return render(request, "home/504.html", status=504)

def page503(request):
    return render(request, "home/503.html", status=503)


def privacy_policy(request):
    return render(request, 'home/privacy.html')