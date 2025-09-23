# products/admin.py
from django import forms
from django.contrib import admin, messages
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import path
from django.http import JsonResponse
from .models import (
    Category, Color, Brand, Product, ProductVariant, ProductImage,
    Attribute, AttributeChoice, CategoryAttribute, ProductAttributeValue
)
from mptt.admin import DraggableMPTTAdmin
from mptt.exceptions import InvalidMove


# =============== Helpers ===============
def _selected_category_id(request, obj=None):
    if obj and getattr(obj, "category_id", None):
        return obj.category_id
    return request.POST.get("category") or request.GET.get("category")


# =============== Inlines & Forms ===============

class ProductAttributeValueForm(forms.ModelForm):
    class Meta:
        model = ProductAttributeValue
        fields = ("attribute", "value_text", "value_int", "value_decimal", "value_bool",
                  "value_choice", "values_multi")


def __init__(self, *args, **kwargs):
    self.parent_obj = kwargs.pop("parent_obj", None)  # از اینلاین تزریق می‌شود
    super().__init__(*args, **kwargs)

    # فیلتر لیست Attribute بر اساس دسته‌ی محصول (به همراه والدها)
    if self.parent_obj and self.parent_obj.category_id:
        allowed_attr_ids = list(
            self.parent_obj.category.effective_category_attributes().values_list("attribute_id", flat=True)
        )
        self.fields["attribute"].queryset = Attribute.objects.filter(id__in=allowed_attr_ids).order_by("position", "id")

    # تعیین ویژگیِ انتخاب‌شده (از instance یا داده‌ی POST جاری)
    attr = None
    if self.instance and self.instance.pk:
        attr = self.instance.attribute
    else:
        # در فرم بایندشده، مقدار attribute در self.data هست (براساس prefix فرم)
        # مثال نام فیلد:  attr_values-0-attribute  یا productattributevalue_set-0-attribute
        for key in self.data:
            if key.endswith("-attribute") and key.startswith(self.prefix):
                try:
                    attr_id = int(self.data.get(key)) or None
                except (TypeError, ValueError):
                    attr_id = None
                if attr_id:
                    try:
                        attr = Attribute.objects.get(pk=attr_id)
                    except Attribute.DoesNotExist:
                        pass
                break

    # فیلتر کوئری‌ست گزینه‌ها
    if attr:
        qs = AttributeChoice.objects.filter(attribute=attr).order_by("position", "id")
    else:
        qs = AttributeChoice.objects.none()
    self.fields["value_choice"].queryset = qs
    self.fields["values_multi"].queryset = qs


