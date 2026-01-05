# products/admin.py
from django import forms
from django.contrib import admin, messages
from django.db.models import Count, Sum
from django.utils.text import slugify
from django.db.models.functions import Coalesce
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import path, reverse
from decimal import Decimal
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType
from django.db.models import Avg, Count
from Core.models import Rating
from .models import (
    Category, Color, Brand, Product, ProductVariant, ProductImage,
    Attribute, AttributeChoice, CategoryAttribute, ProductAttributeValue, SizeGroup,
    Size,Service, ServicePrice, CategoryService, ProductService
)
from Core.admin_mixins import JalaliAdminMixin
from django.contrib.admin.widgets import FilteredSelectMultiple
from mptt.admin import DraggableMPTTAdmin
from django.contrib.humanize.templatetags.humanize import intcomma
from mptt.exceptions import InvalidMove
# products/admin.py
from django.db.models import OuterRef, Subquery, Sum, Count, IntegerField, Q
from django.db.models.functions import Coalesce



# helpers: pass parent_obj (Product یا Product موقتی) به فرم‌های Inline
class ParentAwareInlineMixin:
    """
    - در change: parent همان obj است.
    - در add: اگر ?category=<id> باشد، یک Product موقتی با آن کتگوری می‌سازیم تا فرم‌ها بتوانند بر اساسش فیلتر شوند.
    """
    def _resolve_parent(self, request, obj):
        if obj:
            return obj
        cat_id = _selected_category_id(request, obj=None)
        if not cat_id:
            return None
        try:
            cat = Category.objects.only("id").get(pk=cat_id)
            return Product(category=cat)  # فقط برای فرم (سیو نمی‌شود)
        except Category.DoesNotExist:
            return None

    def get_formset(self, request, obj=None, **kwargs):
        FS = super().get_formset(request, obj, **kwargs)
        parent = self._resolve_parent(request, obj)

        class _FS(FS):
            def _construct_form(self, i, **k):
                k["parent_obj"] = parent
                return super()._construct_form(i, **k)
        return _FS


class AttributeChoiceForm(forms.ModelForm):
    class Meta:
        model = AttributeChoice
        fields = ("value", "label", "position")
        widgets = {
            "value": forms.TextInput(attrs={
                "placeholder": "مثلاً: cotton",
                "dir": "ltr",
            }),
            "label": forms.TextInput(attrs={
                "placeholder": "مثلاً: پنبه‌ای",
            }),
        }

    def clean(self):
        cleaned = super().clean()
        val = (cleaned.get("value") or "").strip()
        lbl = (cleaned.get("label") or "").strip()

        # اگر کاربر value را خالی گذاشت و label لاتین بود، خودکار از label اسلاگ بساز
        if not val and lbl:
            # فقط حروف/اعداد و فاصله و - _ را نگه داریم
            # و بعد اسلاگ ASCII بسازیم تا با UniqueConstraint به مشکل نخورد
            auto = slugify(lbl, allow_unicode=False)
            if auto:
                cleaned["value"] = auto

        # هنوز خالی؟ خطا بده تا کاربر کُد بگذارد
        if not cleaned.get("value"):
            raise forms.ValidationError("فیلد «مقدار (کُد)» باید پر باشد (مثلاً cotton).")

        return cleaned

# =============== Helpers ===============
def _selected_category_id(request, obj=None):
    if obj and getattr(obj, "category_id", None):
        return obj.category_id
    return request.POST.get("category") or request.GET.get("category")


# =============== Inlines & Forms ===============

class ProductAttributeValueForm(forms.ModelForm):
    class Meta:
        model = ProductAttributeValue
        fields = ("attribute", "value_text", "value_int", "value_decimal", "value_bool", "value_choice", "values_multi")

    def __init__(self, *args, **kwargs):
        self.parent_obj = kwargs.pop("parent_obj", None)
        super().__init__(*args, **kwargs)

        # 1) فهرست Attribute
        if self.parent_obj and self.parent_obj.category_id:
            allowed_attr_ids = list(
                self.parent_obj.category.effective_category_attributes()
                .values_list("attribute_id", flat=True)
            )
            if allowed_attr_ids:
                self.fields["attribute"].queryset = (
                    Attribute.objects.filter(id__in=allowed_attr_ids, is_active=True)
                    .order_by("position", "id")
                )
            else:
                # Fallback: همهٔ فعال‌ها
                self.fields["attribute"].queryset = (
                    Attribute.objects.filter(is_active=True).order_by("position", "id")
                )
        else:
            # حالت Add بدون کتگوری: همهٔ فعال‌ها
            self.fields["attribute"].queryset = (
                Attribute.objects.filter(is_active=True).order_by("position", "id")
            )

        # 2) پر کردن choices بسته به «attribute»
        attr = None
        if getattr(self.instance, "pk", None):
            attr = self.instance.attribute
        else:
            for key in self.data:
                if key.endswith("-attribute") and key.startswith(self.prefix):
                    try:
                        aid = int(self.data.get(key) or 0)
                        if aid: attr = Attribute.objects.filter(pk=aid).first()
                    except ValueError:
                        pass
                    break

        qs = AttributeChoice.objects.filter(attribute=attr).order_by("position",
                                                                     "id") if attr else AttributeChoice.objects.none()
        self.fields["value_choice"].queryset = qs
        self.fields["values_multi"].queryset = qs


