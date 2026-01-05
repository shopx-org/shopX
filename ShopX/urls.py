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
    path("orders/", include("orders.urls")),
    path("search/", include("search.urls", namespace="search")),
    path("faq/", include(("faq.urls", "faq"), namespace="faq")),
    path("contact/", include("contact.urls")),
    # path("jalali_date/", include("jalali_date.urls")),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


handler404 = "home.views.page404"
handler500 = "home.views.page500"
handler403 = "home.views.page403"
handler400 = "home.views.page400"
