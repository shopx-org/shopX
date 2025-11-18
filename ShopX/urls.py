# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("home.urls")),
    path("", include(("products.urls", "products"), namespace="products")),

    path("account/", include(("account.urls", "account"), namespace="account")),
    path("promos/", include("promos.urls")),
    path("cart/", include("cart.urls")),
    path("dashboard/", include(("dashboards.urls", "dashboards"), namespace="dashboards")),
    path("shipping/", include(("shipping.urls", "shipping"))),
    path('core/', include('Core.urls', namespace='core')),

    path("checkout/",include(("checkout.urls", "checkout"), namespace="checkout")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