class PAVInlineForm(forms.ModelForm):
    class Meta:
        model = ProductAttributeValue
        fields = ("attribute","value_text","value_int","value_decimal","value_bool","value_choice","values_multi")

    def __init__(self, *args, **kwargs):
        parent: Product | None = kwargs.pop("parent_obj", None)
        super().__init__(*args, **kwargs)

        allowed_attr_ids = []
        if parent and parent.category_id:
            allowed_attr_ids = list(
                parent.category.effective_category_attributes()
                .values_list("attribute_id", flat=True)
            )

        inst_attr_id = getattr(self.instance, "attribute_id", None)
        if inst_attr_id and inst_attr_id not in allowed_attr_ids:
            allowed_attr_ids.append(inst_attr_id)

        if allowed_attr_ids:
            qs_attr = Attribute.objects.filter(id__in=allowed_attr_ids, is_active=True).order_by("position","id")
        else:
            # Fallback: همهٔ فعال‌ها، تا همیشه به «ویژگی‌های از قبل» دسترسی داشته باشی
            qs_attr = Attribute.objects.filter(is_active=True).order_by("position","id")

        self.fields["attribute"].queryset = qs_attr

        selected_attr = None

        # 1. اگر instance از قبل ویژگی دارد (ویرایش)
        if getattr(self.instance, "attribute_id", None):
            selected_attr = self.instance.attribute

        # 2. اگر در داده‌های POST هست
        if not selected_attr:
            for key in self.data:
                if key.endswith("-attribute") and key.startswith(self.prefix):
                    try:
                        aid = int(self.data.get(key) or 0)
                        if aid:
                            selected_attr = Attribute.objects.filter(pk=aid).first()
                    except ValueError:
                        pass
                    break

        # ✅ 3. حالت تازه ایجاد‌شده در add mode (instance خالی ولی attribute ست‌شده در initial)
        if not selected_attr and self.initial.get("attribute"):
            selected_attr = Attribute.objects.filter(pk=self.initial["attribute"]).first()

        qs = AttributeChoice.objects.filter(attribute=selected_attr).order_by("position","id") if selected_attr else AttributeChoice.objects.none()
        self.fields["value_choice"].queryset = qs
        self.fields["values_multi"].queryset = qs

    def clean(self):
        cleaned = super().clean()
        attr = cleaned.get("attribute")
        if not attr:
            raise forms.ValidationError("ابتدا «ویژگی» را انتخاب کن.")

        kind = attr.kind
        vt = cleaned.get("value_text")
        vi = cleaned.get("value_int")
        vd = cleaned.get("value_decimal")
        vb = cleaned.get("value_bool")
        vc = cleaned.get("value_choice")
        vm = list(cleaned.get("values_multi") or [])

        def any_set(*vals): return any(v not in (None, "", [], False) for v in vals)

        if kind == "text":
            if not any_set(vt): raise forms.ValidationError("برای «متن» فیلد متن را پر کن.")
            cleaned.update(value_int=None, value_decimal=None, value_bool=None, value_choice=None); cleaned["values_multi"]=[]
        elif kind == "int":
            if vi is None: raise forms.ValidationError("برای «عدد صحیح» فیلد عدد را پر کن.")
            cleaned.update(value_text="", value_decimal=None, value_bool=None, value_choice=None); cleaned["values_multi"]=[]
        elif kind == "decimal":
            if vd is None: raise forms.ValidationError("برای «عدد اعشاری» فیلد اعشاری را پر کن.")
            cleaned.update(value_text="", value_int=None, value_bool=None, value_choice=None); cleaned["values_multi"]=[]
        elif kind == "bool":
            if vb is None: raise forms.ValidationError("برای «بلی/خیر» یکی را انتخاب کن.")
            cleaned.update(value_text="", value_int=None, value_decimal=None, value_choice=None); cleaned["values_multi"]=[]
        elif kind == "choice":
            if not vc and not vm: raise forms.ValidationError("برای «گزینشی (تکی)» یک گزینه را انتخاب کن.")
            if vm and len(vm) > 1: raise forms.ValidationError("این ویژگی تکی است؛ فقط یک گزینه انتخاب کن.")
            cleaned["value_choice"] = vm[0] if (not vc and vm) else vc
            cleaned.update(value_text="", value_int=None, value_decimal=None, value_bool=None); cleaned["values_multi"]=[]
        elif kind == "multi":
            if not vm: raise forms.ValidationError("برای «چندگزینه‌ای» حداقل یک گزینه را انتخاب کن.")
            cleaned.update(value_text="", value_int=None, value_decimal=None, value_bool=None, value_choice=None)
        return cleaned


