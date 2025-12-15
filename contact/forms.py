from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
import re
from .models import ContactMessage


# ---------------------------
#   Bad Patterns (Advanced)
# ---------------------------
BAD_PATTERNS = [
    r"<.*?>",                 # هر نوع تگ HTML
    r"&lt;.*?&gt;",           # نسخه انکود شده تگ‌ها
    r"<\s*script",            # <script
    r"<\s*/\s*script",        # </script>
    r"javascript:",           # جاوااسکریپت
    r"on\w+=",                # onclick= , onerror= , ...
    r"https?://",             # لینک‌های http و https
    r"www\.",                 # لینک با www
]


def contains_bad_patterns(value):
    """چک می‌کند آیا کاربر کد، لینک یا HTML وارد کرده یا خیر"""
    for pattern in BAD_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE | re.MULTILINE):
            return True
    return False


# ---------------------------
#      Contact Form
# ---------------------------
class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام خود را وارد کنید *',
                'maxlength': '100',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'ایمیل خود را وارد کنید *'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'شماره موبایل (مثال: 09123456789)',
                'maxlength': '11',
                'inputmode': 'numeric',
                'pattern': '09[0-9]{9}'
            }),

            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'موضوع پیام',
                'maxlength': '150'
            }),

            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'متن پیام شما *',
                'maxlength': '2000'
            }),
        }

    # ---------------------------
    #       Validations
    # ---------------------------

    def clean_name(self):
        value = strip_tags(self.cleaned_data.get("name", "")).strip()

        if len(value) < 3:
            raise forms.ValidationError("نام باید حداقل ۳ کاراکتر باشد.")

        if contains_bad_patterns(value):
            raise forms.ValidationError("نام فقط باید شامل متن ساده باشد.")

        return value

    def clean_subject(self):
        raw_value = self.cleaned_data.get("subject", "")

        if contains_bad_patterns(raw_value):
            raise ValidationError("موضوع نباید شامل لینک یا کد باشد.")

        cleaned_value = strip_tags(raw_value).strip()

        if len(cleaned_value) < 3:
            raise ValidationError("موضوع باید حداقل ۳ کاراکتر باشد.")

        return cleaned_value


    def clean_message(self):
        raw_value = self.cleaned_data.get("message", "")

        # چک قبل از strip_tags
        if contains_bad_patterns(raw_value):
            raise ValidationError("متن پیام نباید شامل کد، تگ یا اسکریپت باشد.")

        cleaned_value = strip_tags(raw_value).strip()

        if len(cleaned_value) < 5:
            raise ValidationError("متن پیام خیلی کوتاه است.")

        return cleaned_value


    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()

        # فقط عدد
        if not phone.isdigit():
            raise forms.ValidationError("شماره موبایل فقط باید شامل عدد باشد.")

        # دقیقا 11 رقم
        if len(phone) != 11:
            raise forms.ValidationError("شماره موبایل باید دقیقاً ۱۱ رقم باشد.")

        # شروع با 09
        if not phone.startswith("09"):
            raise forms.ValidationError("شماره موبایل باید با 09 شروع شود.")

        return phone
