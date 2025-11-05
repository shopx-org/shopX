# core/views.py
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required
from .models import Comment
from .forms import CommentForm


# گرفتن IP واقعی کاربر
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@login_required
@require_POST
def add_comment(request, app_label, model_name, object_id):

    ALLOWED_MODELS = {
        ("products", "product"),
    }
    if (app_label, model_name) not in ALLOWED_MODELS:
        messages.error(request, "اجازه ثبت نظر برای این بخش وجود ندارد.")
        return redirect(request.META.get('HTTP_REFERER', '/'))


    form = CommentForm(request.POST)
    if not form.is_valid():
        messages.error(request, list(form.errors.values())[0])
        return redirect(request.META.get('HTTP_REFERER', '/'))


    content_type = get_object_or_404(ContentType, app_label=app_label, model=model_name)
    model_class = content_type.model_class()
    obj = get_object_or_404(model_class, id=object_id)

    # 🔹 IP ضد اسپم
    ip = get_client_ip(request)
    recent_ip_comments = Comment.objects.filter(
        ip_address=ip,
        created_at__gte=timezone.now() - timezone.timedelta(seconds=10)
    ).count()

    if recent_ip_comments >= 3:
        messages.error(request, "ارسال بیش از حد مجاز. لطفاً چند لحظه بعد تلاش کنید.")
        return redirect(obj.get_absolute_url())

    # 🔹 کلمات ممنوعه
    BAD_WORDS = ["http://", "https://", "telegram", "porn", "adult"]
    text = form.cleaned_data.get("text", "").lower()
    for bad in BAD_WORDS:
        if bad in text:
            messages.error(request, "کامنت شما شامل کلمات غیرمجاز است.")
            return redirect(obj.get_absolute_url())

    # 🔹 ساخت کامنت
    comment = form.save(commit=False)
    comment.user = request.user
    comment.content_object = obj
    comment.ip_address = ip

    # 🔹 ریپلای فقط یک سطح
    parent_id = form.cleaned_data.get('parent_id')
    if parent_id:
        parent_comment = Comment.objects.filter(
            id=parent_id,
            content_type=content_type,
            object_id=object_id,
            is_active=True
        ).first()

        if parent_comment:
            comment.parent = parent_comment.parent or parent_comment

    # 🔹 محدودیت ارسال زیاد توسط کاربر
    last_comment = Comment.objects.filter(user=request.user).order_by('-created_at').first()
    if last_comment and (timezone.now() - last_comment.created_at).total_seconds() < 10:
        messages.error(request, "خیلی سریع نظر ارسال کردید. کمی صبر کنید.")
        return redirect(obj.get_absolute_url())

    # 🔹 Moderation
    comment.is_approved = False
    comment.save()

    messages.success(request, "نظر شما ثبت شد و پس از تایید نمایش داده می‌شود.")
    return redirect(obj.get_absolute_url())
