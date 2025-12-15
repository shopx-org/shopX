# /home/atusa92/PycharmProjects/ShopX/account/models.py
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from django.core.validators import RegexValidator
from django_jalali.db import models as jmodels


class UserManager(BaseUserManager, jmodels.jManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("You must enter a valid phone number.")
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    phone = models.CharField(max_length=11, unique=True)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(unique=True, null=True, blank=True, default=None)

    is_active = models.BooleanField(default=True, verbose_name="فعال")
    is_staff = models.BooleanField(default=False, verbose_name="ادمین سایت")
    date_joined = jmodels.jDateTimeField(default=timezone.now, verbose_name="تاریخ عضویت")

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        full = (self.first_name or "").strip() + " " + (self.last_name or "").strip()
        full = full.strip() or self.phone
        return f"{full} ({self.phone})"

    def get_full_name(self):
        return f"{(self.first_name or '').strip()} {(self.last_name or '').strip()}".strip()

    def get_short_name(self):
        return (self.first_name or self.phone).strip()


# مدل Profile برای اطلاعات اضافی
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    national_id = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        unique=True,
        verbose_name="کد ملی",
        validators=[RegexValidator(r'^\d{10}$', 'کد ملی باید ۱۰ رقم باشد.')]
    )
    day = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="روز تولد",
                                           choices=[(i, str(i).zfill(2)) for i in range(1, 32)])
    month = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="ماه تولد",
                                             choices=[(i, str(i).zfill(2)) for i in range(1, 13)])
    year = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="سال تولد",
                                            choices=[(i, str(i)) for i in range(1300, 1405)])
    gender = models.CharField(
        max_length=1,
        choices=[('M', 'مرد'), ('F', 'زن')],
        blank=True,
        null=True,
        verbose_name="جنسیت"
    )
    display_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="نام نمایش")

    class Meta:
        verbose_name = "پروفایل کاربر"
        verbose_name_plural = "پروفایل کاربران"

    def __str__(self):
        return f"پروفایل {self.user.phone}"

    @property
    def birth_date(self):
        """محاسبه تاریخ تولد به فرمت جلالی (مثلاً 1371/10/12)"""
        if self.day and self.month and self.year:
            return f"{self.year}/{str(self.month).zfill(2)}/{str(self.day).zfill(2)}"
        return None


# سیگنال برای ایجاد خودکار پروفایل
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


# مدل PasswordLock
class PasswordLock(models.Model):
    phone = models.CharField(max_length=11, unique=True)
    failed = models.PositiveSmallIntegerField(default=0)
    locked_until = jmodels.jDateTimeField(null=True, blank=True)

    objects = jmodels.jManager()

    def is_locked(self):
        return self.locked_until and timezone.now() < self.locked_until