class ProductAttributeValueInline(admin.TabularInline):
    model = ProductAttributeValue
    form = PAVInlineForm
    extra = 1
    fields = ("attribute", "value_text", "value_int", "value_decimal",
              "value_bool", "value_choice", "values_multi")
    ordering = ("attribute", "id")

    def has_add_permission(self, request, obj=None):
        return True

    def get_min_num(self, request, obj=None, **kwargs):
        return 0

    def _resolve_parent(self, request, obj):
        if obj: return obj
        cat_id = _selected_category_id(request, obj=None)
        if not cat_id: return None
        try:
            cat = Category.objects.only("id").get(pk=cat_id)
            return Product(category=cat)  # فقط برای فرم
        except Category.DoesNotExist:
            return None

    def get_formset(self, request, obj=None, **kwargs):
        FS = super().get_formset(request, obj, **kwargs)
        parent = self._resolve_parent(request, obj)

        class _FS(FS):
            def _construct_form(self, i, **k):
                k["parent_obj"] = parent
                return super()._construct_form(i, **k)
        return _FS


    def get_extra(self, request, obj=None, **kwargs):
        parent = self._resolve_parent(request, obj)
        if not parent or not parent.category_id:
            return 1
        allowed_ids = set(parent.category.effective_category_attributes()
                          .values_list("attribute_id", flat=True))
        existing_ids = set(
            ProductAttributeValue.objects.filter(product=obj)
            .values_list("attribute_id", flat=True)
        ) if obj else set()
        remaining = len(allowed_ids - existing_ids)
        return max(1, min(remaining or 1, 25))

    def get_max_num(self, request, obj=None, **kwargs):
        return 1000



# پایین فایل (یا نزدیک تعریف ProductVariantInlineForm)


# Images
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ("thumb", "image", "color", "alt", "is_primary", "position")
    readonly_fields = ("thumb",)
    autocomplete_fields = ("color",)
    ordering = ("position", "id")
    classes = ("collapse",)

    @admin.display(description=_("پیش‌نمایش"))
    def thumb(self, obj: ProductImage):
        if obj.pk and obj.image:
            try:
                return format_html('<img src="{}" style="height:56px;object-fit:cover;border-radius:6px;"/>',
                                   obj.image.url)
            except Exception:
                return "—"
        return "—"


class AttributeChoiceInline(admin.TabularInline):
    model = AttributeChoice
    form = AttributeChoiceForm
    extra = 0
    fields = ("value", "label", "position")
    ordering = ("position", "id")
    prepopulated_fields = {"value": ("label",)}


class CategoryAttributeInline(admin.TabularInline):
    model = CategoryAttribute
    extra = 0
    fields = ("attribute", "is_required", "position")
    autocomplete_fields = ("attribute",)
    ordering = ("position", "id")


# =============== Category (MPTT) ===============

class IndentedCategoryChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        depth = getattr(obj, "level", 0) or 0
        return f"{'— ' * depth}{obj.name}"


