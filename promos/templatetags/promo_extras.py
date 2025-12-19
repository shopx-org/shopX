from django import template

register = template.Library()

@register.filter
def pick_slot(banners, slot):
    for b in (banners or []):
        if getattr(b, "slot", "") == slot:
            return b
    return None