class PAVInlineForm(forms.ModelForm):
    class Meta:
        model = ProductAttributeValue
        fields = ("attribute", "value_text", "value_int", "value_decimal",
                  "value_bool", "value_choice", "values_multi")

    def __init__(self, *args, **kwargs):
        parent: Product | None = kwargs.pop("parent_obj", None)
        super().__init__(*args, **kwargs)

        # محدود کردن لیست Attribute به کتگوری محصول
        if parent and parent.category_id:
            allowed = Attribute.objects.filter(
                categories__in=parent.category.get_ancestors(include_self=True)
            ).distinct().order_by("position", "id")
            self.fields["attribute"].queryset = allowed

        # پیش‌فرض: کوئریِ گزینه‌ها خالی باشد تا بعداً با AJAX پر شود
        self.fields["value_choice"].queryset = AttributeChoice.objects.none()
        self.fields["values_multi"].queryset = AttributeChoice.objects.none()

        # اگر داریم ویرایش می‌کنیم، گزینه‌های همان attribute را لود کن
        vc_initial = ""
        vm_initial_ids: list[str] = []

        if self.instance and self.instance.attribute_id:
            qs = AttributeChoice.objects.filter(
                attribute_id=self.instance.attribute_id
            ).order_by("position", "id")
            self.fields["value_choice"].queryset = qs
            self.fields["values_multi"].queryset = qs

            # مقدارهای ذخیره‌شده (برای انتخاب دوباره بعد از AJAX)
            if self.instance.value_choice_id:
                vc_initial = str(self.instance.value_choice_id)
                self.fields["value_choice"].initial = self.instance.value_choice_id  # سرور هم انتخاب کند
            vm_initial_ids = [str(i) for i in
                              self.instance.values_multi.values_list("id", flat=True)]
            if vm_initial_ids:
                self.fields["values_multi"].initial = [int(i) for i in vm_initial_ids]

        # اینها را به data-attributes هم بده تا JS اگر مجبور شد بعد از پاک/پر کردن، ست کند
        self.fields["value_choice"].widget.attrs["data-initial"] = vc_initial
        self.fields["values_multi"].widget.attrs["data-initial"] = ",".join(vm_initial_ids)

    def clean(self):
        cleaned = super().clean()
        attr = cleaned.get("attribute")
        if not attr:
            cleaned["DELETE"] = True
            return cleaned

        kind = attr.kind
        vt = cleaned.get("value_text")
        vi = cleaned.get("value_int")
        vd = cleaned.get("value_decimal")
        vb = cleaned.get("value_bool")
        vc = cleaned.get("value_choice")
        vm = list(cleaned.get("values_multi") or [])

        def any_set(*vals): return any(v not in (None, "", [], False) for v in vals)

        # اگر برای نوع فعلی هیچ ارزشی نداده، این ردیف را حذف کن تا خطا نگیری
        if kind == "text" and not any_set(vt): cleaned["DELETE"] = True; return cleaned
        if kind == "int" and vi is None:       cleaned["DELETE"] = True; return cleaned
        if kind == "decimal" and vd is None:   cleaned["DELETE"] = True; return cleaned
        if kind == "bool" and vb is None:      cleaned["DELETE"] = True; return cleaned
        if kind == "choice" and not vc and not vm:  cleaned["DELETE"] = True; return cleaned
        if kind == "multi" and not vm:              cleaned["DELETE"] = True; return cleaned

        # عادی‌سازی تضادها
        if kind == "choice":
            if not vc and vm:
                if len(vm) == 1:
                    cleaned["value_choice"] = vm[0]
                    cleaned["values_multi"] = []
                else:
                    raise forms.ValidationError("برای این ویژگی فقط یک گزینهٔ تکی مجاز است.")
            cleaned["value_text"] = ""
            cleaned["value_int"] = None
            cleaned["value_decimal"] = None
            cleaned["value_bool"] = None

        elif kind == "multi":
            cleaned["value_choice"] = None
            cleaned["value_text"] = ""
            cleaned["value_int"] = None
            cleaned["value_decimal"] = None
            cleaned["value_bool"] = None

        else:
            cleaned["value_choice"] = None
            cleaned["values_multi"] = []

        return cleaned


class ProductAttributeValueInline(admin.TabularInline):
    model = ProductAttributeValue
    form = PAVInlineForm
    extra = 0
    fields = ("attribute", "value_text", "value_int", "value_decimal",
              "value_bool", "value_choice", "values_multi")
    ordering = ("attribute", "id")

    # 👇 این بخش مهم است: parent_obj را به فرم بده
    def get_formset(self, request, obj=None, **kwargs):
        FS = super().get_formset(request, obj, **kwargs)
        parent = obj

        class _FS(FS):
            def _construct_form(self, i, **k):
                k["parent_obj"] = parent
                return super()._construct_form(i, **k)

        return _FS


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ("color", "size", "sku", "price", "stock", "is_active")
    autocomplete_fields = ("color",)
    classes = ("collapse",)


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
    extra = 0
    fields = ("value", "label", "position")
    ordering = ("position", "id")


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
        fields = ["name", "slug", "parent", "is_active", "position", "image", "meta_title", "meta_description"]

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
                obj.save();
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

    list_display = ("tree_actions", "indented_title", "slug", "is_active", "position", "parent")
    list_display_links = ("indented_title",)
    list_editable = ("is_active", "position")
    list_filter = ("is_active", RootFilter, LeafFilter)
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
class ColorAdmin(admin.ModelAdmin):
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


