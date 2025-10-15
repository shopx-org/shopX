# promos/management/commands/promos_cache_clear.py
from django.core.management.base import BaseCommand
from django.core.cache import cache

class Command(BaseCommand):
    help = "Clear promos active-campaigns cache (optionally for a specific channel)."

    def add_arguments(self, parser):
        parser.add_argument("--channel", type=str, default=None, help="e.g. web")

    def handle(self, *args, **kwargs):
        channel = kwargs.get("channel")
        try:
            if channel:
                deleted = cache.delete_pattern(f"promos:active:{channel}")
            else:
                deleted = cache.delete_pattern("promos:active:*")
            self.stdout.write(self.style.SUCCESS(f"Promos cache cleared via delete_pattern (deleted~{deleted})."))
            return
        except Exception:
            # Fallback برای LocMem
            if channel:
                cache.delete(f"promos:active:{channel}")
            else:
                # اگر کانال‌ها محدودند، دستی پاک کن؛ در غیر این صورت cache.clear() در DEV
                try:
                    for ch in ("web", "app", "pos"):
                        cache.delete(f"promos:active:{ch}")
                except Exception:
                    cache.clear()
            self.stdout.write(self.style.SUCCESS("Promos cache cleared (fallback)."))
