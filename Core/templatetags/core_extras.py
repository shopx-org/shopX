# Core/templatetags/core_extras.py
from django import template
from django.contrib.contenttypes.models import ContentType

register = template.Library()

@register.filter
def user_vote_for(comment, user):
    """
    برمی‌گردونه که کاربر فعلی روی این کامنت چه رأیی داده (1 برای لایک، -1 برای دیسلایک، 0 برای هیچ‌کدام)
    """
    try:
        return comment.user_vote(user)
    except Exception:
        return 0


@register.filter
def content_type_id(obj):
    """
    برای گرفتن content_type.id از هر آبجکت
    """
    try:
        return ContentType.objects.get_for_model(obj).id
    except Exception:
        return None