from django.db import models
from ckeditor.fields import RichTextField

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