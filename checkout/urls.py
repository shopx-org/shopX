# checkout/urls.py
from django.urls import path
from . import views
app_name = "checkout"

urlpatterns = [
    path("", views.checkout_start, name="start"),
    path("address/", views.checkout_address, name="address"),
    path("review/", views.checkout_review, name="review"),
    path("confirm/", views.checkout_confirm, name="confirm"),
]
