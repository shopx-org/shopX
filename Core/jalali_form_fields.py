from datetime import datetime
import jdatetime

from django import forms
from django.utils import timezone

from Core.jalali_admin_widgets import AdminJalaliSplitDateTimeWidget


class JalaliDateField(forms.Field):
    def clean(self, value):
        value = super().clean(value)
        if not value:
            return None
        value = str(value).strip()

        # Jalali: 1404-10-05
        try:
            j = jdatetime.datetime.strptime(value, "%Y-%m-%d").date()
            return j.togregorian()
        except Exception:
            pass

        # Gregorian fallback: 2025-12-26
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except Exception:
            raise forms.ValidationError("تاریخ معتبر نیست.")


class JalaliSplitDateTimeField(forms.MultiValueField):
    widget = AdminJalaliSplitDateTimeWidget  # ✅ خیلی مهم

    def __init__(self, *args, **kwargs):
        fields = [JalaliDateField(), forms.TimeField()]
        super().__init__(fields=fields, require_all_fields=True, *args, **kwargs)

    def compress(self, data_list):
        if not data_list:
            return None
        date_val, time_val = data_list
        if not date_val or not time_val:
            return None

        dt = datetime.combine(date_val, time_val)

        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
