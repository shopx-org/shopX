from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from django.core.validators import RegexValidator


# موجود در کد قبلی
class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("You must enter a valid phone number.")
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            # اجازهٔ ورود با OTP بدون پسورد
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
    date_joined = models.DateTimeField(default=timezone.now, verbose_name="تاریخ عضویت")

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
    birth_date = models.DateField(blank=True, null=True, verbose_name="تاریخ تولد")
    gender = models.CharField(
        max_length=1,
        choices=[('M', 'مرد'), ('F', 'زن'), ('O', 'سایر')],
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


# سیگنال برای ایجاد خودکار پروفایل
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

#
# # مدل Address برای مدیریت آدرس‌ها
# class Address(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
#     first_name = models.CharField(max_length=30, verbose_name="نام")
#     last_name = models.CharField(max_length=30, verbose_name="نام خانوادگی")
#     company_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="نام شرکت")
#     province = models.CharField(max_length=100, verbose_name="استان")
#     city = models.CharField(max_length=100, verbose_name="شهر")
#     street = models.CharField(max_length=255, verbose_name="خیابان")
#     plaque = models.CharField(max_length=10, blank=True, null=True, verbose_name="پلاک")
#     postal_code = models.CharField(
#         max_length=10,
#         verbose_name="کد پستی",
#         validators=[RegexValidator(r'^\d{10}$', 'کد پستی باید ۱۰ رقم باشد.')]
#     )
#     phone = models.CharField(
#         max_length=11,
#         verbose_name="شماره تماس",
#         validators=[RegexValidator(r'^09\d{9}$', 'شماره باید با ۰۹ شروع شود و ۱۱ رقم باشد.')]
#     )
#     is_default = models.BooleanField(default=False, verbose_name="آدرس پیش‌فرض")
#
#     class Meta:
#         verbose_name = "آدرس"
#         verbose_name_plural = "آدرس‌ها"
#
#     def __str__(self):
#         return f"{self.province} - {self.city} - {self.street}"
#
#     def save(self, *args, **kwargs):
#         if self.is_default:
#             Address.objects.filter(user=self.user, is_default=True).exclude(id=self.id).update(is_default=False)
#         super().save(*args, **kwargs)


# مدل PasswordLock (موجود در کد قبلی)
class PasswordLock(models.Model):
    phone = models.CharField(max_length=11, unique=True)
    failed = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    def is_locked(self):
        return self.locked_until and timezone.now() < self.locked_until

# from django.db import models
# from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
# from django.utils import timezone
#
#
# class UserManager(BaseUserManager):
#     def create_user(self, phone, password=None, **extra_fields):
#         if not phone:
#             raise ValueError("You must enter a valid phone number.")
#         user = self.model(phone=phone, **extra_fields)
#         if password:
#             user.set_password(password)
#         else:
#             # اجازهٔ ورود با OTP بدون پسورد
#             user.set_unusable_password()
#         user.save(using=self._db)
#         return user
#
#     def create_superuser(self, phone, password=None, **extra_fields):
#         extra_fields.setdefault('is_staff', True)
#         extra_fields.setdefault('is_superuser', True)
#         if extra_fields.get('is_staff') is not True:
#             raise ValueError("Superuser must have is_staff=True.")
#         if extra_fields.get('is_superuser') is not True:
#             raise ValueError("Superuser must have is_superuser=True.")
#         return self.create_user(phone, password, **extra_fields)
#
#
# class User(AbstractBaseUser, PermissionsMixin):
#     phone = models.CharField(max_length=11, unique=True)
#     first_name = models.CharField(max_length=30, blank=True)
#     last_name = models.CharField(max_length=30, blank=True)
#     email = models.EmailField(unique=True, null=True, blank=True, default=None)
#
#     is_active = models.BooleanField(default=True, verbose_name="فعال")
#     is_staff = models.BooleanField(default=False, verbose_name="ادمین سایت")
#     date_joined = models.DateTimeField(default=timezone.now, verbose_name="تاریخ عضویت")
#
#     objects = UserManager()
#
#     USERNAME_FIELD = "phone"
#     REQUIRED_FIELDS = []
#
#     class Meta:
#         verbose_name = "کاربر"
#         verbose_name_plural = "کاربران"
#
#     def __str__(self):
#         full = (self.first_name or "").strip() + " " + (self.last_name or "").strip()
#         full = full.strip() or self.phone
#         return f"{full} ({self.phone})"
#
#     def get_full_name(self):
#         return f"{(self.first_name or '').strip()} {(self.last_name or '').strip()}".strip()
#
#     def get_short_name(self):
#         return (self.first_name or self.phone).strip()
#
#
# # account/models.py
# class PasswordLock(models.Model):
#     phone = models.CharField(max_length=11, unique=True)
#     failed = models.PositiveSmallIntegerField(default=0)
#     locked_until = models.DateTimeField(null=True, blank=True)
#
#     def is_locked(self):
#         return self.locked_until and timezone.now() < self.locked_until
