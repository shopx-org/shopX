# core/forms.py
from django import forms
from .models import Comment

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
        text = self.cleaned_data.get('text', '').strip()
        if not text:
            raise forms.ValidationError("متن نظر نمی‌تواند خالی باشد.")
        if len(text) < 3:
            raise forms.ValidationError("لطفاً نظر خود را کامل‌تر بنویسید (حداقل ۳ کاراکتر).")
        return text