# products/models.py
from typing import Optional
from django.db import models
from django.db.models import Q, F
from django.utils.text import slugify
from django.urls import reverse
from django.core.validators import MinValueValidator, RegexValidator
from colorfield.fields import ColorField
from django import forms
from mptt.models import MPTTModel, TreeForeignKey
from mptt.managers import TreeManager
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType
from Core.models import Rating


# ---------- 1) گروه سرویس ها بیمه / نصب /گارانتی  ----------

class Service(models.Model):
    """
    یک «خدمت افزوده» مثل: نصب در محل، راه‌اندازی نرم‌افزار، بیمه/گارانتی افزوده.
    """
    KIND_CHOICES = (
        ("install", "نصب و راه‌اندازی"),
        ("warranty", "گارانتی/بیمه افزوده"),
        ("custom", "سفارشی"),
    )
    code = models.SlugField(max_length=80, unique=True, verbose_name="کد")
    name = models.CharField(max_length=160, verbose_name="عنوان")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="install", verbose_name="نوع")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    # گروه انحصاری (اختیاری): مثلا فقط یکی از «پلن‌های بیمه» قابل انتخاب باشد
    exclusive_group = models.CharField(max_length=60, blank=True, verbose_name="گروه انحصاری")

    # محدودیت‌ها
    per_item = models.BooleanField(default=True, verbose_name="به ازای هر آیتم؟ (qty مبنا)")
    max_qty = models.PositiveIntegerField(null=True, blank=True, verbose_name="حداکثر تعداد قابل انتخاب")

    def __str__(self):
        return self.name


class ServicePrice(models.Model):
    """
    قیمت‌دهی منعطف برای یک سرویس:
    - fixed: مبلغ ثابت
    - percent_of_item: درصدی از قیمت آیتم
    - per_unit_fixed: مبلغ ثابت * تعداد
    - tiered_by_item_price: پلکانی بر اساس قیمت آیتم
    """
    PRICE_TYPES = (
        ("fixed", "مبلغ ثابت"),
        ("percent_of_item", "درصدی از قیمت آیتم"),
        ("per_unit_fixed", "مبلغ ثابت به ازای هر واحد"),
        ("tiered_by_item_price", "پلکانی بر اساس قیمت آیتم"),
    )
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="prices", verbose_name="سرویس")
    price_type = models.CharField(max_length=40, choices=PRICE_TYPES, default="fixed", verbose_name="نوع قیمت")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)],
                                 verbose_name="مبلغ/درصد")
    # برای پلکانی (اختیاری)
    item_price_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    item_price_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "قیمت سرویس"
        verbose_name_plural = "قیمت‌های سرویس"
        indexes = [models.Index(fields=["service", "is_active"])]

    def __str__(self):
        return f"{self.service} – {self.get_price_type_display()} : {self.amount}"


class CategoryService(models.Model):
    """
    وصل‌کردن یک سرویس به دسته‌ها (برای ارث‌بری به محصولات آن کتگوری).
    """
    category = models.ForeignKey("products.Category", on_delete=models.CASCADE, related_name="category_services")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="category_links")
    is_default_on = models.BooleanField(default=False, verbose_name="پیشنهاد پیش‌فرض روشن؟")

    class Meta:
        unique_together = (("category", "service"),)


class ProductService(models.Model):
    """
    وصل‌کردن مستقیم سرویس به یک محصول (برای override/افزودن خاص).
    """
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="product_services")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="product_links")
    is_default_on = models.BooleanField(default=False)

    class Meta:
        unique_together = (("product", "service"),)

# ---------- 1) گروه سایز و خود سایز ----------
class SizeGroup(models.Model):
    code  = models.SlugField(max_length=50, unique=True)   # مثلا: apparel_alpha
    name  = models.CharField(max_length=100)               # مثلا: لباس (حروفی)
    note  = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name

class Size(models.Model):
    group = models.ForeignKey(SizeGroup, on_delete=models.CASCADE, related_name="sizes")
    code  = models.CharField(max_length=30)     # کلید داخلی: S, M, 42, 29x30 …
    label = models.CharField(max_length=30)     # نمایش به کاربر: S, M, EU 42, 29/30
    rank  = models.PositiveIntegerField(default=0)  # برای sort صحیح

    class Meta:
        unique_together = (("group", "code"),)
        ordering = ["group", "rank", "code"]

    def __str__(self):
        return f"{self.label} ({self.group.code})"

