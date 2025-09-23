from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.validators import RegexValidator, MinLengthValidator, MaxLengthValidator
from django.contrib.auth import password_validation
from django.utils.safestring import mark_safe

from .models import User
from django.core.exceptions import ValidationError
import re


# ---- Admin forms for custom user ----
class XUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("phone", "email", "first_name", "last_name", "is_active", "is_staff", "is_superuser")

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if not phone:
            raise forms.ValidationError("شماره تلفن نمی‌تواند خالی باشد.")
        if not phone.isdigit():
            raise forms.ValidationError("شماره تلفن باید فقط شامل ارقام باشد.")
        if not phone.startswith("09"):
            raise forms.ValidationError("شماره تلفن باید با 09 شروع شود.")
        if len(phone) != 11:
            raise forms.ValidationError("شماره تلفن باید ۱۱ رقم باشد.")
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("این شماره تلفن قبلاً ثبت شده است.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("این ایمیل قبلاً ثبت شده است.")
        return email


class XUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = ("phone", "email", "first_name", "last_name", "is_active", "is_staff", "is_superuser")

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if not phone:
            raise forms.ValidationError("شماره تلفن نمی‌تواند خالی باشد.")
        if not phone.isdigit():
            raise forms.ValidationError("شماره تلفن باید فقط شامل ارقام باشد.")
        if not phone.startswith("09"):
            raise forms.ValidationError("شماره تلفن باید با 09 شروع شود.")
        if len(phone) != 11:
            raise forms.ValidationError("شماره تلفن باید ۱۱ رقم باشد.")
        qs = User.objects.filter(phone=phone)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("این شماره تلفن قبلاً ثبت شده است.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email")
        qs = User.objects.all()
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if email and qs.filter(email=email).exists():
            raise forms.ValidationError("این ایمیل قبلاً ثبت شده است.")
        return email


# ---- Public forms ----
class RegisterForm(forms.Form):
    phone = forms.CharField(
        label="شماره موبایل",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "09xxxxxxxxx"}),
        validators=[MinLengthValidator(11), MaxLengthValidator(11), RegexValidator(r"^09\d{9}$")],
    )


# class LoginForm(forms.Form):
#     phone = forms.CharField(
#         label="شماره موبایل",
#         widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "09xxxxxxxxx"}),
#         validators=[MinLengthValidator(11), MaxLengthValidator(11), RegexValidator(r"^09\d{9}$")],
#     )
#     password = forms.CharField(
#         label="رمز عبور",
#         widget=forms.PasswordInput(attrs={"class": "form-control"}),
#     )


class CheckOtpForm(forms.Form):
    code = forms.CharField(
        label="کد ۴ رقمی",
        widget=forms.TextInput(attrs={"class": "otp-number-input", "inputmode": "numeric", "pattern": "[0-9]*"}),
        validators=[RegexValidator(r"^\d{4}$")],
    )

class PasswordOnlyForm(forms.Form):
    password = forms.CharField(
        label="رمز عبور",
        widget=forms.PasswordInput(attrs={"class": "login-input", "placeholder": "رمز عبور"}),
    )


class ForgotPasswordForm(forms.Form):
    phone = forms.CharField(
        label="شماره موبایل",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "09xxxxxxxxx"}),
        validators=[MinLengthValidator(11), MaxLengthValidator(11), RegexValidator(r"^09\d{9}$")],
    )

class SetPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label="رمز عبور جدید",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
            "class": "login-input",
            "placeholder": "رمز عبور جدید",
        }),
    )
    new_password2 = forms.CharField(
        label="تکرار رمز عبور",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
            "class": "login-input",
            "placeholder": "تکرار رمز عبور",
        }),
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        # (اختیاری) help_text فارسی:
        self.fields['new_password1'].help_text = mark_safe(
            "حداقل ۱۰ کاراکتر، بهتر است ترکیبی از حروف بزرگ/کوچک، عدد و نماد باشد. از رمزهای رایج و تماماً عددی استفاده نکنید."
        )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")

        if p1 and p2 and p1 != p2:
            self.add_error("new_password2", "دو رمز عبور وارد شده یکسان نیستند.")
            raise forms.ValidationError("رمزها با هم برابر نیستند.")

        if p1:
            try:
                password_validation.validate_password(p1, user=self.user)
            except ValidationError as e:
                # نگاشت کدهای پیش‌فرض جنگو به پیام فارسی
                fa = []
                for err in e.error_list:
                    code   = getattr(err, "code", "")
                    params = getattr(err, "params", {}) or {}
                    if code == "password_too_short":
                        # از MinimumLengthValidator می‌آید
                        fa.append("رمز عبور کوتاه است؛ حداقل %(min_length)d کاراکتر لازم است." % params)
                    elif code == "password_too_common":
                        fa.append("این رمز عبور بسیار رایج است. لطفاً رمز قوی‌تری انتخاب کنید.")
                    elif code == "password_entirely_numeric":
                        fa.append("رمز عبور نباید فقط از اعداد تشکیل شده باشد.")
                    elif code == "password_too_similar":
                        # از UserAttributeSimilarityValidator می‌آید
                        # می‌توان نام فیلد مشابه را هم نشان داد (در params['verbose_name'])
                        vn = params.get("verbose_name")
                        if vn:
                            fa.append(f"رمز عبور بیش از حد شبیه «{vn}» شماست.")
                        else:
                            fa.append("رمز عبور بیش از حد شبیه اطلاعات پروفایل شماست.")
                    else:
                        # برای هر مورد غیرمنتظره
                        fa.append(str(err))
                raise forms.ValidationError(fa)

        return cleaned