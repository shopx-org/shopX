from django import forms
from django.contrib.auth import password_validation
from django.core.validators import RegexValidator
from account.models import User, Profile
from jdatetime import date as jdate  # تغییر import به jdatetime


class DashboardAccountForm(forms.ModelForm):
    first_name = forms.CharField(
        label="نام",
        required=True,
        min_length=3,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'نام خود را وارد کنید', 'name': 'first_name'}),
        error_messages={'required': 'لطفاً نام خود را وارد کنید.',
                        'min_length': 'نام باید حداقل ۳ کاراکتر باشد.'}
    )
    last_name = forms.CharField(
        label="نام خانوادگی",
        required=True,
        min_length=3,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'نام خانوادگی خود را وارد کنید', 'name': 'last_name'}),
        error_messages={'required': 'لطفاً نام خانوادگی خود را وارد کنید.',
                        'min_length': 'نام خانوادگی باید حداقل ۳ کاراکتر باشد.'}
    )
    email = forms.EmailField(
        label="ایمیل",
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ایمیل شما', 'name': 'email'}),
        error_messages={'invalid': 'لطفاً یک ایمیل معتبر وارد کنید.'}
    )

    # فیلدهای Profile
    display_name = forms.CharField(
        label="نام نمایشی",
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'نامی که در سایت نمایش داده شود', 'name': 'display_name'})
    )
    national_id = forms.CharField(
        label="کد ملی",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'کد ملی ۱۰ رقمی',
            'name': 'national_id',
            'type': 'text',
            'maxlength': '10',
            'pattern': '[0-9]{10}',
            'onkeypress': 'return (event.charCode !=8 && event.charCode ==0 || (event.charCode >= 48 && event.charCode <= 57))'
        }),
        validators=[
            RegexValidator(
                regex=r'^\d{10}$',
                message='کد ملی باید دقیقاً ۱۰ رقم باشد و فقط شامل اعداد باشد.'
            )
        ]
    )
    day = forms.ChoiceField(
        label="روز",
        required=False,
        choices=[(str(i).zfill(2), str(i).zfill(2)) for i in range(1, 32)],
        widget=forms.Select(attrs={'class': 'form-control', 'name': 'day'})
    )
    month = forms.ChoiceField(
        label="ماه",
        required=False,
        choices=[
            ('01', 'فروردین'), ('02', 'اردیبهشت'), ('03', 'خرداد'),
            ('04', 'تیر'), ('05', 'مرداد'), ('06', 'شهریور'),
            ('07', 'مهر'), ('08', 'آبان'), ('09', 'آذر'),
            ('10', 'دی'), ('11', 'بهمن'), ('12', 'اسفند')
        ],
        widget=forms.Select(attrs={'class': 'form-control', 'name': 'month'})
    )
    year = forms.ChoiceField(
        label="سال",
        required=False,
        choices=[(str(i), str(i)) for i in range(1300, jdate.today().year - 6)],  # 1404 - 7 = 1397 (سال جاری منهای 7)
        widget=forms.Select(attrs={'class': 'form-control', 'name': 'year'})
    )
    gender = forms.ChoiceField(
        label="جنسیت",
        choices=[('', 'انتخاب کنید'), ('M', 'مرد'), ('F', 'زن'), ('O', 'سایر')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'name': 'gender'})
    )

    # فیلدهای تغییر رمز
    new_password = forms.CharField(
        label="رمز جدید",
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'رمز جدید (حداقل ۸ کاراکتر، شامل حروف کوچک، بزرگ و عدد)',
            'name': 'new_password'
        })
    )
    confirm_password = forms.CharField(
        label="تکرار رمز جدید",
        required=False,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'تکرار رمز جدید', 'name': 'confirm_password'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            profile = self.instance.profile
            self.fields['display_name'].initial = profile.display_name or ''
            self.fields['national_id'].initial = profile.national_id or ''
            self.fields['day'].initial = str(profile.day).zfill(2) if profile.day else ''
            self.fields['month'].initial = str(profile.month).zfill(2) if profile.month else ''
            self.fields['year'].initial = str(profile.year) if profile.year else ''
            self.fields['gender'].initial = profile.gender or ''
            # self.fields['phone'].initial = self.instance.phone or ''

    def clean(self):
        cleaned_data = super().clean()
        new_pw = cleaned_data.get('new_password')
        confirm_pw = cleaned_data.get('confirm_password')
        #
        # اعتبارسنجی رمز عبور
        if new_pw or confirm_pw:
            if new_pw != confirm_pw:
                self.add_error('confirm_password', 'رمز جدید و تکرار آن یکسان نیستند.')
            if new_pw:
                # بررسی حداقل طول
                if len(new_pw) < 8:
                    self.add_error('new_password', 'رمز عبور باید حداقل ۸ کاراکتر باشد.')
                # بررسی وجود حروف کوچک
                if not any(c.islower() for c in new_pw):
                    self.add_error('new_password', 'رمز عبور باید حداقل شامل یک حرف کوچک باشد.')
                # بررسی وجود حروف بزرگ
                if not any(c.isupper() for c in new_pw):
                    self.add_error('new_password', 'رمز عبور باید حداقل شامل یک حرف بزرگ باشد.')
                # بررسی وجود عدد
                if not any(c.isdigit() for c in new_pw):
                    self.add_error('new_password', 'رمز عبور باید حداقل شامل یک عدد باشد.')
                # اعتبارسنجی‌های پیش‌فرض جنگو
                try:
                    password_validation.validate_password(new_pw, self.user)
                except forms.ValidationError as e:
                    self.add_error('new_password', 'رمز جدید نامعتبر است: ' + '; '.join([str(m) for m in e.messages]))

        # بررسی یکتایی ایمیل
        email = cleaned_data.get('email')
        if email and User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            self.add_error('email', 'این ایمیل قبلاً توسط حساب کاربری دیگری استفاده شده است.')

        # بررسی یکتایی کد ملی
        national_id = cleaned_data.get('national_id')
        if national_id and Profile.objects.filter(national_id=national_id).exclude(user=self.user).exists():
            self.add_error('national_id', 'این کد ملی قبلاً توسط حساب کاربری دیگری استفاده شده است.')

        # بررسی یکتایی شماره تلفن
        # phone = cleaned_data.get('phone')
        # if phone and User.objects.filter(phone=phone).exclude(pk=self.user.pk).exists():
        #     self.add_error('phone', 'این شماره تلفن قبلاً توسط حساب کاربری دیگری استفاده شده است.')

        # اعتبارسنجی تاریخ تولد
        day = cleaned_data.get('day')
        month = cleaned_data.get('month')
        year = cleaned_data.get('year')
        if day or month or year:
            try:
                day, month, year = int(day), int(month), int(year)
                if not (1 <= day <= 31 and 1 <= month <= 12 and 1300 <= year <= jdate.today().year - 6):
                    self.add_error('birth_date', 'لطفاً یک تاریخ معتبر وارد کنید.')
            except ValueError:
                self.add_error('birth_date', 'لطفاً مقادیر معتبر برای روز، ماه و سال وارد کنید.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile, created = Profile.objects.get_or_create(user=user)
            profile.display_name = self.cleaned_data['display_name'] or None
            profile.national_id = self.cleaned_data['national_id'] or None
            profile.day = self.cleaned_data['day'] or None
            profile.month = self.cleaned_data['month'] or None
            profile.year = self.cleaned_data['year'] or None
            profile.gender = self.cleaned_data['gender'] or None
            profile.save()

            new_pw = self.cleaned_data.get('new_password')
            if new_pw:
                user.set_password(new_pw)
                user.save()

        return user


# در انتهای forms.py اضافه کن:
class ChangePhoneNumberForm(forms.Form):
    new_phone = forms.CharField(
        label="شماره جدید",
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'شماره تلفن جدید (با ۰۹ شروع شود)',
            'maxlength': '11',
            'pattern': '[0][9][0-9]{9}',
            'type': 'tel',
            'inputmode': 'numeric',
        }),
        validators=[
            RegexValidator(
                regex=r'^09\d{9}$',
                message='شماره تلفن باید با ۰۹ شروع شود و دقیقاً ۱۱ رقم عددی باشد.'
            )
        ],
        error_messages={'required': 'لطفاً شماره تلفن جدید را وارد کنید.'}
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_new_phone(self):
        phone = self.cleaned_data.get('new_phone', '').strip()

        # بررسی عدد بودن
        if not phone.isdigit():
            raise forms.ValidationError('شماره تلفن فقط باید شامل اعداد باشد.')

        # بررسی طول دقیق و شروع با 09
        if not phone.startswith('09') or len(phone) != 11:
            raise forms.ValidationError('شماره تلفن باید با ۰۹ شروع شود و دقیقاً ۱۱ رقم باشد.')

        # بررسی تکراری نبودن
        if User.objects.filter(phone=phone).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('این شماره تلفن قبلاً توسط کاربر دیگری استفاده شده است.')

        return phone