# =========================
# Category (MPTT)
# =========================
class CategoryQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def ordered(self):
        # ترتیب طبیعی درخت + سورت هم‌سطح‌ها با position سپس name
        return self.order_by("tree_id", "lft", "position", "id")


class CategoryManager(TreeManager.from_queryset(CategoryQuerySet)):
    pass


class Category(MPTTModel):
    name = models.CharField(max_length=150, verbose_name="نام")
    slug = models.SlugField(max_length=160, blank=True, verbose_name="اسلاگ")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    position = models.PositiveIntegerField(default=0, verbose_name="موقعیت")
    image = models.ImageField(upload_to="categories/", null=True, blank=True, verbose_name="تصویر")
    meta_title = models.CharField(max_length=70, blank=True, verbose_name="عنوان متا")
    meta_description = models.CharField(max_length=160, blank=True, verbose_name="توضیحات متا")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")
    spec_slots = models.JSONField(default=list, blank=True, help_text=(
        "لیست آیتم‌ها به ترتیب نمایش. مثال:"
        " ["
        ' {"key":"brand","label":"برند"},'
        ' {"key":"attr:os","label":"سیستم‌عامل"},'
        ' {"key":"attr:model_name","label":"مدل"},'
        ' {"key":"attr:storage","label":"ظرفیت حافظه"},'
        ' {"key":"attr:display_size","label":"اندازه صفحه‌نمایش"},'
        ' {"key":"attr:battery_capacity","label":"ظرفیت باتری"}'
        " ]"
    ))

    @cached_property
    def resolved_spec_slots(self):
        # نزدیک‌ترین spec_slots غیرخالی در زنجیرهٔ اجداد
        for c in reversed(list(self.get_ancestors(include_self=True))):
            if c.spec_slots:
                return c.spec_slots
        return []

    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
        db_index=True,
        verbose_name="والد",
    )
    size_group = models.ForeignKey(
        "products.SizeGroup",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="categories",
        verbose_name="گروه سایز",
        help_text="اگر تنظیم شود، محصولات این دسته به‌طور پیش‌فرض از این گروه سایز استفاده می‌کنند.",
    )
    objects: CategoryManager = CategoryManager()

    class MPTTMeta:
        order_insertion_by = ("position", "name")

    @property
    def slug_path(self) -> str:
        return "/".join(self.get_ancestors(include_self=True).values_list("slug", flat=True))

    def get_absolute_url(self):
        # توجه: حتماً با namespace اپ
        return reverse("products:category", kwargs={"path": self.slug_path})

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        constraints = [
            models.UniqueConstraint(fields=["parent", "slug"], name="uniq_sibling_slug"),
            models.CheckConstraint(check=~Q(pk=F("parent_id")), name="no_self_parent"),
        ]
        indexes = [
            models.Index(fields=["parent", "position"]),
            models.Index(fields=["slug", "parent"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["size_group"]),
        ]

        # 🔹 نزدیک‌ترین گروه‌سایز معتبر در شاخه درخت (اگر روی خود دسته نبود از والد می‌گیرد)
    @cached_property
    def resolved_size_group(self):
        # نزدیک‌ترین اجداد از خود دسته به سمت بالا
        for cat in reversed(list(self.get_ancestors(include_self=True))):
            if cat.size_group_id:
                return cat.size_group
        return None

    def save(self, *args, **kwargs):
        MAX = self._meta.get_field("slug").max_length
        base = slugify(self.slug or self.name, allow_unicode=True) or "cat"
        base = base[: MAX - 5]
        slug = base
        i = 2
        while self.__class__.objects.filter(parent=self.parent, slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{i}"
            i += 1
        self.slug = slug
        super().save(*args, **kwargs)

    # @property
    # def slug_path(self) -> str:
    #     return "/".join(self.get_ancestors(include_self=True).values_list("slug", flat=True))
    #
    # def get_absolute_url(self):
    #     return reverse("category", kwargs={"path": self.slug_path})

    # ویژگی‌های مؤثر این کتگوری با ارث‌بری از والدین (برای UI/فیلتر)
    def effective_category_attributes(self):
        from django.db.models import Prefetch
        cats = self.get_ancestors(include_self=True)
        return (
            CategoryAttribute.objects
            .filter(category__in=cats)
            .select_related("attribute")
            .prefetch_related(
                Prefetch(
                    "attribute__choices",
                    queryset=AttributeChoice.objects.order_by("position", "id"),
                )
            )
            .order_by("position", "id")
        )

    def __str__(self):
        return self.name


# =========================
# Color (swatches)
# =========================
class Color(models.Model):
    name = models.CharField(max_length=50, verbose_name="نام رنگ")
    slug = models.SlugField(max_length=60, unique=True, blank=True, verbose_name="اسلاگ")
    hex_code = ColorField(
        default="#6B7280",
        format="hex",
        samples=["#000000", "#FFFFFF", "#FF0000", "#00FF00", "#0000FF", "#F59E0B", "#10B981", "#06B6D4", "#6366F1"],
        verbose_name="کد رنگ",
    )
    swatch_image = models.ImageField(upload_to="colors/", null=True, blank=True, verbose_name="تصویر سواچ")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")

    class Meta:
        verbose_name = "رنگ"
        verbose_name_plural = "رنگ‌ها"
        ordering = ("name",)
        indexes = [models.Index(fields=["is_active"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.hex_code})"


# =========================
# Helpers
# =========================
def product_image_upload_to(instance: "ProductImage", filename: str) -> str:
    pid = instance.product_id or "unknown"
    cid = instance.color_id or "common"
    return f"products/{pid}/images/{cid}/{filename}"


# =========================
# Brand
# =========================
class Brand(models.Model):
    name = models.CharField(max_length=120, unique=True, verbose_name="نام برند")
    slug = models.SlugField(max_length=140, unique=True, blank=True, verbose_name="اسلاگ")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    logo = models.ImageField(upload_to="brands/", null=True, blank=True, verbose_name="لوگو")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    position = models.PositiveIntegerField(default=0, verbose_name="اولویت")
    meta_title = models.CharField(max_length=70, blank=True, verbose_name="عنوان متا")
    meta_description = models.CharField(max_length=160, blank=True, verbose_name="توضیحات متا")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="به‌روزرسانی")



    class Meta:
        verbose_name = "برند"
        verbose_name_plural = "برندها"
        ordering = ("position", "name")
        indexes = [models.Index(fields=["is_active"]), models.Index(fields=["position"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or "brand"
            self.slug = base[: 135]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# =========================
# Product
# =========================
class Product(models.Model):
    STATUS_CHOICES = (
        ("draft", "پیش‌نویس"),
        ("pub", "منتشر شده"),
        ("arch", "آرشیو"),
    )

    name = models.CharField(max_length=220, verbose_name="نام محصول")
    slug = models.SlugField(max_length=230, unique=True, blank=True, verbose_name="اسلاگ")

    # دسته اصلی (برای قوانین Spec)
    category = models.ForeignKey(
        "products.Category",
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="دسته‌بندی",
    )
    # دسته‌های اضافی (برای نمایش در چند مسیر)
    additional_categories = models.ManyToManyField(
        "products.Category",
        blank=True,
        related_name="products_extra",
        verbose_name="دسته‌های دیگر",
    )

    brand_fk = models.ForeignKey(
        "products.Brand",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="برند",
    )

    short_description = models.CharField(
        max_length=280,
        blank=True,
        verbose_name="توضیح کوتاه",
    )
    description = models.TextField(blank=True, verbose_name="توضیحات")

    # --- اطلاعات حمل‌ونقل (سطح محصول) ---
    is_digital = models.BooleanField(
        default=False,
        verbose_name="محصول دیجیتال / بدون ارسال فیزیکی",
        help_text="برای دوره آنلاین، فایل دانلودی و خدماتی که ارسال پستی ندارند این گزینه را فعال کن.",
    )

    default_weight_grams = models.PositiveIntegerField(
        default=0,
        verbose_name="وزن پیش‌فرض (گرم)",
        help_text="اگر واریانت‌ها وزن جدا ندارند، وزن ارسال این محصول را اینجا بر حسب گرم وارد کن.",
    )

    default_length_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="طول بسته (سانتی‌متر)",
        help_text="برای محاسبه وزن حجمی؛ اختیاری.",
    )
    default_width_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="عرض بسته (سانتی‌متر)",
        help_text="برای محاسبه وزن حجمی؛ اختیاری.",
    )
    default_height_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="ارتفاع بسته (سانتی‌متر)",
        help_text="برای محاسبه وزن حجمی؛ اختیاری.",
    )

    # --- قیمت پایه ---
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="قیمت",
    )
    compare_at_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="قیمت قبلی",
    )

    shipping_flat_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="هزینه بسته‌بندی و ارسال (تومان)",
        help_text="برای هر عدد از این کالا، این مقدار به هزینه ارسال اضافه می‌شود.",
    )
    status = models.CharField(
        max_length=5,
        choices=STATUS_CHOICES,
        default="draft",
        verbose_name="وضعیت",
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    meta_title = models.CharField(
        max_length=70,
        blank=True,
        verbose_name="عنوان متا",
    )
    meta_description = models.CharField(
        max_length=160,
        blank=True,
        verbose_name="توضیحات متا",
    )

    # اختیاری: ذخیرهٔ خام؛ موتور اصلی مشخصات در جداول Attribute* است
    attributes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="ویژگی‌ها",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ به‌روزرسانی",
    )

    # === product-level sale fields (اختیاری: admin-only) ===
    sale_active = models.BooleanField(
        default=False,
        verbose_name="تخفیف محصول فعال",
    )
    sale_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="درصد تخفیف (مثلاً 10 برای 10%)",
        help_text="اگر پر شد، درصدی از قیمت پایه کم می‌شود.",
    )
    sale_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="مبلغ ثابت تخفیف (تومان)",
        help_text="اگر پر شد، مبلغ ثابت از قیمت پایه کم می‌شود.",
    )
    sale_starts_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="شروع تخفیف",
    )
    sale_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="پایان تخفیف",
    )

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["status"]),
            models.Index(fields=["brand_fk"]),
        ]

    # ==== Helpers ====
    def get_default_weight_grams(self) -> int:
        return int(self.default_weight_grams or 0)

    @property
    def is_shippable(self) -> bool:
        """
        محصولی که دیجیتال نیست و ارسال فیزیکی دارد.
        """
        return not self.is_digital

    def effective_services(self):
        """
        سرویس‌های موثر این محصول = سرویس‌های سطح محصول + سرویس‌های کتگوری‌های اجدادی.
        """
        cats = self.category.get_ancestors(include_self=True)
        cat_services = (
            CategoryService.objects
            .filter(category__in=cats)
            .select_related("service")
        )
        prd_services = (
            ProductService.objects
            .filter(product=self)
            .select_related("service")
        )

        seen = set()
        result = []
        for link in list(prd_services) + list(cat_services):
            s = link.service
            if not s.is_active or s.id in seen:
                continue
            seen.add(s.id)
            result.append(
                {"service": s, "is_default_on": getattr(link, "is_default_on", False)}
            )
        return result

    @property
    def effective_price(self) -> Decimal:
        """
        قیمت مؤثر بدون درنظرگرفتن کوپن‌های سشن (برای ادمین/استفاده آفلاین).
        """
        from products.services.pricing_adapter import price_single_product
        res = price_single_product(self, qty=1, coupons=[], channel="web")
        return res.total

    def save(self, *args, **kwargs):
        MAX = self._meta.get_field("slug").max_length
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or "product"
            base = base[: MAX - 5]
            slug = base
            i = 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("products:product_detail", kwargs={"slug": self.slug})

    @property
    def cover_image(self) -> Optional["ProductImage"]:
        return (
            self.images.filter(is_primary=True).first()
            or self.images.order_by("position", "id").first()
        )

    def get_size_group(self):
        cat = getattr(self, "category", None)
        if not cat:
            return None
        if hasattr(cat, "get_size_group"):
            return cat.get_size_group()
        return getattr(cat, "size_group", None)

    @property
    def colors(self):
        ids = set(self.variants.values_list("color_id", flat=True))
        ids.update(
            self.images
            .exclude(color__isnull=True)
            .values_list("color_id", flat=True)
        )
        return Color.objects.filter(id__in=ids, is_active=True)

    def __str__(self):
        return self.name

    @property
    def average_rating(self):
        ctype = ContentType.objects.get_for_model(self)
        avg = (
            Rating.objects
            .filter(content_type=ctype, object_id=self.id)
            .aggregate(models.Avg("score"))["score__avg"]
        )
        return round(avg or 0, 1)

    @property
    def rating_count(self):
        ctype = ContentType.objects.get_for_model(self)
        return Rating.objects.filter(content_type=ctype, object_id=self.id).count()



