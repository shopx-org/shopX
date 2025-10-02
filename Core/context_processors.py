# products/context_processors.py
from django.db.models import Prefetch
from products.models import Category

# ───────────────── helpers
def _c2_qs():
    """سطح سوم: فرزندانِ سطح دوم (برای ul داخلی)"""
    return Category.objects.active().ordered()

def _c1_qs():
    """سطح دوم: فرزندانِ ریشه‌ها + prefetchِ سطح سوم روی همان children"""
    return (
        Category.objects.active()
        .ordered()
        .prefetch_related(
            Prefetch("children", queryset=_c2_qs())  # c1.children آماده است
        )
    )

_C1_PREFETCH = Prefetch(
    "children",
    queryset=_c1_qs(),
    to_attr="c1_list",  # لیست سطح دوم روی آبجکتِ ریشه با نام c1_list
)

# ───────────────── exposed processors
def top_categories(request):
    """
    برای مِگا‌منو:
    - ریشه‌ها
    - سطح دوم در to_attr = c1_list
    - سطح سوم در c1.children
    """
    roots = (
        Category.objects.active()
        .filter(parent__isnull=True)
        .ordered()
        .prefetch_related(_C1_PREFETCH)
    )
    return {"top_categories": roots}

def header_categories(request):
    """
    اختیاری برای هدر ساده (بدون to_attr):
    ریشه‌ها + دو سطح بعدی با همان نام پیش‌فرض children
    """
    qs = (
        Category.objects.active()
        .filter(parent__isnull=True)
        .ordered()
        .prefetch_related(
            "children",
            "children__children",
        )
    )
    return {"header_categories": qs[:12]}
