# orders/urls.py
from django.urls import path
from . import views

app_name = "orders"


urlpatterns = [
    path("payment/start/<int:order_id>/", views.payment_start, name="payment_start"),
    path("payment/callback/", views.payment_callback, name="payment_callback"),  # 👈 این
    path("payment/success/<int:order_id>/", views.payment_success, name="payment_success"),
    path("payment/failed/<int:order_id>/", views.payment_failed, name="payment_failed"),
]