# =========================
# Product Variant
# =========================
SKU_VALIDATOR = RegexValidator(
    regex=r"^[A-Z0-9\-_\.]{3,32}$",
    message="SKU باید 3 تا 32 کاراکتر، فقط حروف بزرگ، اعداد و - _ . باشد.",
)


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants", verbose_name="محصول")
    color   = models.ForeignKey(Color, on_delete=models.PROTECT, related_name="variants", verbose_name="رنگ")
    size    = models.ForeignKey(
        "products.Size",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="variants",
        verbose_name="سایز",
    )

    sku     = models.CharField(max_length=64, unique=True, validators=[SKU_VALIDATOR], verbose_name="SKU")
    barcode = models.CharField(max_length=64, blank=True, verbose_name="بارکد")

    price   = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="قیمت واریانت",
    )
    stock   = models.PositiveIntegerField(default=0, verbose_name="موجودی")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    # --- Shipping info (سطح واریانت) ---
    weight_grams = models.PositiveIntegerField(
        default=0,
        verbose_name="وزن این واریانت (گرم)",
        help_text="اگر خالی بماند، از وزن پیش‌فرض محصول استفاده می‌شود.",
    )
    length_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="طول (سانتی‌متر)",
    )
    width_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="عرض (سانتی‌متر)",
    )
    height_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="ارتفاع (سانتی‌متر)",
    )

    # === sale fields (variant-level) ===
    sale_active_variant = models.BooleanField(
        default=False,
        verbose_name="تخفیف روی این واریانت فعال",
    )
    sale_percent_variant = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="درصد تخفیف واریانت",
        help_text="مثلاً 10 برای 10% (اختیاری)",
    )
    sale_amount_variant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="مبلغ ثابت تخفیف واریانت",
        help_text="مثلاً 10000 (تومان) (اختیاری)",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")

    class Meta:
        verbose_name = "واریانت"
        verbose_name_plural = "واریانت‌ها"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "color", "size"],
                condition=Q(size__isnull=False),
                name="uniq_prod_color_size_when_size_not_null",
            ),
            models.UniqueConstraint(
                fields=["product", "color"],
                condition=Q(size__isnull=True),
                name="uniq_prod_color_when_size_null",
            ),
        ]
        indexes = [
            models.Index(fields=["product", "color", "size"]),
            models.Index(fields=["is_active"]),
        ]
    unique_together = (("product", "sku"),)

    # ==== Pricing & stock ====
    def get_price(self):
        return self.price if self.price is not None else self.product.price

    @property
    def in_stock(self) -> bool:
        return self.is_active and self.stock > 0

    # ==== Helpers for shipping ====
    @property
    def shipping_weight_grams(self) -> int:
        if self.weight_grams:
            return int(self.weight_grams)
        return getattr(self.product, "get_default_weight_grams", lambda: 0)()

    @property
    def shipping_dimensions_cm(self):
        length = self.length_cm or self.product.default_length_cm
        width  = self.width_cm or self.product.default_width_cm
        height = self.height_cm or self.product.default_height_cm
        return (length, width, height)

    # ==== Validation ====
    def clean(self):
        super().clean()
        sg = self.product.get_size_group() if self.product_id else None
        if sg and self.size_id and self.size.group_id != sg.id:
            raise ValidationError({"size": "سایز انتخابی با گروه سایز محصول/دسته سازگار نیست."})

    # ==== Misc ====
    def __str__(self):
        size_label = self.size.label if self.size_id else ""
        return f"{self.product.name} — {self.color.name}" + (f" / {size_label}" if size_label else "")

    def save(self, *args, **kwargs):
        if not self.sku:
            size_token = (self.size.code if self.size_id else "OS")[:4]
            parts = [
                (self.product.slug[:8] if self.product_id else "PROD").upper(),
                (self.color.slug[:3] if self.color_id else "N/A").upper(),
                size_token.upper(),
            ]
            base = "-".join(parts).replace("--", "-")
            sku = base
            i = 1
            Model = self.__class__
            while Model.objects.filter(sku=sku).exclude(pk=self.pk).exists():
                i += 1
                sku = f"{base}-{i:02d}"
            self.sku = sku
        super().save(*args, **kwargs)