class CategoryAdminForm(forms.ModelForm):
    parent = IndentedCategoryChoiceField(
        queryset=Category.objects.none(),
        required=False,
        label=_("والد"),
        help_text=_("برای قرار دادن این دسته زیرمجموعهٔ دیگری، والد را انتخاب کنید.")
    )

    class Meta:
        model = Category
        fields = ["name", "slug", "parent", "size_group", "is_active", "position", "image", "meta_title",
                  "meta_description"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Category.objects.all().order_by("tree_id", "lft")
        if self.instance and self.instance.pk:
            banned = list(self.instance.get_descendants(include_self=True).values_list("id", flat=True))
            qs = qs.exclude(id__in=banned)
        self.fields["parent"].queryset = qs

    def clean_parent(self):
        parent = self.cleaned_data.get("parent")
        inst = self.instance
        if inst and inst.pk and parent:
            if parent.pk == inst.pk:
                raise forms.ValidationError(_("یک نود نمی‌تواند والد خودش باشد."))
            if inst.get_descendants(include_self=True).filter(pk=parent.pk).exists():
                raise forms.ValidationError(_("نمی‌توانید یکی از فرزندان را به‌عنوان والد انتخاب کنید."))
        return parent


class RootFilter(admin.SimpleListFilter):
    title = _("سطح ریشه")
    parameter_name = "is_root"

    def lookups(self, request, model_admin):
        return ("1", _("فقط ریشه‌ها")), ("0", _("غیر ریشه"))

    def queryset(self, request, qs):
        if self.value() == "1":
            return qs.filter(parent__isnull=True)
        if self.value() == "0":
            return qs.filter(parent__isnull=False)
        return qs


class LeafFilter(admin.SimpleListFilter):
    title = _("برگ‌ها (بدون فرزند)")
    parameter_name = "is_leaf"

    def lookups(self, request, model_admin):
        return (("1", _("فقط برگ‌ها")),)

    def queryset(self, request, qs):
        return qs.filter(children__isnull=True) if self.value() == "1" else qs


@admin.action(description=_("انتقال یک پله ↑ بین هم‌سطح‌ها"))
def move_up(modeladmin, request, queryset):
    moved = 0
    for obj in queryset:
        prev = obj.get_previous_sibling()
        if prev:
            try:
                obj.move_to(prev, "left");
                obj.save();
                moved += 1
            except InvalidMove:
                pass
    if moved:
        messages.success(request, _("%d مورد جابه‌جا شد.") % moved)


@admin.action(description=_("انتقال یک پله ↓ بین هم‌سطح‌ها"))
def move_down(modeladmin, request, queryset):
    moved = 0
    for obj in queryset:
        nxt = obj.get_next_sibling()
        if nxt:
            try:
                obj.move_to(nxt, "right");
                obj.save()
                moved += 1
            except InvalidMove:
                pass
    if moved:
        messages.success(request, _("%d مورد جابه‌جا شد.") % moved)


@admin.action(description=_("فعال‌سازی"))
def make_active(modeladmin, request, queryset):
    messages.success(request, _("%d مورد فعال شد.") % queryset.update(is_active=True))


@admin.action(description=_("غیرفعال‌سازی"))
def make_inactive(modeladmin, request, queryset):
    messages.success(request, _("%d مورد غیرفعال شد.") % queryset.update(is_active=False))


@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    form = CategoryAdminForm
    mptt_indent_field = "name"
    mptt_level_indent = 18

    list_display = ("tree_actions", "indented_title", "size_group", "slug", "is_active", "position", "parent")
    list_display_links = ("indented_title",)
    list_editable = ("is_active", "position")
    list_filter = ("is_active", "size_group", RootFilter, LeafFilter)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    actions = (make_active, make_inactive, move_up, move_down)
    inlines = (CategoryAttributeInline,)
    list_per_page = 200
    list_select_related = ("parent",)

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("tree_id", "lft", "position", "id")


# =============== Color ===============

@admin.register(Color)
class ColorAdmin(JalaliAdminMixin):
    list_display = ("swatch", "name", "hex_code", "is_active", "updated_at")
    list_editable = ("is_active",)
    search_fields = ("name", "hex_code")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("is_active",)
    ordering = ("name",)

    @admin.display(description=_("نمونه رنگ"))
    def swatch(self, obj: Color):
        return format_html(
            '<span title="{}" style="display:inline-block;width:18px;height:18px;'
            'border-radius:50%;border:1px solid #ddd;background:{}"></span>',
            obj.hex_code, obj.hex_code
        )


# =============== Attribute Engine ===============

@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "kind", "unit", "is_variant", "position", "is_active")
    list_editable = ("position", "is_variant", "is_active")
    list_filter = ("kind", "is_variant", "is_active")
    search_fields = ("name", "code")
    ordering = ("position", "id")
    inlines = (AttributeChoiceInline,)


@admin.register(AttributeChoice)
class AttributeChoiceAdmin(admin.ModelAdmin):
    search_fields = ("value", "label", "attribute__name", "attribute__code")
    list_display = ("label", "value", "attribute", "position")
    list_filter = ("attribute",)
    ordering = ("attribute", "position", "id")
    autocomplete_fields = ("attribute",)


@admin.register(CategoryAttribute)
class CategoryAttributeAdmin(admin.ModelAdmin):
    list_display = ("category", "attribute", "is_required", "position")
    list_filter = ("category", "attribute", "is_required")
    search_fields = ("category__name", "attribute__name", "attribute__code")
    ordering = ("category", "position", "id")
    autocomplete_fields = ("category", "attribute")


