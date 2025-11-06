# core/views.py
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.html import strip_tags
from django.http import JsonResponse

from .models import Comment
from .forms import CommentForm


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@login_required
@require_POST
def add_comment(request, app_label, model_name, object_id):

    # 🔹 تشخیص اینکه درخواست Ajax است یا خیر
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    # ✅ فقط اجازه روی مدل‌های مشخص
    ALLOWED_MODELS = {
        ("products", "product"),
    }
    if (app_label, model_name) not in ALLOWED_MODELS:
        if is_ajax:
            return JsonResponse({"status": "error", "message": "دسترسی مجاز نیست."}, status=403)
        raise PermissionDenied("No access to add comment here.")

    # ✅ دریافت فرم
    form = CommentForm(request.POST)
    if not form.is_valid():
        msg = list(form.errors.values())[0]
        if is_ajax:
            return JsonResponse({"status": "error", "message": msg}, status=400)
        messages.error(request, msg, extra_tags="comment")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    # ✅ یافتن مدل هدف
    content_type = get_object_or_404(ContentType, app_label=app_label, model=model_name)
    obj = get_object_or_404(content_type.model_class(), id=object_id)

    # ✅ گرفتن متن و پاک‌سازی
    raw_text = form.cleaned_data["text"]
    cleaned_text = strip_tags(raw_text).strip()

    if len(cleaned_text) < 3:
        error = "نظر باید حداقل ۳ کاراکتر معتبر داشته باشد."
        if is_ajax:
            return JsonResponse({"status": "error", "message": error}, status=400)
        messages.error(request, error, extra_tags="comment")
        return redirect(obj.get_absolute_url())

    # ✅ فیلتر لینک و کلمات ممنوعه
    BAD_WORDS = ["http://", "https://", "www.", ".com", ".ir", "telegram", "sex", "porn", "adult"]
    if any(bad in cleaned_text.lower() for bad in BAD_WORDS):
        error = "استفاده از لینک و تبلیغات در نظرها مجاز نیست."
        if is_ajax:
            return JsonResponse({"status": "error", "message": error}, status=400)
        messages.error(request, error, extra_tags="comment")
        return redirect(obj.get_absolute_url())

    # ✅ محدودیت سرعت (ضد اسپم)
    ip = get_client_ip(request)
    recent_count = Comment.objects.filter(
        ip_address=ip,
        created_at__gte=timezone.now() - timezone.timedelta(seconds=8)
    ).count()

    if recent_count >= 3:
        error = "ارسال بیش از حد مجاز. چند لحظه دیگر تلاش کنید."
        if is_ajax:
            return JsonResponse({"status": "error", "message": error}, status=429)
        messages.error(request, error, extra_tags="comment")
        return redirect(obj.get_absolute_url())

    # ✅ جلوگیری از ثبت نظر تکراری
    duplicate = Comment.objects.filter(
        user=request.user,
        text=cleaned_text,
        created_at__gte=timezone.now() - timezone.timedelta(minutes=2)
    ).exists()

    if duplicate:
        error = "همین نظر را قبلاً ارسال کرده‌اید."
        if is_ajax:
            return JsonResponse({"status": "error", "message": error}, status=400)
        messages.error(request, error, extra_tags="comment")
        return redirect(obj.get_absolute_url())

    # ✅ بررسی صحت parent (فقط کامنت‌های تایید شده قابل پاسخ هستند)
    parent_id = form.cleaned_data.get("parent_id")
    parent_obj = None

    if parent_id:
        parent_obj = Comment.objects.filter(
            id=parent_id,
            content_type=content_type,
            object_id=object_id,
            is_approved=True
        ).first()

        if not parent_obj:
            error = "پاسخ نامعتبر است."
            if is_ajax:
                return JsonResponse({"status": "error", "message": error}, status=400)
            messages.error(request, error, extra_tags="comment")
            return redirect(obj.get_absolute_url())

    # ✅ ذخیره کامنت — فقط بعد تایید ادمین نمایش داده شود
    try:
        comment = Comment(
            user=request.user,
            content_object=obj,
            text=cleaned_text,
            parent=parent_obj,
            ip_address=ip,
            is_approved=False,   # ⛔ فقط بعد تایید نمایش داده شود
        )
        comment.full_clean()
        comment.save()

        success = "نظر شما با موفقیت ثبت شد و پس از تایید مدیریت نمایش داده می‌شود."

        if is_ajax:
            return JsonResponse({"status": "success", "message": success})

        messages.success(request, success, extra_tags="comment")

    except ValidationError:
        error = "مقادیر ارسالی معتبر نیست."
        if is_ajax:
            return JsonResponse({"status": "error", "message": error}, status=400)
        messages.error(request, error, extra_tags="comment")

    except Exception:
        error = "خطایی رخ داد، لطفاً دوباره تلاش کنید."
        if is_ajax:
            return JsonResponse({"status": "error", "message": error}, status=500)
        messages.error(request, error, extra_tags="comment")

    return redirect(obj.get_absolute_url())