# =========================
# Product Image
# =========================
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images", verbose_name="محصول")
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True, related_name="images", verbose_name="رنگ")
    image = models.ImageField(upload_to=product_image_upload_to, verbose_name="تصویر")
    alt = models.CharField(max_length=120, blank=True, verbose_name="متن جایگزین")
    is_primary = models.BooleanField(default=False, verbose_name="تصویر اصلی")
    position = models.PositiveIntegerField(default=0, verbose_name="اولویت نمایش")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")

    class Meta:
        verbose_name = "تصویر محصول"
        verbose_name_plural = "گالری تصاویر"
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(fields=["product"], condition=Q(is_primary=True), name="uniq_primary_image_per_product"),
            models.UniqueConstraint(fields=["product", "position"], name="uniq_product_image_position"),
        ]
        indexes = [models.Index(fields=["product", "color"])]

    def save(self, *args, **kwargs):
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name}" + (f" ({self.color.name})" if self.color_id else "")


# =========================
# Attribute Engine (Specs)
# =========================
class Attribute(models.Model):
    KIND_CHOICES = (
        ("text", "متن"),
        ("int", "عدد صحیح"),
        ("decimal", "عدد اعشاری"),
        ("bool", "بلی/خیر"),
        ("choice", "گزینشی (تکی)"),
        ("multi", "گزینشی (چندتایی)"),
    )
    name       = models.CharField(max_length=120, verbose_name="نام ویژگی")
    code       = models.SlugField(max_length=120, unique=True, verbose_name="کُد ویژگی")
    kind       = models.CharField(max_length=10, choices=KIND_CHOICES, default="text", verbose_name="نوع")
    unit       = models.CharField(max_length=20, blank=True, verbose_name="واحد (مثلاً g, cm)")
    is_variant = models.BooleanField(default=False, verbose_name="تأثیر روی واریانت؟")
    position   = models.PositiveIntegerField(default=0, verbose_name="اولویت نمایش")
    is_active  = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "ویژگی"
        verbose_name_plural = "ویژگی‌ها"
        ordering = ("position", "id")
        indexes = [models.Index(fields=["is_active"]), models.Index(fields=["position"])]

    def __str__(self):
        return f"{self.name} [{self.code}]"


