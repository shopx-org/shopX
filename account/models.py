from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils import timezone


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
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
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


# account/models.py
class PasswordLock(models.Model):
    phone = models.CharField(max_length=11, unique=True)
    failed = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    def is_locked(self):
        return self.locked_until and timezone.now() < self.locked_until
