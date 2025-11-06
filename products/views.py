# products/views.py
from decimal import Decimal
from typing import Optional, Iterable, Any, Dict, List
from dataclasses import dataclass
from django.db.models import Q, Count, Sum, Min, Max, Prefetch
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.http import http_date
from django.utils.timezone import now
from django.views import View
from django.views.generic import ListView, DetailView
from django.templatetags.static import static
from products.services.service_pricing import compute_service_unit_price
from django.contrib import messages
from django.shortcuts import redirect

from .models import (
    Product, ProductVariant, ProductImage, Color, Brand,
    Category, ProductAttributeValue,Service, CategoryService, ProductService
)
from .services.pricing_adapter import price_single_product

from django.contrib.contenttypes.models import ContentType
from Core.models import Comment
from Core.forms import CommentForm


# ---------------- Utils (single source of truth) ----------------
def _normalize_unit_price(obj):
    """
    اگر obj.price خالی/نامعتبر بود، از محصولش بردار.
    اگر باز هم خالی بود، صفر می‌گذاریم تا Decimal خطا ندهد.
    """
    try:
        p = getattr(obj, "price", None)
        if p in (None, "", " ", "None"):
            base = getattr(obj, "product", None)
            fallback = getattr(base, "price", None) if base else None
            setattr(obj, "price", fallback or 0)
        else:
            # اگر رشته‌ای با جداکننده بود، تمیزش کن
            if isinstance(p, str):
                pp = p.replace(",", "").strip()
                setattr(obj, "price", float(pp) if pp else 0)
    except Exception:
        try:
            setattr(obj, "price", float(getattr(obj, "product", None).price or 0))
        except Exception:
            setattr(obj, "price", 0)

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
    # برای لیست‌ها (نه دیتیل)، به لیست تبدیل می‌کنیم تا سبک‌تر باشد
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

# ---------------- List / Category ----------------
class ProductBaseQS:
    def base_qs(self):
        return (
            Product.objects
            .filter(is_active=True, status="pub")
            .select_related("category", "brand_fk")
            .prefetch_related(images_prefetch(), attr_prefetch_list())
            .annotate(_stock_total=Coalesce(Sum("variants__stock", distinct=True), 0))
            .distinct()
        )

class ProductListView(ProductBaseQS, ListView):
    model = Product
    template_name = "products/product_list.html"
    context_object_name = "products"
    paginate_by = 12

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
        qs = super().get_queryset() if hasattr(super(), "get_queryset") else self.base_qs()

        category = self.get_category()
        if category:
            tree_ids = list(category.get_descendants(include_self=True).values_list("id", flat=True))
            if hasattr(Product, "additional_categories"):
                qs = qs.filter(Q(category_id__in=tree_ids) | Q(additional_categories__in=tree_ids))
            else:
                qs = qs.filter(category_id__in=tree_ids)

        # brand filter
        brand_str = self.request.GET.get("brand", "").strip()
        if brand_str:
            try:
                ids: Iterable[int] = [int(x) for x in brand_str.split(",") if x]
                if ids:
                    qs = qs.filter(brand_fk_id__in=ids)
            except ValueError:
                pass

        # price range
        price_min = self.request.GET.get("min")
        price_max = self.request.GET.get("max")
        if price_min:
            try: qs = qs.filter(price__gte=int(price_min))
            except ValueError: pass
        if price_max:
            try: qs = qs.filter(price__lte=int(price_max))
            except ValueError: pass

        # q
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(short_description__icontains=q) |
                Q(description__icontains=q)
            )

        # sort
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
            qs = qs.order_by("-views", "-id") if hasattr(Product, "views") else qs.order_by("-created_at", "-id")

        return qs.prefetch_related(
            Prefetch(
                "variants",
                queryset=(
                    ProductVariant.objects
                    .filter(is_active=True, color__is_active=True)
                    .select_related("color")
                    .only("id", "product_id", "color_id",
                          "color__id", "color__name", "color__hex_code", "color__slug")
                ),
                to_attr="_prefetch_variants",
            ),
            images_prefetch(),
            attr_prefetch_list(),
        ).distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        category = self.get_category()
        ctx["category"] = category
        ctx["ancestors"] = list(category.get_ancestors(include_self=True)) if category else []

        full_qs = self.get_queryset().order_by()
        brand_facets = (
            full_qs.values("brand_fk_id", "brand_fk__name")
            .annotate(cnt=Count("id"))
            .order_by("brand_fk__name")
        )
        ctx["brand_facets"] = brand_facets
        ctx["brands"] = Brand.objects.filter(products__is_active=True).distinct().order_by("position", "name")

        agg = full_qs.aggregate(minp=Min("price"), maxp=Max("price"))
        ctx["price_min"] = agg["minp"]
        ctx["price_max"] = agg["maxp"]

        b = self.request.GET.get("brand", "")
        try:
            ctx["selected_brands"] = {int(x) for x in b.split(",") if x}
        except ValueError:
            ctx["selected_brands"] = set()
        ctx["q"] = self.request.GET.get("q", "").strip()
        ctx["current_sort"] = self.request.GET.get("sort", "pop")

        # رنگ‌های روی کارت لیست
        for p in ctx["products"]:
            uniq: dict[int, dict] = {}
            for v in getattr(p, "_prefetch_variants", []):
                c = getattr(v, "color", None)
                if c and c.id not in uniq:
                    uniq[c.id] = {"id": c.id, "name": c.name, "hex": c.hex_code, "slug": c.slug}
            for img in getattr(p, "image_list", []):
                c = getattr(img, "color", None)
                if c and c.id not in uniq:
                    uniq[c.id] = {"id": c.id, "name": c.name, "hex": c.hex_code, "slug": c.slug}
            p.colors_list = sorted(uniq.values(), key=lambda x: x["name"])

        return ctx

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
                Prefetch("variants", queryset=ProductVariant.objects.select_related("color", "size").filter(is_active=True)),
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
        def _add_unit(txt): return f"{txt} {unit}" if unit else txt
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
        labels = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور"]
        data = [68_800_000,66_500_000,64_900_000,63_200_000,62_200_000,61_880_000]
        return {"labels": labels, "data": data, "currency": "تومان"}

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
        data = {k:v for k,v in data.items() if v not in (None, [], {})}
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
                "price": _float(v.get_price()),   # قیمت پایه واریانت (قبل از موتور)
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
        priced_item = active_variant or p

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
                    "stock": int(getattr(v, "stock", 0) or 0),
                    "sku": v.sku or None,
                }
            except Exception:
                # اگر باز هم مشکلی بود، حداقل قیمت خام یا 0 نمایش بده
                variant_prices[str(v.id)] = {
                    "price": _float(
                        getattr(v, "price", getattr(v, "product", None).price if getattr(v, "product", None) else 0)),
                    "stock": int(getattr(v, "stock", 0) or 0),
                    "sku": v.sku or None,
                }
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
        auto_has_color = vqs.filter(color_id__isnull=False).exists() or any(getattr(im, "color_id", None) for im in images)
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
        ctx["related_products"] = (
            Product.objects.filter(is_active=True, status="pub", category=p.category)
            .exclude(id=p.id).select_related("brand_fk").prefetch_related("images")[:8]
        )

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
        is_approved=True,   # 🔥 این مهمه
        parent__isnull=True
    ).select_related("user").prefetch_related("replies__user")


        ctx["comments"] = comments
        ctx["comment_form"] = CommentForm()

        return ctx
    
    


    