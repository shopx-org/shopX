from django import forms
from decimal import Decimal
from .models import Action, Rule
from products.models import Product, Category


class ActionForm(forms.ModelForm):
    class Meta:
        model = Action
        fields = "__all__"

    def clean(self):
        c = super().clean()
        kind, value, cap, scope = c.get("kind"), c.get("value"), c.get("cap"), c.get("scope")
        if kind == "percent_off":
            if value is None or value <= 0 or value > Decimal("100"):
                raise forms.ValidationError("درصد باید بین 0 و 100 باشد.")
        if kind == "amount_off":
            if value is None or value <= 0:
                raise forms.ValidationError("مبلغ تخفیف باید > 0 باشد.")
        if scope == "shipping" and kind == "percent_off":
            raise forms.ValidationError("درصد روی ارسال پشتیبانی نمی‌شود.")
        if cap is not None and cap < 0:
            raise forms.ValidationError("سقف تخفیف نمی‌تواند منفی باشد.")
        return c

class RuleForm(forms.ModelForm):
    products = forms.ModelMultipleChoiceField(Product.objects.all(), required=False)
    categories = forms.ModelMultipleChoiceField(Category.objects.all(), required=False)
    class Meta:
        model = Rule
        fields = "__all__"

    def clean(self):
        c = super().clean()
        kind = c.get("kind")
        if kind == "product_in":
            ids = list(self.cleaned_data["products"].values_list("id", flat=True))
            if not ids:
                raise forms.ValidationError("محصولات را انتخاب کنید.")
            c["payload"] = {"product_ids": ids}
        elif kind == "category_in":
            ids = list(self.cleaned_data["categories"].values_list("id", flat=True))
            if not ids:
                raise forms.ValidationError("دسته‌ها را انتخاب کنید.")
            c["payload"] = {"category_ids": ids}
        # بقیه‌ی ruleها مثل قبل
        return c
