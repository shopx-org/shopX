# promos/forms.py
from __future__ import annotations
from .models import PromoBanner, Campaign
from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import PromoBanner
from .models import Rule
from products.models import Category, Brand, Product, ProductVariant


def _flatten_ids(v) -> list[int]:
    if not v:
        return []
    out = []
    for x in v:
        try:
            out.append(int(x))
        except Exception:
            continue
    return out


def _used_ids_for_kind(kind: str, exclude_campaign_id=None) -> set[int]:
    """
    kind: 'product_in' یا 'variant_in'
    خروجی: set از id هایی که در payload rule های قبلی استفاده شده
    """
    qs = Rule.objects.filter(kind=kind).only("campaign_id", "payload")
    if exclude_campaign_id:
        qs = qs.exclude(campaign_id=exclude_campaign_id)

    used: set[int] = set()
    key = "product_ids" if kind == "product_in" else "variant_ids"

    for r in qs:
        payload = getattr(r, "payload", None) or {}
        ids = _flatten_ids(payload.get(key) or [])
        used.update(ids)

    return used


class RuleAdminForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label="دسته‌ها",
    )
    brands = forms.ModelMultipleChoiceField(
        queryset=Brand.objects.all(),
        required=False,
        label="برندها",
    )
    products = forms.ModelMultipleChoiceField(
        queryset=Product.objects.none(),   # ⬅️ مهم: بعداً تو __init پر می‌کنیم
        required=False,
        label="محصولات",
    )
    variants = forms.ModelMultipleChoiceField(
        queryset=ProductVariant.objects.none(),  # ⬅️ مهم
        required=False,
        label="واریانت‌ها",
    )

    threshold = forms.DecimalField(
        required=False,
        label="حداقل مبلغ سبد (تومان)",
        min_value=0,
    )
    qty = forms.IntegerField(
        required=False,
        label="حداقل تعداد",
        min_value=1,
    )

    class Meta:
        model = Rule
        fields = ("kind", "categories", "brands", "products", "variants", "threshold", "qty")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        obj = getattr(self, "instance", None)
        payload = (getattr(obj, "payload", None) or {}) if obj and obj.pk else {}
        kind = (obj.kind if obj and obj.pk else None)

        # --- Prefill از payload هنگام edit ---
        if kind == "category_in":
            self.fields["categories"].initial = payload.get("category_ids", [])
        elif kind == "brand_in":
            self.fields["brands"].initial = payload.get("brand_ids", [])
        elif kind == "product_in":
            self.fields["products"].initial = payload.get("product_ids", [])
        elif kind == "variant_in":
            self.fields["variants"].initial = payload.get("variant_ids", [])
        elif kind == "cart_min_total":
            self.fields["threshold"].initial = payload.get("threshold")
        elif kind == "qty_at_least":
            self.fields["qty"].initial = payload.get("qty")

        # --- Queryset filtering (کلید ماجرا همینجاست) ---
        campaign_id = getattr(obj, "campaign_id", None)

        # محصولات استفاده‌شده در سایر کمپین‌ها
        used_product_ids = _used_ids_for_kind("product_in", exclude_campaign_id=campaign_id)

        # واریانت‌های استفاده‌شده در سایر کمپین‌ها (اختیاری)
        used_variant_ids = _used_ids_for_kind("variant_in", exclude_campaign_id=campaign_id)

        # محصولات همین rule (برای اینکه هنگام edit قفل نشه)
        current_product_ids = set(_flatten_ids(payload.get("product_ids") or []))
        current_variant_ids = set(_flatten_ids(payload.get("variant_ids") or []))

        # 1) queryset محصولات
        pqs = Product.objects.all()

        # حذف محصولاتی که قبلاً تو کمپین‌های دیگر بوده‌اند
        if used_product_ids:
            pqs = pqs.exclude(id__in=used_product_ids)

        # حذف محصولاتی که sale داخلی دارند (این قسمت را با فیلد واقعی مدل خودت تنظیم کن)
        # ✅ یکی/چندتا از این‌ها را مطابق مدل‌ات نگه دار:
        # pqs = pqs.exclude(_product_sale_active=True)
        # pqs = pqs.exclude(sale_active=True)
        # pqs = pqs.exclude(sale_percent__gt=0)
        # pqs = pqs.exclude(sale_amount__gt=0)

        # ⚠️ چون من فیلدهای دقیق Product تو پروژه‌ات را اینجا ندارم،
        # فعلاً این خط را کامنت می‌گذارم تا خطا ندهد:
        # pqs = pqs.exclude(_product_sale_active=True)

        # محصولات خود همین rule را دوباره اضافه کن (در edit)
        # --- products queryset ---
        if current_product_ids:
            pqs = (pqs | Product.objects.filter(id__in=current_product_ids)).distinct()

        products_field = self.fields.get("products")
        if isinstance(products_field, forms.ModelMultipleChoiceField):
            products_field.queryset = pqs

        # --- variants queryset ---
        vqs = ProductVariant.objects.select_related("product").all()

        if used_variant_ids:
            vqs = vqs.exclude(id__in=used_variant_ids)

        if current_variant_ids:
            vqs = (vqs | ProductVariant.objects.filter(id__in=current_variant_ids)).distinct()

        variants_field = self.fields.get("variants")
        if isinstance(variants_field, forms.ModelMultipleChoiceField):
            variants_field.queryset = vqs

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")

        def require(field, msg):
            if not cleaned.get(field):
                raise ValidationError({field: msg})

        if kind == "category_in":
            require("categories", "حداقل یک دسته انتخاب کنید.")
        elif kind == "brand_in":
            require("brands", "حداقل یک برند انتخاب کنید.")
        elif kind == "product_in":
            require("products", "حداقل یک محصول انتخاب کنید.")
        elif kind == "variant_in":
            require("variants", "حداقل یک واریانت انتخاب کنید.")
        elif kind == "cart_min_total":
            require("threshold", "حداقل مبلغ سبد را وارد کنید.")
        elif kind == "qty_at_least":
            require("qty", "حداقل تعداد را وارد کنید.")

        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        kind = self.cleaned_data.get("kind")

        if kind == "category_in":
            cats = self.cleaned_data.get("categories")
            obj.payload = {"category_ids": list(cats.values_list("id", flat=True))}
        elif kind == "brand_in":
            brands = self.cleaned_data.get("brands")
            obj.payload = {"brand_ids": list(brands.values_list("id", flat=True))}
        elif kind == "product_in":
            products = self.cleaned_data.get("products")
            obj.payload = {"product_ids": list(products.values_list("id", flat=True))}
        elif kind == "variant_in":
            variants = self.cleaned_data.get("variants")
            obj.payload = {"variant_ids": list(variants.values_list("id", flat=True))}
        elif kind == "cart_min_total":
            obj.payload = {"threshold": str(self.cleaned_data.get("threshold") or 0)}
        elif kind == "qty_at_least":
            obj.payload = {"qty": int(self.cleaned_data.get("qty") or 1)}
        else:
            obj.payload = obj.payload or {}

        if commit:
            obj.save()
        return obj



