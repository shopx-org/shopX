from decimal import Decimal
from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()
_EN_TO_FA = str.maketrans("0123456789,.-", "۰۱۲۳۴۵۶۷۸۹٬٫-")

@register.filter
def fa_digits(value):
    if value is None: return ""
    return f"{value}".translate(_EN_TO_FA)

@register.filter
def fa_price(value):
    if value in ("", None): return ""
    try:
        n = int(Decimal(str(value)))
        s = intcomma(n)  # 1,234,567
    except Exception:
        return fa_digits(value)
    return s.translate(_EN_TO_FA)  # ۱٬۲۳۴٬۵۶۷