@admin.register(SizeGroup)
class SizeGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "note", "sizes_count")
    search_fields = ("name", "code")
    ordering = ("name",)

    @admin.display(description=_("تعداد سایز"))
    def sizes_count(self, obj):
        return obj.sizes.count()


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ("label", "code", "group", "rank")
    list_editable = ("rank",)
    list_filter = ("group",)
    search_fields = ("label", "code", "group__name", "group__code")  # برای autocomplete
    ordering = ("group", "rank", "id")
    autocomplete_fields = ("group",)


@admin.register(ProductVariant)
class ProductVariantAdmin(JalaliAdminMixin):
    list_display = ("product", "color",  "size", "sku", "price", "stock","weight_grams", "is_active", "updated_at")
    list_filter = ("is_active", "color", "size")
    search_fields = ("product__name", "sku", "barcode")
    autocomplete_fields = ("product", "color", "size")
    list_editable = ("price", "stock", "is_active")
    ordering = ("-updated_at",)
    list_select_related = ("product", "color", "size")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        def limit_size_for_product(product: Product):
            sg = product.get_size_group() if product else None
            if sg and "size" in form.base_fields:
                form.base_fields["size"].queryset = Size.objects.filter(group=sg).order_by("rank", "id")

        if obj:  # ویرایش
            limit_size_for_product(obj.product)
        else:  # افزودن جدید - اگر ?product=ID در URL باشد
            pid = request.GET.get("product") or request.POST.get("product")
            if pid:
                try:
                    p = Product.objects.get(pk=pid)
                    limit_size_for_product(p)
                except Product.DoesNotExist:
                    pass
        return form

# --- Variant Inline (single, clean) ---
class ProductVariantInlineForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = (
            "color", "size", "sku", "price", "stock", "is_active",

            "sale_active_variant", "sale_percent_variant", "sale_amount_variant",
        )

    def __init__(self, *args, **kwargs):
        parent: Product | None = kwargs.pop("parent_obj", None)
        super().__init__(*args, **kwargs)
        # پیش‌فرض: همه سایزها، تا خالی نماند
        self.fields["size"].queryset = Size.objects.all().order_by("group__id", "rank", "id")
        sg = None
        if parent and getattr(parent, "category_id", None):
            sg = parent.get_size_group()
        elif self.instance and self.instance.pk:
            sg = self.instance.product.get_size_group()
        if sg:
            qs = Size.objects.filter(group=sg).order_by("rank", "id")
            # اگر سایز ذخیره‌شده خارج از گروه باشد، همان را هم اضافه کن
            if self.instance and self.instance.size_id and self.instance.size.group_id != sg.id:
                qs = Size.objects.filter(pk=self.instance.size_id) | qs
            self.fields["size"].queryset = qs


class ProductVariantInline(ParentAwareInlineMixin, admin.TabularInline):
    model = ProductVariant
    form = ProductVariantInlineForm
    extra = 0
    fields = (
        "color", "size", "sku", "price", "stock", "is_active",

        "sale_active_variant", "sale_percent_variant", "sale_amount_variant",
    )
    autocomplete_fields = ("color", "size")
    classes = ("collapse",)

# =============== Product: filters & actions ===============

class HasImagesFilter(admin.SimpleListFilter):
    title = _("دارای تصویر")
    parameter_name = "has_images"

    def lookups(self, request, model_admin):
        return (("1", _("بله")), ("0", _("خیر")))

    def queryset(self, request, qs):
        qs = qs.annotate(_img_cnt=Count("images"))
        if self.value() == "1":
            return qs.filter(_img_cnt__gt=0)
        if self.value() == "0":
            return qs.filter(_img_cnt=0)
        return qs


class HasVariantsFilter(admin.SimpleListFilter):
    title = _("دارای واریانت")
    parameter_name = "has_variants"

    def lookups(self, request, model_admin):
        return (("1", _("بله")), ("0", _("خیر")))

    def queryset(self, request, qs):
        qs = qs.annotate(_var_cnt=Count("variants", distinct=True))
        if self.value() == "1":
            return qs.filter(_var_cnt__gt=0)
        if self.value() == "0":
            return qs.filter(_var_cnt=0)
        return qs


class CategoryRootFilter(admin.SimpleListFilter):
    title = _("فیلتر کتگوری‌ توسط ریشه")
    parameter_name = "by_root"

    def lookups(self, request, model_admin):
        roots = Category.objects.filter(parent__isnull=True).order_by("name")
        return [(str(r.id), r.name) for r in roots]

    def queryset(self, request, qs):
        rid = self.value()
        if not rid:
            return qs
        try:
            root = Category.objects.get(id=rid)
        except Category.DoesNotExist:
            return qs.none()
        ids = list(root.get_descendants(include_self=True).values_list("id", flat=True))
        return qs.filter(category_id__in=ids)


