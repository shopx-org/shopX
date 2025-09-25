# products/context_processors.py
from django.db.models import Prefetch
from products.models import Category

def prefetch_cat_tree():
    return Prefetch(
        "children",
        queryset=Category.objects.active().ordered().prefetch_related(
            Prefetch("children", queryset=Category.objects.active().ordered())
        ),
        to_attr="c1_list",  # سطح دوم روی آبجکت به اسم c1_list
    )

def top_categories(request):
    """برای مگامنو: ریشه‌ها + سطح ۲ (c1_list) + سطح ۳ (children)"""
    try:
        roots = (
            Category.objects.active()
            .filter(parent__isnull=True)
            .ordered()
            .prefetch_related(prefetch_cat_tree())
        )
    except Exception:
        roots = Category.objects.none()
    return {"top_categories": roots}

def header_categories(request):
    """اختیاری: یک لیست ساده برای هدر (بدون c1_list)، کلید جدا تا تداخلی با مگامنو نداشته باشه."""
    qs = (
        Category.objects.active()
        .filter(parent__isnull=True)
        .ordered()
        .prefetch_related("children__children")
    )
    return {"header_categories": qs[:12]}
