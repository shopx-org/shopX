from django.db import models
from ckeditor.fields import RichTextField
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFit, Adjust, Transpose, ResizeToFill
from django.utils.translation import gettext_lazy as _


class Contact(models.Model):
    # عنوان داخلی (برای تمایز چند صفحه/نسخه در admin)
    title = models.CharField(max_length=120, verbose_name=_("عنوان"), default="تماس با ما")

    # فیلدهای متا برای SEO
    meta_title = models.CharField(max_length=70, blank=True, null=True, verbose_name=_("متا تایتل (SEO)"))
    meta_description = models.CharField(max_length=160, blank=True, null=True, verbose_name=_("متا دیسکریپشن (SEO)"))

    # تصویر هدر و نسخه بهینه‌شده برای نمایش در سایت
    header_image = models.ImageField(upload_to="contact/", blank=True, null=True, verbose_name=_("تصویر هدر"))
    header_image_optimized = ImageSpecField(
        source='header_image',
        processors=[
            ResizeToFit(1920, 600, upscale=False),
            Adjust(contrast=1.1, sharpness=1.2),
        ],
        format='WEBP',
        options={'quality': 85},
    )

    # در صورت نیاز می‌شه فیلد متنی/ریچ‌تکست اضافه کرد (مثال: intro_text)
    intro_text = models.TextField(blank=True, null=True, verbose_name=_("متن معرفی کوتاه"))

    class Meta:
        verbose_name = _("تماس با ما")
        verbose_name_plural = _("تماس با ما")

    def __str__(self):
        return self.title



class ContactMessage(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام")
    email = models.EmailField(verbose_name="ایمیل")
    phone = models.CharField(max_length=20, blank=True, verbose_name="شماره تماس")
    subject = models.CharField(max_length=200, blank=True, verbose_name="موضوع")
    message = models.TextField(verbose_name="متن پیام")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    is_read = models.BooleanField(default=False, verbose_name="خوانده شده؟")

    class Meta:
        verbose_name = "پیام تماس"
        verbose_name_plural = "پیام های تماس"

    def __str__(self):
        return f"{self.name} - {self.subject}"
