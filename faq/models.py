from django.db import models


class FAQCategory(models.Model):
    title = models.CharField(max_length=150, blank=True, null=True, verbose_name="عنوان دسته‌بندی")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")

    class Meta:
        ordering = ('order',)
        verbose_name = "دسته‌بندی سوالات"
        verbose_name_plural = "دسته‌بندی سوالات"

    def __str__(self):
        return self.title


class FAQ(models.Model):
    category = models.ForeignKey(
        FAQCategory,
        on_delete=models.CASCADE,
        related_name='faqs',
        blank=True, 
        null=True,
        verbose_name="دسته‌بندی"
    )
    question = models.CharField(max_length=255, blank=True, null=True, verbose_name="سؤال")
    answer = models.TextField(blank=True, null=True, verbose_name="پاسخ")
    order = models.PositiveIntegerField(default=0, blank=True, null=True, verbose_name="ترتیب نمایش")

    class Meta:
        ordering = ('category__order', 'order')
        verbose_name = "سؤال"
        verbose_name_plural = "سوالات متداول"

    def __str__(self):
        return self.question
