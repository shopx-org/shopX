# core/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.contenttypes.models import ContentType
from .models import Comment
from .forms import CommentForm


@login_required
def add_comment(request, app_label, model_name, object_id):
    content_type = get_object_or_404(ContentType, app_label=app_label, model=model_name)
    model_class = content_type.model_class()
    obj = get_object_or_404(model_class, id=object_id)

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.content_object = obj

            parent_id = form.cleaned_data.get('parent_id')
            parent_comment = None

            if parent_id:
                try:
                    parent_comment = Comment.objects.get(id=parent_id)
                    # جلوگیری از پاسخ به پاسخ (فقط 1 سطح)
                    if parent_comment.parent:
                        parent_comment = parent_comment.parent
                    comment.parent = parent_comment
                except Comment.DoesNotExist:
                    comment.parent = None

            comment.save()
            return redirect(obj.get_absolute_url())

    return redirect(obj.get_absolute_url())
