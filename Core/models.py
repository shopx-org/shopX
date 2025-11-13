# core/models.py
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django_jalali.db import models as jmodels


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