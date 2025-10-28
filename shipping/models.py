# shipping/models.py
from django.db import models
from account.models import User

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    title = models.CharField(max_length=100, blank=True, verbose_name="نام آدرس")
    province = models.CharField(max_length=50, verbose_name="استان")
    city = models.CharField(max_length=50, verbose_name="شهر")
    address = models.TextField(verbose_name="آدرس دقیق")
    number = models.CharField(max_length=50, blank=True, verbose_name="پلاک")
    unit = models.CharField(max_length=50, blank=True, verbose_name="واحد")
    postal_code = models.CharField(max_length=10, verbose_name="کد پستی")
    latitude = models.FloatField(null=True, blank=True, verbose_name="عرض جغرافیایی")
    longitude = models.FloatField(null=True, blank=True, verbose_name="طول جغرافیایی")
    is_default = models.BooleanField(default=False, verbose_name="آدرس پیش‌فرض")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "آدرس"
        verbose_name_plural = "آدرس‌ها"

    def __str__(self):
        title_str = f"{self.title} - " if self.title else ""
        return f"{title_str}{self.province} - {self.city} - {self.address[:50]}..."