class AttributeChoice(models.Model):
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name="choices", verbose_name="ویژگی")
    value     = models.SlugField(max_length=120, verbose_name="مقدار (کُد)")
    label     = models.CharField(max_length=120, verbose_name="برچسب نمایشی")
    position  = models.PositiveIntegerField(default=0, verbose_name="اولویت")

    class Meta:
        verbose_name = "گزینهٔ ویژگی"
        verbose_name_plural = "گزینه‌های ویژگی"
        ordering = ("attribute", "position", "id")
        constraints = [
            models.UniqueConstraint(fields=["attribute", "value"], name="uniq_attr_value"),
        ]

    def __str__(self):
        return f"{self.attribute.name}: {self.label}"


class CategoryAttribute(models.Model):
    category  = models.ForeignKey("products.Category", on_delete=models.CASCADE, related_name="category_attributes", verbose_name="دسته")
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name="category_attributes", verbose_name="ویژگی")
    is_required = models.BooleanField(default=False, verbose_name="الزامی؟")
    position    = models.PositiveIntegerField(default=0, verbose_name="اولویت")

    class Meta:
        verbose_name = "ویژگیِ دسته"
        verbose_name_plural = "ویژگی‌های دسته"
        ordering = ("category", "position", "id")
        constraints = [
            models.UniqueConstraint(fields=["category", "attribute"], name="uniq_category_attribute"),
        ]

    def __str__(self):
        return f"{self.category} → {self.attribute}"


