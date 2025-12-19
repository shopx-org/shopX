from django.db import models
from ckeditor.fields import RichTextField
from django.core.exceptions import ValidationError
class TermsAndConditions(models.Model):
    title = models.CharField(max_length=200, default="قوانین و مقررات فروشگاه")
    content = RichTextField()
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

    banner_image = models.ImageField(
        upload_to='home/banner/images/',
        null=True,
        blank=True,
        verbose_name="تصویر بنر"
    )

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