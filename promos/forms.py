# promos/forms.py
from django import forms
from .models import Rule
from products.models import Category  # اگر مسیرت چیز دیگری است، اصلاح کن

class RuleAdminForm(forms.ModelForm):
    # فیلدهای انسانی‌تر برای ادمین
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label="دسته‌ها",
        help_text="برای نوع «عضویت در دسته» استفاده می‌شود.",
    )
    threshold = forms.DecimalField(
        required=False,
        label="حداقل مبلغ سبد",
        help_text="برای نوع «حداقل مبلغ سبد» استفاده می‌شود.",
    )
    qty = forms.IntegerField(
        required=False,
        label="حداقل تعداد یک سطر",
        help_text="برای نوع «حداقل تعداد یک سطر» استفاده می‌شود.",
        min_value=1,
    )

    class Meta:
        model = Rule
        # payload را اینجا نمی‌آوریم؛ پشت‌صحنه پر می‌کنیم
        fields = ("kind", "categories", "threshold", "qty")

    def save(self, commit=True):
        obj = super().save(commit=False)
        kind = self.cleaned_data.get("kind")

        # به ازای هر نوع، payload مناسب را بساز
        if kind == "category_in":
            cats = self.cleaned_data.get("categories")
            obj.payload = {
                "category_ids": list(cats.values_list("id", flat=True)) if cats else []
            }

        elif kind == "cart_min_total":
            thr = self.cleaned_data.get("threshold") or 0
            obj.payload = {"threshold": str(thr)}

        elif kind == "qty_at_least":
            q = self.cleaned_data.get("qty") or 1
            obj.payload = {"qty": int(q)}

        # بقیه‌ی انواع (product_in, variant_in, brand_in) را فعلاً دست‌نخورده می‌گذاریم
        # و اگر خواستی بعداً همین کار را برایشان هم تکرار می‌کنیم.

        if commit:
            obj.save()
        return obj
