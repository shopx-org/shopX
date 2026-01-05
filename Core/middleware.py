# core/middleware.py
from django.conf import settings
from django.shortcuts import render

class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, "MAINTENANCE_MODE", False):
            # اجازه بده ادمین‌ها رد شن
            if request.user.is_authenticated and request.user.is_staff:
                return self.get_response(request)

            # اجازه بده استاتیک/مدیا لود بشه (برای اینکه صفحه 503 بهم نریزه)
            if request.path_info.startswith("/static/") or request.path_info.startswith("/media/"):
                return self.get_response(request)

            return render(request, "home/503.html", status=503)

        return self.get_response(request)
