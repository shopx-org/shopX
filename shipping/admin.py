# shipping/admin.py
from django.contrib import admin
from .models import Address, ShippingMethod

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'province', 'city', 'number', 'unit', 'postal_code', 'is_default', 'created_at')
    list_filter = ('is_default', 'province', 'city', 'user')
    search_fields = ('title', 'address', 'number', 'unit', 'postal_code', 'user__username', 'user__phone')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'province', 'city', 'address', 'number', 'unit', 'postal_code', 'latitude', 'longitude', 'is_default')
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    ordering = ('-created_at',)


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "carrier", "is_active", "base_fee", "max_weight_grams")
    list_filter = ("carrier", "is_active")
    search_fields = ("name", "code")

