# core/models.py
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django_jalali.db import models as jmodels


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

    text = models.TextField(verbose_name="متن نظر")
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = jmodels.jDateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")
    is_active = models.BooleanField(default=True, verbose_name="فعال است؟")

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
