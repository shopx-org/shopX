from django.contrib import admin
from .models import ContactMessage
from django.utils.html import format_html
from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("title", "header_image_thumb",)
    readonly_fields = ("header_image_preview",)
    fieldsets = (
        ("محتوا", {
            "fields": ("title", "intro_text")
        }),
        ("تصویر هدر", {
            "fields": ("header_image", "header_image_preview"),
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description"),
            "classes": ("collapse",),
        }),
    )

    def header_image_preview(self, obj):
        if obj.header_image_optimized:
            try:
                url = obj.header_image_optimized.url
                return format_html('<img src="{}" style="max-width: 100%; height: auto; border-radius:6px;" />', url)
            except Exception:
                # fallback to original
                if obj.header_image:
                    return format_html('<img src="{}" style="max-width: 100%; height: auto; border-radius:6px;" />', obj.header_image.url)
        return "(بدون تصویر)"
    header_image_preview.short_description = "پیش‌نمایش تصویر هدر"

    def header_image_thumb(self, obj):
        if obj.header_image_optimized:
            try:
                url = obj.header_image_optimized.url
                return format_html('<img src="{}" style="max-width:120px; height:auto; border-radius:4px;" />', url)
            except Exception:
                if obj.header_image:
                    return format_html('<img src="{}" style="max-width:120px; height:auto; border-radius:4px;" />', obj.header_image.url)
        return "-"
    header_image_thumb.short_description = "هدر"



@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'phone')
