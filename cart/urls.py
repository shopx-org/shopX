from django.urls import path
from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_detail, name="cart_detail"),

    # add
    path("add/<int:product_id>/", views.cart_add, name="cart_add"),

    # update qty
    path("update-qty/<int:product_id>/<int:variant_id>/", views.cart_update_qty, name="cart_update_qty"),
    path("update-qty/<int:product_id>/", views.cart_update_qty_no_variant, name="cart_update_qty_no_variant"),

    # remove
    path("remove/<int:product_id>/<int:variant_id>/", views.cart_remove, name="cart_remove"),
    path("remove/<int:product_id>/", views.cart_remove_no_variant, name="cart_remove_no_variant"),

    # coupon & clear
    path("set-coupon/", views.cart_set_coupon, name="cart_set_coupon"),
    path("clear/", views.cart_clear, name="cart_clear"),
    path("toggle-service/<int:product_id>/<int:variant_id>/<int:service_id>/", views.cart_toggle_service,
         name="cart_toggle_service"),
    path("toggle-service/<int:product_id>/<int:service_id>/", views.cart_toggle_service_no_variant,
         name="cart_toggle_service_no_variant"),
    path("set-coupon/", views.cart_set_coupon, name="cart_set_coupon"),
    path("api/header-summary/", views.cart_header_summary, name="cart_header_summary"),
]

