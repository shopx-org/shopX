from django.contrib import admin
from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_object', 'short_text', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__phone', 'user__first_name', 'user__last_name', 'text')
    readonly_fields = ('created_at', 'updated_at')

    # نمایش تمیزتر برای مدل‌های GenericForeignKey
    def content_object(self, obj):
        return f"{obj.content_type} - {obj.object_id}"