@admin.action(description=_("انتشار (Published)"))
def make_published(modeladmin, request, queryset):
    messages.success(request, _("%d مورد منتشر شد.") % queryset.update(status="pub", is_active=True))


@admin.action(description=_("پیش‌نویس (Draft)"))
def make_draft(modeladmin, request, queryset):
    messages.success(request, _("%d مورد پیش‌نویس شد.") % queryset.update(status="draft"))



@admin.action(description=_("آرشیو (Archived)"))
def make_archived(modeladmin, request, queryset):
    messages.success(request, _("%d مورد آرشیو شد.") % queryset.update(status="arch", is_active=False))


@admin.action(description=_("اگر تصویر اصلی تنظیم نیست، اولی را Primary کن"))
def ensure_primary_image(modeladmin, request, queryset):
    fixed = 0
    for p in queryset.prefetch_related("images"):
        if not p.images.filter(is_primary=True).exists():
            first = p.images.order_by("position", "id").first()
            if first:
                first.is_primary = True
                first.save(update_fields=["is_primary"])
                fixed += 1
    if fixed:
        messages.success(request, _("برای %d محصول تصویر اصلی تعیین شد.") % fixed)


@admin.action(description=_("کپی محصول (بدون کپی فایل‌ها)"))
def duplicate_products(modeladmin, request, queryset):
    created = 0
    for p in queryset.prefetch_related("variants", "images"):
        clone = Product(
            name=f"{p.name} (کپی)", slug="",
            category=p.category, brand_fk=p.brand_fk,
            short_description=p.short_description, description=p.description,
            price=p.price, compare_at_price=p.compare_at_price,
            status="draft", is_active=False,
            meta_title=p.meta_title, meta_description=p.meta_description,
            # attributes=p.attributes,
        )
        clone.save()
        # دسته‌های اضافی هم کپی شوند
        clone.additional_categories.set(p.additional_categories.all())

        for v in p.variants.all():
            ProductVariant.objects.create(
                product=clone, color=v.color, size=v.size, sku=f"COPY-{v.sku}",
                price=v.price, stock=v.stock, is_active=v.is_active,
            )
        for img in p.images.all():
            ProductImage.objects.create(
                product=clone, color=img.color, image=img.image,
                alt=img.alt, is_primary=img.is_primary, position=img.position,
            )
        created += 1
    if created:
        messages.success(request, _("%d محصول کپی شد (Draft).") % created)



# =============== Variant Admin ==============


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = "__all__"
        widgets = {
            "description": forms.Textarea(attrs={"rows": 10, "style": "width: 100%;"}),
        }

    def clean(self):
        cleaned = super().clean()
        sp = cleaned.get("sale_percent")
        sa = cleaned.get("sale_amount")
        if sp and sa:
            self.add_error("sale_amount", _("لطفاً یا درصد یا مبلغ را انتخاب کنید (نه هردو)."))

        if cleaned.get("status") == "pub" and not cleaned.get("is_active", True):
            raise forms.ValidationError(_("محصول منتشرشده باید فعال باشد."))

        price = cleaned.get("price")
        if price is None or price < 0:
            raise forms.ValidationError(_("قیمت پایهٔ محصول نامعتبر است."))

        cap = cleaned.get("compare_at_price")
        if cap is not None and cap <= price:
            self.add_error("compare_at_price", _("«قیمت قبلی» باید از قیمت فعلی بیشتر باشد."))

        cleaned["price"] = price.quantize(Decimal("0.01"))
        if cap is not None:
            cleaned["compare_at_price"] = cap.quantize(Decimal("0.01"))

        return cleaned

# =============== Product Admin ===============

