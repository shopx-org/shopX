# products/templatetags/specs.py
from django import template
from products.models import ProductAttributeValue

register = template.Library()

def _get_attr_value(product, code: str) -> str:
    """
    مقدار نمایشی ویژگی از روی attribute.code
    از prefetch: product.attr_values_list استفاده می‌کند.
    """
    items = getattr(product, "attr_values_list", None)
    pav = None
    if items is not None:
        for v in items:
            if getattr(v.attribute, "code", None) == code:
                pav = v
                break
    else:
        pav = (ProductAttributeValue.objects
               .select_related("attribute", "value_choice")
               .prefetch_related("values_multi")
               .filter(product_id=product.id, attribute__code=code)
               .first())
    if not pav:
        return ""

    kind = getattr(pav.attribute, "kind", "text")
    if kind == "text":
        return pav.value_text or ""
    if kind == "int":
        return "" if pav.value_int is None else str(pav.value_int)
    if kind == "decimal":
        return "" if pav.value_decimal is None else ("{:g}".format(float(pav.value_decimal)))
    if kind == "bool":
        return "بله" if pav.value_bool else "خیر"
    if kind == "choice":
        return pav.value_choice.label if pav.value_choice else ""
    if kind == "multi":
        return "، ".join([c.label for c in pav.values_multi.all()])
    return ""

def _lower(s): return (s or "").lower()

def _category_group(product) -> str:
    c = getattr(product, "category", None)
    name = _lower(getattr(c, "name", ""))
    slug = _lower(getattr(c, "slug", ""))
    if any(k in name or k in slug for k in ["mobile", "phone", "موبایل", "گوشی"]):
        return "mobile"
    if any(k in name or k in slug for k in ["laptop", "notebook", "لپ", "نوت"]):
        return "laptop"
    return "generic"

@register.inclusion_tag("products/partials/specs_bar.html")
def product_specs_bar(product):
    """
    نوار مشخصات کارت محصول.
    اگر کد ویژگی‌ها فرق می‌کند، فقط mapping را با کدهای خودت هماهنگ کن.
    """
    group = _category_group(product)
    if group == "mobile":
        mapping = [
            ("battery",      "mAh",  "battery"),
            ("camera_mp",    "MP",   "camera"),
            ("display_size", "اینچ", "display"),
            ("storage",      "GB",   "storage"),
        ]
    elif group == "laptop":
        mapping = [
            ("cpu",          "",     "cpu"),
            ("ram",          "GB",   "ram"),
            ("storage",      "GB",   "storage"),
            ("display_size", "اینچ", "display"),
        ]
    else:
        mapping = [
            ("ram",          "GB",   "ram"),
            ("storage",      "GB",   "storage"),
            ("display_size", "اینچ", "display"),
            ("battery",      "mAh",  "battery"),
        ]

    items = []
    for code, unit, icon in mapping:
        val = _get_attr_value(product, code)
        if val:
            items.append({"code": code, "value": val, "unit": unit, "icon": icon})
    return {"items": items[:4]}