# =============== Product Admin ===============

class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") == "pub":
            if not cleaned.get("is_active", True):
                raise forms.ValidationError(_("محصول منتشرشده باید فعال باشد."))
            price = cleaned.get("price")
            if price is None or price < 0:
                raise forms.ValidationError(_("قیمت پایهٔ محصول نامعتبر است."))
        return cleaned


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    exclude = ("attributes",)
    form = ProductAdminForm
    inlines = [ProductVariantInline, ProductAttributeValueInline, ProductImageInline]
    list_display = (
        "thumb", "name", "category", "price", "status",
        "is_active", "variant_count", "stock_total", "created_at",
    )
    list_display_links = ("name", "thumb")
    list_editable = ("price", "status", "is_active")
    list_filter = ("status", "is_active", HasImagesFilter, HasVariantsFilter, CategoryRootFilter)
    search_fields = ("name", "slug", "brand_fk__name", "variants__sku")
    autocomplete_fields = ("category", "brand_fk")
    readonly_fields = ("created_at", "updated_at")
    actions = (make_published, make_draft, make_archived, ensure_primary_image, duplicate_products)
    list_per_page = 50
    list_select_related = ("category", "brand_fk")
    prepopulated_fields = {"slug": ("name",)}

    fieldsets = (
        (None, {"fields": ("name", "slug", "category", "additional_categories", "brand_fk", "status", "is_active")}),
        (_("قیمت"), {"fields": ("price", "compare_at_price")}),
        (_("محتوا"), {"fields": ("short_description", "description")}),
        (_("SEO"), {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
        (_("زمان"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related("category", "brand_fk")
            .prefetch_related("images")
            .annotate(
                _variant_count=Count("variants", distinct=True),
                _stock_total=Coalesce(Sum("variants__stock"), 0),
            )
        )

    # مقدار اولیهٔ category از روی ?category=... (برای add-view بدون سیو)
    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        cat = request.GET.get("category")
        if cat:
            initial["category"] = cat
        return initial

    class Media:
        js = (
            "admin/js/jquery.init.js",
            "products/js/pav-boot.js",       # آدرس endpoint را روی window ست می‌کند (اختیاری اما خوب است)
            "products/js/pav-inline.js",     # منطق AJAX و نگه‌داشتن انتخاب‌ها
            "products/js/product_dynamic_attrs.js",  # اگر می‌خواهی با تغییر دسته، صفحه رفرش شود
        )

    # 2) endpoint: برگرداندن لیست گزینه‌ها + نوع ویژگی
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

    @admin.display(description=_("کاور"))
    def thumb(self, obj: Product):
        img = obj.cover_image
        if img and img.image:
            try:
                return format_html('<img src="{}" style="height:48px;border-radius:6px;object-fit:cover;"/>',
                                   img.image.url)
            except Exception:
                return "—"
        return "—"

    @admin.display(ordering="_variant_count", description=_("تعداد واریانت"))
    def variant_count(self, obj: Product):
        return getattr(obj, "_variant_count", 0)

    @admin.display(ordering="_stock_total", description=_("موجودی کل"))
    def stock_total(self, obj: Product):
        return getattr(obj, "_stock_total", 0)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "color", "size", "sku", "price", "stock", "is_active", "updated_at")
    list_filter = ("is_active", "color")
    search_fields = ("product__name", "sku", "barcode")
    autocomplete_fields = ("product", "color")
    list_editable = ("price", "stock", "is_active")
    ordering = ("-updated_at",)
    list_select_related = ("product", "color")


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
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


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
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
