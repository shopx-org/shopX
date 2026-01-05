from django.db import models
from products.models import Brand, Category
from django.core.exceptions import ValidationError

class TermsAndConditions(models.Model):
    title = models.CharField(max_length=200, default="قوانین و مقررات فروشگاه")
    content = models.TextField(blank=True, null=True, verbose_name="متن")
    meta_title = models.CharField(max_length=200, blank=True, null=True)
    meta_description = models.CharField(max_length=300, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


    class Meta:
        verbose_name = "قوانین و مقررات"
        verbose_name_plural = " قوانین و مقررات"


def validate_video(file):
    max_size = 30 * 1024 * 1024
    if file.size > max_size:
        raise ValidationError("حجم ویدیو نباید بیشتر از 30 مگابایت باشد.")

    valid_extensions = ['mp4', 'webm', 'ogg']
    ext = file.name.split('.')[-1].lower()
    if ext not in valid_extensions:
        raise ValidationError("فرمت ویدیو باید mp4 یا webm یا ogg باشد.")


class HomeVideoBanner(models.Model):
    title_small = models.CharField("عنوان کوچک", max_length=100)
    title_big = models.CharField("عنوان بزرگ", max_length=150)

    video_file = models.FileField(
        upload_to='home/banner/videos/',
        validators=[validate_video],
        verbose_name="ویدیو"
    )

    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "بنر ویدیویی صفحه اصلی"
        verbose_name_plural = "بنر ویدیویی صفحه اصلی"

    def __str__(self):
        return "بنر ویدیویی صفحه اصلی"




class HomeBrandBanner(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, verbose_name="برند")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="دسته‌بندی (اختیاری)"
    )
    title = models.CharField(max_length=120, blank=True, verbose_name="تیتر")
    subtitle = models.CharField(max_length=120, blank=True, verbose_name="زیرتیتر")
    image = models.ImageField(upload_to="home/banners/", null=True, blank=True, verbose_name="تصویر بنر")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    position = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        ordering = ["position", "-id"]
        verbose_name = "بنر برند صفحه اصلی"
        verbose_name_plural = "بنرهای برند صفحه اصلی"

    def __str__(self):
        return f"{self.brand.name}"