from django.contrib import admin
from django.utils.html import format_html
from .models import Comment, LikeDislike
from django.contrib.contenttypes.models import ContentType


class ReplyFilter(admin.SimpleListFilter):
    title = 'نوع نظر'
    parameter_name = 'is_reply'

    def lookups(self, request, model_admin):
        return [
            ('yes', 'پاسخ‌ها'),
            ('no', 'کامنت‌های اصلی'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(parent__isnull=False)
        if self.value() == 'no':
            return queryset.filter(parent__isnull=True)
        return queryset


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = (
        'user_display',
        'content_object_link',
        'short_text',
        'likes_count_display',
        'dislikes_count_display',
        'created_at',
        'is_approved',
        'is_reply',
        'reply_count',
    )

    list_filter = (
        'is_approved',
        'created_at',
        'content_type',
        ReplyFilter,
    )

    search_fields = (
        'user__phone',
        'user__first_name',
        'user__last_name',
        'text'
    )

    readonly_fields = (
        'created_at',
        'updated_at',
        'content_object_link',
        'likes_count_display',
        'dislikes_count_display',
    )

    actions = [
        'approve_selected_comments',
        'unapprove_selected_comments',
        'delete_unapproved'
    ]

    def user_display(self, obj):
        return obj.user.get_full_name() or obj.user.phone
    user_display.short_description = "کاربر"

    def reply_count(self, obj):
        return obj.replies.filter(is_approved=True).count()
    reply_count.short_description = "تعداد پاسخ‌ها"

    def content_object_link(self, obj):
        model = obj.content_type.model
        app = obj.content_type.app_label
        url = f"/admin/{app}/{model}/{obj.object_id}/change/"
        return format_html('<a href="{}">{} #{} </a>', url, model, obj.object_id)
    content_object_link.short_description = "محتوا"

    # ✅ تعداد لایک‌ها
    def likes_count_display(self, obj):
        return obj.likes_count
    likes_count_display.short_description = "👍 لایک‌ها"

    # ✅ تعداد دیسلایک‌ها
    def dislikes_count_display(self, obj):
        return obj.dislikes_count
    dislikes_count_display.short_description = "👎 دیسلایک‌ها"

    @admin.action(description="✔ تایید انتخاب‌شده‌ها")
    def approve_selected_comments(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} کامنت تایید شد ✅")

    @admin.action(description="❌ عدم تایید انتخاب‌شده‌ها")
    def unapprove_selected_comments(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"{updated} کامنت لغو تایید شد ❌")

    @admin.action(description="🗑 حذف فقط کامنت‌های تایید نشده")
    def delete_unapproved(self, request, queryset):
        to_delete = queryset.filter(is_approved=False)
        count = to_delete.count()
        to_delete.delete()
        self.message_user(request, f"{count} کامنت تایید نشده حذف شد 🗑")