Category.add_to_class(
    "attributes",
    models.ManyToManyField(
        Attribute, through=CategoryAttribute, related_name="categories", blank=True, verbose_name="ویژگی‌ها"
    ),
)


class ProductAttributeValue(models.Model):
    product   = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="attr_values", verbose_name="محصول")
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name="values", verbose_name="ویژگی")

    # مقادیر ممکن (یکی از این‌ها باید استفاده شود بسته به kind)
    value_text    = models.CharField(max_length=500, blank=True, verbose_name="متن")
    value_int     = models.IntegerField(null=True, blank=True, verbose_name="عدد صحیح")
    value_decimal = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, verbose_name="عدد اعشاری")
    value_bool    = models.BooleanField(null=True, blank=True, verbose_name="بلی/خیر")

    value_choice  = models.ForeignKey(
        AttributeChoice, on_delete=models.PROTECT, null=True, blank=True,
        related_name="product_values_single", verbose_name="گزینه (تکی)"
    )
    values_multi  = models.ManyToManyField(
        AttributeChoice, blank=True, related_name="product_values_multi", verbose_name="گزینه‌ها (چندتایی)"
    )

    class Meta:
        verbose_name = "مقدار ویژگیِ محصول"
        verbose_name_plural = "مقادیر ویژگی‌های محصول"
        constraints = [
            models.UniqueConstraint(fields=["product", "attribute"], name="uniq_product_attribute"),
        ]
        indexes = [models.Index(fields=["product", "attribute"])]

    def __str__(self):
        return f"{self.product} / {self.attribute.name}"

    def clean(self):
        super().clean()
        kind = self.attribute.kind if self.attribute_id else None

        def any_set(*vals):
            return any(v not in (None, "", [], False) for v in vals)

        # اعتبارسنجی سازگار با نوع
        if kind == "text":
            if not self.value_text or any_set(self.value_int, self.value_decimal, self.value_bool, self.value_choice):
                raise forms.ValidationError("برای ویژگی متنی فقط «value_text» را پر کن.")
        elif kind == "int":
            if self.value_int is None or any_set(self.value_text, self.value_decimal, self.value_bool, self.value_choice):
                raise forms.ValidationError("برای ویژگی عدد صحیح فقط «value_int» را پر کن.")
        elif kind == "decimal":
            if self.value_decimal is None or any_set(self.value_text, self.value_int, self.value_bool, self.value_choice):
                raise forms.ValidationError("برای ویژگی اعشاری فقط «value_decimal» را پر کن.")
        elif kind == "bool":
            if self.value_bool is None or any_set(self.value_text, self.value_int, self.value_decimal, self.value_choice):
                raise forms.ValidationError("برای ویژگی بولی فقط «value_bool» را پر کن.")
        elif kind == "choice":
            if not self.value_choice_id or any_set(self.value_text, self.value_int, self.value_decimal, self.value_bool):
                raise forms.ValidationError("برای ویژگیِ گزینشی (تکی) باید «value_choice» را انتخاب کنی.")
            if self.value_choice and self.value_choice.attribute_id != self.attribute_id:
                raise forms.ValidationError("گزینهٔ انتخاب‌شده متعلق به همین ویژگی نیست.")
        elif kind == "multi":
            if self.value_choice_id or any_set(self.value_text, self.value_int, self.value_decimal, self.value_bool):
                raise forms.ValidationError("برای ویژگیِ چندگزینه‌ای فقط «values_multi» را استفاده کن.")
            if self.pk:
                invalid = self.values_multi.exclude(attribute_id=self.attribute_id).exists()
                if invalid:
                    raise forms.ValidationError("بعضی گزینه‌های چندتایی متعلق به این ویژگی نیستند")


