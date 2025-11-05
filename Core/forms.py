# core/forms.py
from django import forms
from django.utils.html import strip_tags, escape
import re
from .models import Comment


BAD_PATTERNS = [
    r"<script.*?>.*?</script>",
    r"javascript:",
    r"onerror\s*=",
    r"onload\s*=",
]

class CommentForm(forms.ModelForm):
    parent_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Comment
        fields = ['text', 'parent_id']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'نظر خود را بنویسید...',
            }),
        }
        labels = {'text': ''}

    def clean_text(self):
        text: str = self.cleaned_data.get('text', '').strip()

        # خالی نباشه
        if not text:
            raise forms.ValidationError("متن نظر نمی‌تواند خالی باشد.")

        # حداقل طول
        if len(text) < 3:
            raise forms.ValidationError("لطفاً نظر خود را کامل‌تر بنویسید (حداقل ۳ کاراکتر).")

        # جلوگیری از حملات script و JS
        stripped = strip_tags(text)        # حذف تگ‌های HTML
        safe_text = escape(stripped)       # تبدیل < > " '

        # الگوهای خطرناک
        for p in BAD_PATTERNS:
            if re.search(p, text, re.IGNORECASE):
                raise forms.ValidationError("محتوای نظر معتبر نیست.")

        return safe_text
