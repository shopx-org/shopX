from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Campaign, Coupon

def _wipe():
    try: cache.delete_pattern("promos:active:*")
    except Exception: pass  # LocMem این متد را ندارد؛ TTL کوتاه کافیست

@receiver([post_save, post_delete], sender=Campaign)
def _camp_changed(*_, **__): _wipe()

@receiver([post_save, post_delete], sender=Coupon)
def _coupon_changed(*_, **__): _wipe()
