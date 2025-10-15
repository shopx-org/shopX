from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.timezone import now
from datetime import timedelta
from decimal import Decimal

from .models import Campaign, Rule, Action


from .forms import ActionForm, RuleForm
class RuleInline(admin.TabularInline):
    model = Rule
    form = RuleForm
    extra = 0
class ActionInline(admin.TabularInline):
    model = Action
    form = ActionForm
    extra = 0
# promos/admin.py


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name","is_active","starts_at","ends_at","priority","exclusive","channel")
    inlines = []  # اگر RuleInline/ActionInline داری، اینجا بگذار

    def get_urls(self):
        urls = super().get_urls()
        my = [
            path("quick-create/product/", self.admin_site.admin_view(self.quick_create_product), name="promos_quick_product"),
            path("quick-create/category/", self.admin_site.admin_view(self.quick_create_category), name="promos_quick_category"),
        ]
        return my + urls

    def quick_create_product(self, request):
        """
        /admin/promos/campaign/quick-create/product/?product_id=123&percent=10&days=7&channel=web
        """
        try:
            pid = int(request.GET.get("product_id"))
            percent = Decimal(str(request.GET.get("percent", "10")))
            days = int(request.GET.get("days", 7))
            channel = request.GET.get("channel", "web")
        except Exception:
            messages.error(request, "پارامترها نامعتبرند.")
            return redirect(reverse("admin:promos_campaign_changelist"))

        c = Campaign.objects.create(
            name=f"تخفیف {percent}% برای محصول {pid}",
            starts_at=now(),
            ends_at=now() + timedelta(days=days),
            is_active=True,
            priority=10,
            exclusive=False,
            channel=channel,
        )
        Rule.objects.create(campaign=c, kind="product_in", payload={"product_ids":[pid]})
        Action.objects.create(campaign=c, kind="percent_off", scope="line", value=percent)

        messages.success(request, "کمپین ساخته شد.")
        return redirect(reverse("admin:promos_campaign_change", args=[c.id]))

    def quick_create_category(self, request):
        """
        /admin/promos/campaign/quick-create/category/?category_id=55&percent=15&days=7&channel=web
        """
        try:
            cid = int(request.GET.get("category_id"))
            percent = Decimal(str(request.GET.get("percent", "10")))
            days = int(request.GET.get("days", 7))
            channel = request.GET.get("channel", "web")
        except Exception:
            messages.error(request, "پارامترها نامعتبرند.")
            return redirect(reverse("admin:promos_campaign_changelist"))

        c = Campaign.objects.create(
            name=f"تخفیف {percent}% دسته {cid}",
            starts_at=now(),
            ends_at=now() + timedelta(days=days),
            is_active=True,
            priority=10,
            exclusive=False,
            channel=channel,
        )
        Rule.objects.create(campaign=c, kind="category_in", payload={"category_ids":[cid]})
        Action.objects.create(campaign=c, kind="percent_off", scope="line", value=percent)

        messages.success(request, "کمپین ساخته شد.")
        return redirect(reverse("admin:promos_campaign_change", args=[c.id]))