class PromoBannerAdminForm(forms.ModelForm):
    """
    PromoBanner Admin Form (Campaign-first)

    - product_filter پشت‌صحنه ساخته می‌شود و در ادمین Hidden است.
    - اگر campaign انتخاب شود:
        * فیلترهای محصول بنر (kind/categories/brands/products/variants/limit) نمایش داده نمی‌شوند
        * حتی اگر کسی دستی POST کند، بی‌اثر و پاک می‌شوند
        * channel/starts_at/ends_at از کمپین گرفته می‌شود و فیلدها قفل می‌شوند
    - اگر campaign انتخاب نشود (اختیاری):
        * فیلترهای محصول فعال‌اند و product_filter از روی انتخاب‌ها ساخته می‌شود
    """

    FILTER_CHOICES = (
        ("", "بدون فیلتر"),
        ("brand_in", "فقط از برندها"),
        ("product_in", "فقط محصولات خاص"),
        ("variant_in", "فقط واریانت‌های خاص"),
        ("category_in", "فقط از دسته‌ها"),
    )

    filter_kind = forms.ChoiceField(
        required=False,
        label="نوع فیلتر محصول",
        choices=FILTER_CHOICES,
    )

    filter_categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label="دسته‌ها",
    )
    filter_brands = forms.ModelMultipleChoiceField(
        queryset=Brand.objects.all(),
        required=False,
        label="برندها",
    )
    filter_products = forms.ModelMultipleChoiceField(
        queryset=Product.objects.all(),
        required=False,
        label="محصولات",
    )
    filter_variants = forms.ModelMultipleChoiceField(
        queryset=ProductVariant.objects.all(),
        required=False,
        label="واریانت‌ها",
    )

    show_countdown = forms.BooleanField(
        required=False,
        label="نمایش کانت‌داون",
        help_text="اگر فعال باشد، کانت‌داون روی بنر نمایش داده می‌شود.",
    )

    show_before_campaign = forms.BooleanField(
        required=False,
        label="نمایش قبل از شروع کمپین (پیش‌جشنواره)",
        help_text="اگر فعال باشد، بنر حتی قبل از شروع کمپین نمایش داده می‌شود (برای کانت‌داون).",
    )

    countdown_mode = forms.ChoiceField(
        required=False,
        label="کانت‌داون تا",
        choices=(
            ("", "بدون کانت‌داون"),
            ("auto", "خودکار (قبل شروع: تا شروع / هنگام اجرا: تا پایان)"),
            ("starts_at", "تا شروع کمپین"),
            ("ends_at", "تا پایان کمپین"),
        ),
        initial="auto",
    )

    class Meta:
        model = PromoBanner
        fields = "__all__"

    FILTER_FIELDS = [
        "filter_kind",
        "filter_categories",
        "filter_brands",
        "filter_products",
        "filter_variants",
        "limit_products",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # product_filter باید پشت صحنه باشد
        if "product_filter" in self.fields:
            self.fields["product_filter"].required = False
            self.fields["product_filter"].widget = forms.HiddenInput()

        obj = getattr(self, "instance", None)

        # campaign را هم برای add (از POST) و هم edit تشخیص بده
        campaign = None
        if obj and obj.pk:
            campaign = obj.campaign
        if not campaign:
            cid = self.data.get("campaign") or self.initial.get("campaign")
            if cid:
                campaign = Campaign.objects.filter(pk=cid).first()

        # ---------- Prefill فیلترها (فقط وقتی campaign نداریم) ----------
        pf = (getattr(obj, "product_filter", None) or {}) if obj and obj.pk else {}
        kind = (pf.get("kind") or "").strip()
        self.fields["filter_kind"].initial = kind

        if kind == "category_in":
            self.fields["filter_categories"].initial = pf.get("category_ids", [])
        elif kind == "brand_in":
            self.fields["filter_brands"].initial = pf.get("brand_ids", [])
        elif kind == "product_in":
            self.fields["filter_products"].initial = pf.get("product_ids", [])
        elif kind == "variant_in":
            self.fields["filter_variants"].initial = pf.get("variant_ids", [])

        # ---------- Prefill کانت‌داون از payload ----------
        payload = (getattr(obj, "payload", None) or {}) if obj and obj.pk else {}
        self.fields["show_before_campaign"].initial = bool(payload.get("show_before_campaign"))
        self.fields["countdown_mode"].initial = payload.get("countdown_mode") or "auto"
        self.fields["show_countdown"].initial = bool(payload.get("show_countdown"))

        # ---------- اگر campaign انتخاب شده: بنر فقط connector است ----------
        if campaign:
            # فیلترهای محصول را مخفی کن
            for f in self.FILTER_FIELDS:
                if f in self.fields:
                    self.fields[f].required = False
                    self.fields[f].widget = forms.HiddenInput()

            # (اختیاری) این 3 تا را قفل کن تا ادمین نتواند خلاف کمپین ست کند
            for f in ["channel", "starts_at", "ends_at"]:
                if f in self.fields:
                    self.fields[f].disabled = True

            # مقدار نمایشی اولیه از کمپین
            if "channel" in self.fields:
                self.fields["channel"].initial = campaign.channel
            if "starts_at" in self.fields:
                self.fields["starts_at"].initial = campaign.starts_at
            if "ends_at" in self.fields:
                self.fields["ends_at"].initial = campaign.ends_at

    # -------------------------
    # Helpers
    # -------------------------
    def _build_product_filter(self) -> dict:
        kind = (self.cleaned_data.get("filter_kind") or "").strip()
        if not kind:
            return {}

        if kind == "category_in":
            cats = self.cleaned_data.get("filter_categories")
            return {"kind": kind, "category_ids": list(cats.values_list("id", flat=True))}

        if kind == "brand_in":
            brands = self.cleaned_data.get("filter_brands")
            return {"kind": kind, "brand_ids": list(brands.values_list("id", flat=True))}

        if kind == "product_in":
            products = self.cleaned_data.get("filter_products")
            return {"kind": kind, "product_ids": list(products.values_list("id", flat=True))}

        if kind == "variant_in":
            variants = self.cleaned_data.get("filter_variants")
            return {"kind": kind, "variant_ids": list(variants.values_list("id", flat=True))}

        return {}

    def _sync_payload_flags(self, obj: PromoBanner):
        payload = obj.payload or {}

        show_before = bool(self.cleaned_data.get("show_before_campaign"))
        countdown_mode = (self.cleaned_data.get("countdown_mode") or "").strip()
        show_countdown = bool(self.cleaned_data.get("show_countdown"))

        if show_before:
            payload["show_before_campaign"] = True
        else:
            payload.pop("show_before_campaign", None)

        if countdown_mode:
            payload["countdown_mode"] = countdown_mode
        else:
            payload.pop("countdown_mode", None)

        if show_countdown:
            payload["show_countdown"] = True
        else:
            payload.pop("show_countdown", None)

        obj.payload = payload

    # -------------------------
    # Validation
    # -------------------------
    def clean(self):
        cleaned = super().clean()

        campaign = cleaned.get("campaign")
        kind = (cleaned.get("filter_kind") or "").strip()

        # کانت‌داون/پیش‌جشنواره فقط با campaign معنی دارد
        show_before = bool(cleaned.get("show_before_campaign"))
        countdown_mode = (cleaned.get("countdown_mode") or "").strip()
        if (show_before or countdown_mode) and not campaign:
            raise ValidationError({"campaign": "برای پیش‌جشنواره/کانت‌داون باید یک کمپین انتخاب کنید."})

        # اگر campaign داریم => بنر فقط connector، پس فیلترهای محصول بی‌اثر
        if campaign:
            # جلوی هر POST دستی را هم بگیر
            cleaned["filter_kind"] = ""
            cleaned["limit_products"] = None

            # اگر مدل فیلدهای filter_* جداگانه دارد، اهمیتی ندارد؛ در save پاک می‌کنیم
            return cleaned

        # اگر campaign نداریم => فیلتر اختیاری است، ولی اگر kind انتخاب شد باید مقدارش هم بیاید
        if kind == "category_in" and not cleaned.get("filter_categories"):
            raise ValidationError({"filter_categories": "حداقل یک دسته انتخاب کنید."})
        if kind == "brand_in" and not cleaned.get("filter_brands"):
            raise ValidationError({"filter_brands": "حداقل یک برند انتخاب کنید."})
        if kind == "product_in" and not cleaned.get("filter_products"):
            raise ValidationError({"filter_products": "حداقل یک محصول انتخاب کنید."})
        if kind == "variant_in" and not cleaned.get("filter_variants"):
            raise ValidationError({"filter_variants": "حداقل یک واریانت انتخاب کنید."})

        return cleaned

    # -------------------------
    # Save
    # -------------------------
    def save(self, commit=True):
        obj: PromoBanner = super().save(commit=False)

        # payload flags
        self._sync_payload_flags(obj)

        # اگر campaign انتخاب شده => sync کامل با کمپین + پاکسازی فیلتر محصول
        if obj.campaign_id:
            c = obj.campaign

            # بنر زمان/کانال را از کمپین می‌گیرد
            obj.channel = c.channel
            obj.starts_at = c.starts_at
            obj.ends_at = c.ends_at

            # بنر کمپینی = بدون فیلتر محصول
            obj.product_filter = {}
            # اگر روی مدل این فیلدها وجود دارند، پاک کن (برای تمیزی داده)
            for f in ["filter_kind", "limit_products"]:
                if hasattr(obj, f):
                    setattr(obj, f, "" if f == "filter_kind" else None)

        else:
            # بنر غیرکمپینی (اختیاری): product_filter بساز
            obj.product_filter = self._build_product_filter()

        if commit:
            obj.save()
        return obj



# class PromoBannerAdminForm(forms.ModelForm):
#     """
#     PromoBanner Admin Form (Flexible + Safe)
#
#     - product_filter پشت‌صحنه ساخته می‌شود و در ادمین Hidden است
#     - اگر بنر به کمپین وصل باشد و کمپین rule از نوع brand_in داشته باشد:
#         * انتخاب‌های بنر (brand/product/variant) فقط به همان برندها محدود می‌شود
#         * و Validation هم enforce می‌کند بیرون دامنه انتخاب نشود
#     - Category عملاً اختیاری است (می‌تونی نگه داری، ولی در این نسخه تمرکز روی brand است)
#     """
#
#     FILTER_CHOICES = (
#         ("", "بدون فیلتر"),
#         ("brand_in", "فقط از برندها"),
#         ("product_in", "فقط محصولات خاص"),
#         ("variant_in", "فقط واریانت‌های خاص"),
#         # اگر بعداً خواستی:
#         ("category_in", "فقط از دسته‌ها"),
#     )
#
#     filter_kind = forms.ChoiceField(
#         required=False,
#         label="نوع فیلتر محصول",
#         choices=FILTER_CHOICES,
#     )
#
#     # (اختیاری) اگر گفتی کتگوری لازم نیست، می‌تونی کلاً حذفش کنی
#     filter_categories = forms.ModelMultipleChoiceField(
#         queryset=Category.objects.all(),
#         required=False,
#         label="دسته‌ها",
#     )
#
#     filter_brands = forms.ModelMultipleChoiceField(
#         queryset=Brand.objects.all(),
#         required=False,
#         label="برندها",
#     )
#
#     filter_products = forms.ModelMultipleChoiceField(
#         queryset=Product.objects.all(),
#         required=False,
#         label="محصولات",
#     )
#
#     filter_variants = forms.ModelMultipleChoiceField(
#         queryset=ProductVariant.objects.all(),
#         required=False,
#         label="واریانت‌ها",
#     )
#
#     show_countdown = forms.BooleanField(
#         required=False,
#         label="نمایش کانت‌داون",
#         help_text="اگر فعال باشد، کانت‌داون روی بنر نمایش داده می‌شود.",
#     )
#
#     show_before_campaign = forms.BooleanField(
#         required=False,
#         label="نمایش قبل از شروع کمپین (پیش‌جشنواره)",
#         help_text="اگر فعال باشد، بنر حتی قبل از شروع کمپین نمایش داده می‌شود (برای کانت‌داون).",
#     )
#
#     countdown_mode = forms.ChoiceField(
#         required=False,
#         label="کانت‌داون تا",
#         choices=(
#             ("", "بدون کانت‌داون"),
#             ("auto", "خودکار (قبل شروع: تا شروع / هنگام اجرا: تا پایان)"),
#             ("starts_at", "تا شروع کمپین"),
#             ("ends_at", "تا پایان کمپین"),
#         ),
#         initial="auto",
#     )
#
#     class Meta:
#         model = PromoBanner
#         fields = "__all__"
#
#     # -------------------------
#     # Helpers
#     # -------------------------
#     def _campaign_brand_ids(self, campaign) -> set[int]:
#         """
#         brand_ids را از ruleهای کمپین (brand_in) استخراج می‌کند.
#         """
#         if not campaign:
#             return set()
#         ids: set[int] = set()
#         for r in campaign.rules.all():
#             if r.kind == "brand_in":
#                 ids.update((r.payload or {}).get("brand_ids", []))
#         return ids
#
#     def _limit_querysets_by_campaign(self, campaign):
#         """
#         اگر کمپین brand_in داشته باشد، queryset فیلدهای بنر محدود می‌شود.
#         """
#         brand_ids = self._campaign_brand_ids(campaign)
#         if not brand_ids:
#             return
#
#         self.fields["filter_brands"].queryset = Brand.objects.filter(id__in=brand_ids)
#         self.fields["filter_products"].queryset = Product.objects.filter(brand_id__in=brand_ids)
#         self.fields["filter_variants"].queryset = ProductVariant.objects.filter(product__brand_id__in=brand_ids)
#
#         # چون گفتی category لازم نیست، اینجا دست نمی‌زنیم
#         # اگر خواستی: می‌تونیم category را هم با همین سیاست محدود کنیم
#
#     def _build_product_filter(self) -> dict:
#         """
#         از روی filter_kind و انتخاب‌ها، product_filter را می‌سازد.
#         """
#         kind = (self.cleaned_data.get("filter_kind") or "").strip()
#
#         if not kind:
#             return {}
#
#         if kind == "category_in":
#             cats = self.cleaned_data.get("filter_categories")
#             return {"kind": kind, "category_ids": list(cats.values_list("id", flat=True))}
#
#         if kind == "brand_in":
#             brands = self.cleaned_data.get("filter_brands")
#             return {"kind": kind, "brand_ids": list(brands.values_list("id", flat=True))}
#
#         if kind == "product_in":
#             products = self.cleaned_data.get("filter_products")
#             return {"kind": kind, "product_ids": list(products.values_list("id", flat=True))}
#
#         if kind == "variant_in":
#             variants = self.cleaned_data.get("filter_variants")
#             return {"kind": kind, "variant_ids": list(variants.values_list("id", flat=True))}
#
#         return {}
#
#     def _sync_payload_flags(self, obj: PromoBanner):
#         """
#         فلگ‌های جشنواره/کانت‌داون را روی payload می‌نویسد.
#         """
#         payload = obj.payload or {}
#
#         show_before = bool(self.cleaned_data.get("show_before_campaign"))
#         countdown_mode = (self.cleaned_data.get("countdown_mode") or "").strip()
#         show_countdown = bool(self.cleaned_data.get("show_countdown"))
#
#         # show_before_campaign
#         if show_before:
#             payload["show_before_campaign"] = True
#         else:
#             payload.pop("show_before_campaign", None)
#
#         # countdown_mode
#         if countdown_mode:
#             payload["countdown_mode"] = countdown_mode
#         else:
#             payload.pop("countdown_mode", None)
#
#         # show_countdown
#         if show_countdown:
#             payload["show_countdown"] = True
#         else:
#             payload.pop("show_countdown", None)
#
#         obj.payload = payload
#
#     -------------------------