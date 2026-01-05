import jdatetime
from django import forms
from django.utils import timezone
from django_jalali.admin.widgets import AdminjDateWidget, AdminTimeWidget


class AdminJalaliSplitDateTimeWidget(forms.MultiWidget):
    """
    Widget فقط کارش UI هست:
      - تاریخ جلالی
      - ساعت
    و حتماً باید لیست [date, time] بده (نه datetime و نه None)
    """

    def __init__(self, attrs=None):
        widgets = [
            AdminjDateWidget(attrs=attrs),
            AdminTimeWidget(attrs=attrs),
        ]
        super().__init__(widgets=widgets, attrs=attrs)

    def decompress(self, value):
        if not value:
            return [None, None]

        if timezone.is_aware(value):
            value = timezone.localtime(value)

        j_date = jdatetime.date.fromgregorian(date=value.date()).strftime("%Y-%m-%d")
        return [j_date, value.time().replace(microsecond=0)]