@admin.register(Product)
class ProductAdmin(JalaliAdminMixin, admin.ModelAdmin):
    exclude = ("attributes",)
    form = ProductAdminForm

    inlines = [ProductVariantInline, ProductAttributeValueInline, ProductImageInline]

    list_display = (
        "thumb", "name", "category", "price", "status", "is_active", "average_rating_display", "rating_count_display",
        "variant_count_col", "stock_total_col", "created_at","shipping_flat_fee",
    )
    list_display_links = ("name", "thumb")
    list_editable = ("price", "status", "is_active")

    list_filter = ("status", "is_active", HasImagesFilter, HasVariantsFilter, CategoryRootFilter)
    search_fields = ("name", "slug", "brand_fk__name", "variants__sku")
    autocomplete_fields = ("category", "brand_fk")

    readonly_fields = ("created_at", "updated_at", "effective_price_admin", "average_rating_display", "rating_count_display")
    actions = (
        # اکشن‌های خودت + اکشن جدید
        # make_published, make_draft, make_archived, ensure_primary_image, duplicate_products,
        "check_effective_price",
    )

    list_per_page = 50
    list_select_related = ("category", "brand_fk")
    # prepopulated_fields = {"slug": ("name",)}

    fieldsets = (
        (None, {"fields": ("name", "slug", "category", "additional_categories", "brand_fk", "status", "is_active")}),
        (_("قیمت"), {"fields": ("price", "compare_at_price", "sale_active", "sale_percent", "sale_amount", "sale_starts_at",
                                "sale_ends_at", "effective_price_admin")}),
        (_("امتیاز کاربران"), {"fields": ("average_rating_display", "rating_count_display")}),
        (_("حمل‌ونقل"), {
            "fields": (
                "is_digital",
                "default_weight_grams",
                "default_length_cm", "default_width_cm", "default_height_cm","shipping_flat_fee",
            )
        }),
        (_("محتوا"), {"fields": ("short_description", "description")}),
        (_("SEO"), {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
        (_("زمان"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


     # ✅ نمایش میانگین امتیاز
    @admin.display(description="میانگین امتیاز کاربران")
    def average_rating_display(self, obj):
        avg = obj.average_rating
        if avg == 0:
            return "بدون امتیاز"
        avg_str = f"{avg:.1f}"  # قالب‌بندی عدد
        return format_html('<span style="color:#f5c518;">⭐</span> {}', avg_str)

    # ✅ نمایش تعداد رأی‌ها
    @admin.display(description="تعداد رأی‌ها")
    def rating_count_display(self, obj):
        count = obj.rating_count
        if count == 0:
            return "-"
        return format_html('<span style="color:#555;">{} رأی</span>', count)



    @admin.display(description=_("گروه سایز"))
    def effective_size_group(self, obj: Product):
        sg = obj.get_size_group()
        return f"{sg.name} [{sg.code}]" if sg else "—"

    @admin.display(description=_("قیمت مؤثر (بدون کوپن)"))
    def effective_price_admin(self, obj: Product):
        try:
            from products.services.pricing_adapter import price_single_product  # ← lazy
            res = price_single_product(obj, qty=1, coupons=[], channel="web")
            from django.contrib.humanize.templatetags.humanize import intcomma
            from django.utils.html import format_html
            return format_html("{} {}", intcomma(int(res.total)), "تومان")
        except Exception:
            return "—"

    @admin.action(description=_("چک سریع قیمت مؤثر (بدون کوپن)"))
    def check_effective_price(self, request, queryset):
        ok = errs = 0
        from products.services.pricing_adapter import price_single_product  # ← lazy
        for p in queryset:
            try:
                price_single_product(p, 1, coupons=[], channel="web")
                ok += 1
            except Exception:
                errs += 1
        if ok:
            from django.contrib import messages
            from django.utils.translation import gettext_lazy as _
            messages.success(request, _("%d محصول با موفقیت محاسبه شد.") % ok)
        if errs:
            messages.warning(request, _("%d محصول با خطا مواجه شد.") % errs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        pv = ProductVariant.objects.filter(product_id=OuterRef("pk"))

        # اگر فقط واریانت‌های فعال/قابل فروش حساب شوند:
        pv_active = pv.filter(is_active=True)

        stock_sq = pv_active.values("product_id") \
            .annotate(s=Coalesce(Sum("stock"), 0)) \
            .values("s")

        count_sq = pv_active.values("product_id") \
            .annotate(c=Count("id")) \
            .values("c")

        return qs.annotate(
            _stock_total=Coalesce(Subquery(stock_sq, output_field=IntegerField()), 0),
            _variant_count=Coalesce(Subquery(count_sq, output_field=IntegerField()), 0),
        )

    @admin.display(ordering="_variant_count", description="تعداد واریانت")
    def variant_count_col(self, obj):
        return obj._variant_count

    @admin.display(ordering="_stock_total", description="موجودی کل")
    def stock_total_col(self, obj):
        return obj._stock_total


    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        cat = request.GET.get("category")
        if cat:
            initial["category"] = cat
        return initial

    # products/admin.py (داخل کلاس ProductAdmin.changeform_view)
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        resp = super().changeform_view(request, object_id, form_url, extra_context=extra_context)
        try:
            resp.render()
            if object_id:
                try:
                    quick_url = reverse("admin:promos_quick_product")
                except Exception:
                    quick_url = None  # اگر URL ثبت نشده بود، دکمه را تزریق نکنیم

                if quick_url:
                    marker = "</body>"
                    inject = f"""
    <script>
    (function(){{
      var btn = document.createElement('a');
      btn.textContent = 'ایجاد کمپین تخفیف برای این کالا';
      btn.className = 'button';
      btn.style.marginRight = '8px';
      btn.onclick = function(e){{
        e.preventDefault();
        var percent = prompt('درصد تخفیف؟', '10');
        if(percent===null) return;
        var days = prompt('تا چند روز؟', '7');
        if(days===null) return;
        var url = '{quick_url}?product_id={object_id}&percent=' + encodeURIComponent(percent) + '&days=' + encodeURIComponent(days);
        window.location.href = url;
      }};
      var h1 = document.querySelector('#content h1');
      if(h1) h1.appendChild(btn);
    }})();
    </script>"""
                    resp.content = resp.content.replace(marker.encode(), (inject + marker).encode())
        except Exception:
            pass
        return resp

    class Media:
        js = (
            "admin/js/jquery.init.js",
            "products/js/pav-boot.js",
            "products/js/pav-inline-2.js",
            "products/js/product_dynamic_attrs.js",
        )

    def get_urls(self):
        urls = super().get_urls()
        my = [
            path(
                "attribute-choices/",
                self.admin_site.admin_view(self.attribute_choices_view),
                name="products_attribute_choices",
            ),
        ]
        return my + urls

    def attribute_choices_view(self, request):
        attr_id = request.GET.get("attr")
        if not attr_id:
            return JsonResponse({"data": [], "kind": None})
        try:
            attr = Attribute.objects.only("kind").get(pk=attr_id)
        except Attribute.DoesNotExist:
            return JsonResponse({"data": [], "kind": None})
        data = list(
            AttributeChoice.objects
            .filter(attribute_id=attr_id)
            .order_by("position", "id")
            .values("id", "label")
        )
        return JsonResponse({"data": data, "kind": attr.kind})

    @admin.display(ordering="_variant_count", description=_("تعداد واریانت"))
    def variant_count(self, obj: Product):
        return getattr(obj, "_variant_count", 0)

    @admin.display(ordering="_stock_total", description=_("موجودی کل"))
    def stock_total(self, obj: Product):
        return getattr(obj, "_stock_total", 0)

    @admin.display(description=_("کاور"))
    def thumb(self, obj: Product):
        img = obj.cover_image
        if img and img.image:
            try:
                return format_html(
                    '<img src="{}" style="height:48px;border-radius:6px;object-fit:cover;"/>',
                    img.image.url
                )
            except Exception:
                return "—"
        return "—"



@admin.register(ProductImage)
class ProductImageAdmin(JalaliAdminMixin):
    list_display = ("thumb", "product", "color", "is_primary", "position", "updated_at")
    list_filter = ("is_primary", "color")
    search_fields = ("product__name", "alt")
    autocomplete_fields = ("product", "color")
    list_editable = ("is_primary", "position")
    ordering = ("product", "position", "id")
    list_select_related = ("product", "color")

    @admin.display(description=_("پیش‌نمایش"))
    def thumb(self, obj: ProductImage):
        if obj.image:
            try:
                return format_html('<img src="{}" style="height:44px;border-radius:6px;object-fit:cover;"/>',
                                   obj.image.url)
            except Exception:
                return "—"
        return "—"




# =============== BRAND Admin ===============
@admin.register(Brand)
class BrandAdmin(JalaliAdminMixin):
    list_display = ("logo_thumb", "name", "is_active", "position", "updated_at")
    list_editable = ("is_active", "position")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("is_active",)
    ordering = ("position", "name")
    fields = ("name", "slug", "logo", "description", "is_active", "position", "meta_title", "meta_description")

    @admin.display(description=_("لوگو"))
    def logo_thumb(self, obj):
        if obj.logo:
            try:
                return format_html('<img src="{}" style="height:28px;border-radius:6px;"/>', obj.logo.url)
            except Exception:
                return "—"
        return "—"

# =============== Service Admin ===============
class ServicePriceInline(admin.TabularInline):
    model = ServicePrice
    extra = 0
    fields = ("price_type", "amount", "item_price_min", "item_price_max", "is_active")
    ordering = ("price_type", "item_price_min")

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "exclusive_group", "is_active")
    list_filter = ("kind", "exclusive_group", "is_active")
    search_fields = ("name", "code")
    inlines = [ServicePriceInline]

@admin.register(CategoryService)
class CategoryServiceAdmin(admin.ModelAdmin):
    list_display = ("category", "service", "is_default_on")
    list_filter = ("service__kind", "is_default_on")
    autocomplete_fields = ("category", "service")

@admin.register(ProductService)
class ProductServiceAdmin(admin.ModelAdmin):
    list_display = ("product", "service", "is_default_on")
    list_filter = ("service__kind", "is_default_on")
    autocomplete_fields = ("product", "service")