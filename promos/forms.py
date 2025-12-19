# promos/forms.py
from __future__ import annotations

from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import PromoBanner
from .models import Rule
from products.models import Category, Brand, Product, ProductVariant



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
        queryset=Product.objects.all(),
        required=False,
        label="محصولات",
    )
    variants = forms.ModelMultipleChoiceField(
        queryset=ProductVariant.objects.all(),
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

        # payload نباید دستی ادیت شود
        if "payload" in self.fields:
            self.fields["payload"].required = False
            self.fields["payload"].widget = forms.HiddenInput()

        # prefill از payload هنگام edit
        obj = getattr(self, "instance", None)
        payload = (getattr(obj, "payload", None) or {}) if obj and obj.pk else {}

        kind = (obj.kind if obj and obj.pk else None)
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
    ادمین‌پسند برای PromoBanner:
    - product_filter پشت‌صحنه ساخته میشه
    """
    filter_kind = forms.ChoiceField(
        required=False,
        label="نوع فیلتر محصول",
        choices=(
            ("", "بدون فیلتر"),
            ("category_in", "فقط از دسته‌ها"),
            ("brand_in", "فقط از برندها"),
            ("product_in", "فقط محصولات خاص"),
            ("variant_in", "فقط واریانت‌های خاص"),
        ),
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

    class Meta:
        model = PromoBanner
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # product_filter را از ادمین قایم می‌کنیم
        if "product_filter" in self.fields:
            self.fields["product_filter"].required = False
            self.fields["product_filter"].widget = forms.HiddenInput()

        obj = getattr(self, "instance", None)
        pf = (getattr(obj, "product_filter", None) or {}) if obj and obj.pk else {}

        # prefill
        kind = pf.get("kind", "")
        self.fields["filter_kind"].initial = kind
        if kind == "category_in":
            self.fields["filter_categories"].initial = pf.get("category_ids", [])
        elif kind == "brand_in":
            self.fields["filter_brands"].initial = pf.get("brand_ids", [])
        elif kind == "product_in":
            self.fields["filter_products"].initial = pf.get("product_ids", [])
        elif kind == "variant_in":
            self.fields["filter_variants"].initial = pf.get("variant_ids", [])

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("filter_kind") or ""

        # اعتبارسنجی ساده و انسانی
        if kind == "category_in" and not cleaned.get("filter_categories"):
            raise ValidationError({"filter_categories": "حداقل یک دسته انتخاب کنید."})
        if kind == "brand_in" and not cleaned.get("filter_brands"):
            raise ValidationError({"filter_brands": "حداقل یک برند انتخاب کنید."})
        if kind == "product_in" and not cleaned.get("filter_products"):
            raise ValidationError({"filter_products": "حداقل یک محصول انتخاب کنید."})
        if kind == "variant_in" and not cleaned.get("filter_variants"):
            raise ValidationError({"filter_variants": "حداقل یک واریانت انتخاب کنید."})

        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        kind = self.cleaned_data.get("filter_kind") or ""

        if not kind:
            obj.product_filter = {}
        elif kind == "category_in":
            cats = self.cleaned_data["filter_categories"]
            obj.product_filter = {"kind": kind, "category_ids": list(cats.values_list("id", flat=True))}
        elif kind == "brand_in":
            brands = self.cleaned_data["filter_brands"]
            obj.product_filter = {"kind": kind, "brand_ids": list(brands.values_list("id", flat=True))}
        elif kind == "product_in":
            products = self.cleaned_data["filter_products"]
            obj.product_filter = {"kind": kind, "product_ids": list(products.values_list("id", flat=True))}
        elif kind == "variant_in":
            variants = self.cleaned_data["filter_variants"]
            obj.product_filter = {"kind": kind, "variant_ids": list(variants.values_list("id", flat=True))}

        if commit:
            obj.save()
        return obj


