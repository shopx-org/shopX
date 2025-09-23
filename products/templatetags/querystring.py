# products/templatetags/querystring.py
from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    """
    استفاده:
    <a href="?{% querystring sort='new' %}">جدیدترین</a>

    کل پارامترهای GET فعلی را نگه می‌دارد و مقادیر جدید را آپدیت می‌کند.
    """
    request = context["request"]
    q = request.GET.copy()
    for k, v in kwargs.items():
        if v is None:
            q.pop(k, None)
        else:
            q[k] = v
    return q.urlencode()



@register.filter
def get_item(d, key):
    """
    گرفتن مقدار یک کلید از دیکشنری در تمپلیت.
    اگر نبود، لیست خالی برمی‌گرداند تا 'in' خطا ندهد.
    """
    if isinstance(d, dict):
        return d.get(key, [])
    return []

@register.filter
def mul(a, b):
    """
    ضرب ساده برای محاسبات درصد و ...
    """
    try:
        return float(a) * float(b)
    except Exception:
        return 0