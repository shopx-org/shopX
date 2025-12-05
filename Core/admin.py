from django.contrib import admin
from django.utils.html import format_html
from .models import *
from django.contrib.contenttypes.models import ContentType
from ckeditor.widgets import CKEditorWidget
from django import forms


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



@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")
    list_filter = ("user", "product", "created_at")
    search_fields = ("user__username", "user__email", "product__title", "product__id")
    readonly_fields = ("created_at",)

    ordering = ("-created_at",)



# فرم ادمین با CKEditor برای اعضای تیم
class TeamMemberAdminForm(forms.ModelForm):
    bio = forms.CharField(widget=CKEditorWidget())

    class Meta:
        model = TeamMember
        fields = '__all__'

# Inline اعضای تیم
class TeamMemberInline(admin.StackedInline):
    model = TeamMember
    form = TeamMemberAdminForm
    extra = 1
    fields = ('name', 'role', 'image', 'bio', 'facebook', 'twitter', 'instagram')
    verbose_name = "عضو تیم"
    verbose_name_plural = "اعضای تیم"
    formfield_overrides = {
        TeamMember.bio: {'widget': CKEditorWidget(config_name='default', attrs={'cols': 80, 'rows': 10})},
    }

# Inline برندها
class BrandInline(admin.TabularInline):
    model = Brand
    extra = 1
    fields = ('name', 'logo', 'url')

# فرم ادمین About با متا فیلدها
class AboutAdminForm(forms.ModelForm):
    class Meta:
        model = About
        fields = '__all__'
        widgets = {
            'vision_text': CKEditorWidget(),
            'mission_text': CKEditorWidget(),
            'who_text': CKEditorWidget(),
            'brands_text': CKEditorWidget(),
        }

# ادمین درباره ما
@admin.register(About)
class AboutAdmin(admin.ModelAdmin):
    form = AboutAdminForm
    readonly_fields = ('header_image_preview', 'who_image_front_preview', 'who_image_back_preview')


    def header_image_preview(self, obj):
        if obj.header_image:
            return format_html('<img src="{}" style="max-width:150px;">', obj.header_image.url)
        return "-"
    header_image_preview.short_description = "پیش‌نمایش هدر"

    def who_image_front_preview(self, obj):
        if obj.who_image_front:
            return format_html('<img src="{}" style="max-width:100px;">', obj.who_image_front.url)
        return "-"
    who_image_front_preview.short_description = "پیش‌نمایش تصویر جلو"

    def who_image_back_preview(self, obj):
        if obj.who_image_back:
            return format_html('<img src="{}" style="max-width:100px;">', obj.who_image_back.url)
        return "-"
    who_image_back_preview.short_description = "پیش‌نمایش تصویر عقب"


    inlines = [BrandInline, TeamMemberInline]
    list_display = ('title', 'meta_title', 'meta_description')
    fieldsets = (
        (None, {
            'fields': ('title', 'header_image')
        }),
        ('دید و ماموریت', {
            'fields': ('vision_title', 'vision_text', 'mission_title', 'mission_text')
        }),
        ('ما که هستیم', {
            'fields': ('who_title', 'who_lead', 'who_text', 'who_image_front', 'who_image_front_preview',
                       'who_image_back', 'who_image_back_preview')
        }),
        ('متا SEO', {
            'fields': ('meta_title', 'meta_description'),
            'description': 'برای سئو: طول متا تایتل ~60 کاراکتر، طول متا دیسکریپشن ~160 کاراکتر'
        }),
    )
