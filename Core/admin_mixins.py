from django.contrib import admin
from django.db import models
from django_jalali.admin.widgets import AdminjDateWidget
from Core.jalali_form_fields import JalaliSplitDateTimeField


class JalaliAdminMixin(admin.ModelAdmin):
    formfield_overrides = {
        models.DateField: {"widget": AdminjDateWidget},
    }

    def formfield_for_dbfield(self, dbfield, request, **kwargs):
        if isinstance(dbfield, models.DateTimeField):
            return JalaliSplitDateTimeField(required=not dbfield.blank)
        return super().formfield_for_dbfield(dbfield, request, **kwargs)