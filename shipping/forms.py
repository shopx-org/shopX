from django import forms
from django.core.validators import RegexValidator
from .models import Address
from .cities import CITIES_NORM, _norm  # فرض بر این است که cities.py JSON را از static می‌خواند

# ------------------- استان‌ها -------------------
PROVINCES = [
    ('', 'انتخاب استان'),  # 🔸 گزینه پیش‌فرض
    ('آذربایجان شرقی', 'آذربایجان شرقی'),
    ('آذربایجان غربی', 'آذربایجان غربی'),
    ('اردبیل', 'اردبیل'),
    ('اصفهان', 'اصفهان'),
    ('البرز', 'البرز'),
    ('ایلام', 'ایلام'),
    ('بوشهر', 'بوشهر'),
    ('تهران', 'تهران'),
    ('چهارمحال و بختیاری', 'چهارمحال و بختیاری'),
    ('خراسان جنوبی', 'خراسان جنوبی'),
    ('خراسان رضوی', 'خراسان رضوی'),
    ('خراسان شمالی', 'خراسان شمالی'),
    ('خوزستان', 'خوزستان'),
    ('زنجان', 'زنجان'),
    ('سمنان', 'سمنان'),
    ('سیستان و بلوچستان', 'سیستان و بلوچستان'),
    ('فارس', 'فارس'),
    ('قزوین', 'قزوین'),
    ('قم', 'قم'),
    ('کردستان', 'کردستان'),
    ('کرمان', 'کرمان'),
    ('کرمانشاه', 'کرمانشاه'),
    ('کهگیلویه و بویراحمد', 'کهگیلویه و بویراحمد'),
    ('گلستان', 'گلستان'),
    ('گیلان', 'گیلان'),
    ('لرستان', 'لرستان'),
    ('مازندران', 'مازندران'),
    ('مرکزی', 'مرکزی'),
    ('هرمزگان', 'هرمزگان'),
    ('همدان', 'همدان'),
    ('یزد', 'یزد'),
]


class AddressForm(forms.ModelForm):
    title = forms.CharField(
        label="نام آدرس",
        required=True,  # 🔹 الزامی شد
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '* نام آدرس (مثل خانه یا محل کار)'}),
        error_messages={
            'required': 'لطفاً نام آدرس را وارد کنید.',
            'max_length': 'نام آدرس نمی‌تواند بیشتر از ۱۰۰ کاراکتر باشد.',
        }
    )

    province = forms.ChoiceField(
        label="استان",
        choices=PROVINCES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_province'}),
        error_messages={
            'required': 'لطفاً استان را انتخاب کنید.',
            'invalid_choice': 'استان انتخاب‌شده معتبر نیست.',
        }
    )

    city = forms.CharField(
        label="شهر",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_city'}),
        error_messages={
            'required': 'لطفاً شهر را انتخاب کنید.',
        }
    )

    address = forms.CharField(
        label="آدرس دقیق",
        required=True,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': '* آدرس کامل', 'rows': 3}),
        error_messages={
            'required': 'لطفاً آدرس دقیق را وارد کنید.',
        }
    )

    # 🔹 فقط عدد برای پلاک
    number = forms.CharField(
        label="پلاک",
        required=False,
        max_length=5,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'پلاک',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
        }),
        validators=[RegexValidator(r'^\d*$', 'پلاک باید فقط شامل عدد باشد.')],
        error_messages={
            'max_length': 'پلاک نمی‌تواند بیشتر از ۵ رقم باشد.',
        }
    )

    # 🔹 فقط عدد برای واحد
    unit = forms.CharField(
        label="واحد",
        required=False,
        max_length=5,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'واحد',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
        }),
        validators=[RegexValidator(r'^\d*$', 'واحد باید فقط شامل عدد باشد.')],
        error_messages={
            'max_length': 'واحد نمی‌تواند بیشتر از ۵ رقم باشد.',
        }
    )

    postal_code = forms.CharField(
        label="کد پستی",
        required=True,
        max_length=10,
        min_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '* کد پستی ۱۰ رقمی',
            'maxlength': '10',
            'pattern': '[0-9]{10}',
            'inputmode': 'numeric',
        }),
        validators=[
            RegexValidator(regex=r'^\d{10}$', message='کد پستی باید دقیقاً ۱۰ رقم عددی باشد.')
        ],
        error_messages={
            'required': 'لطفاً کد پستی را وارد کنید.',
            'max_length': 'کد پستی باید دقیقاً ۱۰ رقم باشد.',
            'min_length': 'کد پستی باید دقیقاً ۱۰ رقم باشد.',
        }
    )

    latitude = forms.FloatField(
        label="عرض جغرافیایی",
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'latitude'}),
        error_messages={'invalid': 'مقدار عرض جغرافیایی نامعتبر است.'}
    )

    longitude = forms.FloatField(
        label="طول جغرافیایی",
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'longitude'}),
        error_messages={'invalid': 'مقدار طول جغرافیایی نامعتبر است.'}
    )

    is_default = forms.BooleanField(
        label="آدرس پیش‌فرض",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Address
        fields = [
            'title', 'province', 'city', 'address',
            'number', 'unit', 'postal_code',
            'latitude', 'longitude', 'is_default'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # برای نمایش شهرهای مرتبط با استان انتخابی
        raw_province = (
            self.data.get('province')
            or self.initial.get('province')
            or getattr(getattr(self, 'instance', None), 'province', '')
            or ''
        )
        raw_city = (
            self.data.get('city')
            or self.initial.get('city')
            or getattr(getattr(self, 'instance', None), 'city', '')
            or ''
        )

        prov_norm = _norm(raw_province)
        city_norm = _norm(raw_city)

        valid_cities_norm = CITIES_NORM.get(prov_norm, [])
        choices = [('', 'انتخاب شهر')] + [(c, c) for c in valid_cities_norm]

        if city_norm and city_norm not in [v for v, _ in choices]:
            choices.append((city_norm, raw_city or city_norm))

        self.fields['city'].widget.choices = choices

    def clean_city(self):
        raw_city = (self.cleaned_data.get('city') or '')
        raw_province = (self.cleaned_data.get('province') or '')

        city = _norm(raw_city)
        province = _norm(raw_province)

        if not city:
            raise forms.ValidationError('لطفاً شهر را انتخاب کنید.')

        valid = set(CITIES_NORM.get(province, []))
        if city in valid:
            return raw_city
        raise forms.ValidationError('شهر انتخاب‌شده با استان انتخاب‌شده هم‌خوانی ندارد.')

    def clean(self):
        cleaned_data = super().clean()
        lat = cleaned_data.get('latitude')
        lon = cleaned_data.get('longitude')
        if lat is not None and (lat < -90 or lat > 90):
            self.add_error('latitude', 'عرض جغرافیایی باید بین -۹۰ تا ۹۰ باشد.')
        if lon is not None and (lon < -180 or lon > 180):
            self.add_error('longitude', 'طول جغرافیایی باید بین -۱۸۰ تا ۱۸۰ باشد.')
        return cleaned_data

    def save(self, commit=True, user=None):
        address = super().save(commit=False)
        if user:
            address.user = user
        if commit:
            if address.is_default:
                Address.objects.filter(user=address.user, is_default=True).exclude(pk=address.pk).update(is_default=False)
            address.save()
        return address
