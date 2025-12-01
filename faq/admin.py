from django.contrib import admin
from .models import FAQCategory, FAQ


@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'order')
    list_editable = ('order',)
    ordering = ('order',)
    search_fields = ('title',)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'order')
    list_editable = ('order',)
    list_filter = ('category',)
    search_fields = ('question', 'answer')
    ordering = ('category__order', 'order')
