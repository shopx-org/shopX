# core/models.py
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django_jalali.db import models as jmodels
from ckeditor.fields import RichTextField
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFit, Adjust, Transpose, ResizeToFill

class LikeDislike(models.Model):
    LIKE = 1
    DISLIKE = -1
    VALUE_CHOICES = (
        (LIKE, "Like"),
        (DISLIKE, "Dislike"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="votes",
        verbose_name="کاربر"
    )
    value = models.SmallIntegerField(choices=VALUE_CHOICES)

    # 🔹 Generic relation برای وصل‌شدن به هر مدل (مثل Comment، Product، Post و ...)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "content_type", "object_id")  # هر کاربر فقط یک رأی برای هر شیء
        verbose_name = "رأی"
        verbose_name_plural = "رأی‌ها"

    def __str__(self):
        return f"{self.user} -> {self.content_object} ({self.get_value_display()})"


class Comment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="کاربر"
    )

    # Generic Foreign Key برای اتصال به مدل‌های مختلف
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name="نوع محتوا")
    object_id = models.PositiveIntegerField(verbose_name="شناسه شیء")
    content_object = GenericForeignKey('content_type', 'object_id')

    parent = models.ForeignKey(
        'self',
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='replies',
        verbose_name="پاسخ به"
    )

    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP")
    is_approved = models.BooleanField(default=False, verbose_name="تایید شده؟")


    text = models.TextField(verbose_name="متن نظر")
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = jmodels.jDateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")
    # is_active = models.BooleanField(default=True, verbose_name="فعال است؟")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "نظر"
        verbose_name_plural = "نظرات"

    def __str__(self):
        return f"نظر {self.user.get_full_name() or self.user.phone} برای {self.content_object}"

    def short_text(self):
        return (self.text[:50] + '...') if len(self.text) > 50 else self.text

    @property
    def is_reply(self):
        return self.parent is not None

    @property
    def likes_count(self):
        content_type = ContentType.objects.get_for_model(self)
        return LikeDislike.objects.filter(
            content_type=content_type, object_id=self.id, value=LikeDislike.LIKE
        ).count()

    @property
    def dislikes_count(self):
        content_type = ContentType.objects.get_for_model(self)
        return LikeDislike.objects.filter(
            content_type=content_type, object_id=self.id, value=LikeDislike.DISLIKE
        ).count()

    def user_vote(self, user):
        """برای تشخیص اینکه کاربر فعلی لایک کرده یا دیس‌لایک"""
        if not user.is_authenticated:
            return None
        content_type = ContentType.objects.get_for_model(self)
        try:
            vote = LikeDislike.objects.get(
                user=user, content_type=content_type, object_id=self.id
            )
            return vote.value
        except LikeDislike.DoesNotExist:
            return None


class Rating(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ratings",
        verbose_name="کاربر"
    )
    score = models.PositiveSmallIntegerField(
        verbose_name="امتیاز",
        choices=[(i, str(i)) for i in range(1, 6)]
    )

    # برای پشتیبانی از مدل‌های مختلف (Product, Comment و ...)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "content_type", "object_id")  # هر کاربر فقط یک امتیاز برای هر شیء
        verbose_name = "امتیاز"
        verbose_name_plural = "امتیازها"

    def __str__(self):
        return f"{self.user} → {self.content_object} ({self.score}★)"
    


class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="wishlists",
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        "products.Product",     # ✔ lazy reference — NO circular import!
        related_name="wishlisted_users",
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        verbose_name = "علاقه‌مندی"
        verbose_name_plural = "لیست علاقه‌مندی‌ها"

    def __str__(self):
        return f"{self.user} → {self.product}"



