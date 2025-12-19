from django.contrib import admin
from .models import TermsAndConditions
from .models import HomeVideoBanner



admin.site.register(TermsAndConditions)


@admin.register(HomeVideoBanner)
class HomeVideoBannerAdmin(admin.ModelAdmin):
    list_display = ('title_big', 'is_active', 'updated_at')
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        return not HomeVideoBanner.objects.exists()
