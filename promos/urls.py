from django.urls import path
from . import views

app_name = "promos"
urlpatterns = [
    path("apply-coupon/", views.apply_coupon, name="promos_apply"),
    path("remove-coupon/<str:code>/", views.remove_coupon, name="promos_remove"),
    path("quote/", views.quote_pricing, name="promos_quote"),  # NEW
]