class About(models.Model):
    title = models.CharField(max_length=200, default="درباره ما", verbose_name="عنوان صفحه درباره ما")

    # **فیلدهای متا برای SEO**
    meta_title = models.CharField(max_length=70, blank=True, null=True, verbose_name="متا تایتل (SEO)")
    meta_description = models.CharField(max_length=160, blank=True, null=True, verbose_name="متا دیسکریپشن (SEO)")


    header_image = models.ImageField(upload_to="about/", blank=True, null=True, verbose_name="تصویر هدر")
    header_image_optimized = ImageSpecField(
        source='header_image',
        processors=[
            ResizeToFit(1920, 600, upscale=False),  # حداکثر عرض 1920
            Adjust(contrast=1.1, sharpness=1.2),
        ],
        format='WEBP',  # بهترین فرمت برای وب
        options={'quality': 85},
    )

    vision_title = models.CharField(max_length=200, default="دید ما", verbose_name="عنوان دید ما")
    vision_text = RichTextField(null=True, blank=True, verbose_name="متن دید ما")

    mission_title = models.CharField(max_length=200, default="ماموریت ما", verbose_name="عنوان ماموریت ما")
    mission_text = RichTextField(null=True, blank=True, verbose_name="متن ماموریت ما")

    who_title = models.CharField(max_length=200, default="ما که هستیم", verbose_name="عنوان ما که هستیم")
    who_lead = models.CharField(max_length=255, null=True, blank=True, verbose_name="متن پیش‌رو درباره ما")
    who_text = RichTextField(null=True, blank=True, verbose_name="متن ما که هستیم")
    who_image_front = models.ImageField(upload_to="about/", blank=True, null=True, verbose_name="تصویر جلو درباره ما")
    who_image_front_optimized = ImageSpecField(
        source='who_image_front',
        processors=[ResizeToFit(500, 650)],
        format='WEBP',
        options={'quality': 80},
    )
    
    who_image_back = models.ImageField(upload_to="about/", blank=True, null=True, verbose_name="تصویر عقب درباره ما")
    who_image_back_optimized = ImageSpecField(
            source='who_image_back',
            processors=[ResizeToFit(400, 550)],
            format='WEBP',
            options={'quality': 75},
    )

    brands_text = RichTextField(null=True, blank=True, verbose_name="متن برندها")

    class Meta:
        verbose_name = "درباره ما"
        verbose_name_plural = "درباره ما"

    def __str__(self):
        return self.title


# بعد از کلاس About اضافه کن
class Brand(models.Model):
    about = models.ForeignKey(About, on_delete=models.CASCADE, related_name='brands')
    name = models.CharField(max_length=100, verbose_name="نام برند")
    logo = models.ImageField(upload_to="brands/", verbose_name="لوگو برند")
    url = models.URLField(blank=True, null=True, verbose_name="لینک وبسایت برند")

    class Meta:
        verbose_name = "برند"
        verbose_name_plural = "برندها"

    def __str__(self):
        return self.name

# نسخه بهینه‌شده با imagekit (اختیاری ولی توصیه میشه)
    logo_thumb = ImageSpecField(
        source='logo',
        processors=[ResizeToFit(200, 100)],
        format='WEBP',
        options={'quality': 80}
    )


class TeamMember(models.Model):
    about = models.ForeignKey(About, on_delete=models.CASCADE, related_name="team_members")
    name = models.CharField(max_length=200, verbose_name="نام عضو تیم")
    role = models.CharField(max_length=200, verbose_name="سمت")
    bio = RichTextField(null=True, blank=True, verbose_name="بیوگرافی کوتاه")
    image = models.ImageField(upload_to="team/", blank=True, null=True, verbose_name="تصویر")
    image_thumb = ImageSpecField(
        source='image',
        processors=[ResizeToFill(400, 400)],  # مربع دقیق
        format='WEBP',
        options={'quality': 85},
    )

    facebook = models.URLField(blank=True, null=True, verbose_name="فیسبوک")
    twitter = models.URLField(blank=True, null=True, verbose_name="توییتر")
    instagram = models.URLField(blank=True, null=True, verbose_name="اینستاگرام")

    class Meta:
        verbose_name = "عضو تیم"
        verbose_name_plural = "اعضای تیم"

    def __str__(self):
        return self.name
