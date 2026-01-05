from django.urls import path
from .views import *
from products import views
from products.api_views import ProductListAPI


app_name = 'products'
urlpatterns = [
    path("products/", ProductListView.as_view(), name='product_list'),
    # دسته با مسیر درختی (electronics/mobile/ ...)
    path("c/<path:path>/", CategoryProductListView.as_view(), name='category'),
    path("p/<path:slug>/", ProductDetailView.as_view(), name='product_detail'),
    path("p/<path:slug>/variant-price/", VariantPriceView.as_view(), name="variant-price"),
    path("compare/add/<int:product_id>/", add_to_compare, name="add_to_compare"),
    path("compare/remove/<int:product_id>/", remove_from_compare, name="remove_from_compare"),
    path("compare/", compare_list, name="compare_list"),
    path("api/products/", ProductListAPI.as_view(), name="product_list_api"),
    
    # path('product/', views.product_detail_view, name='product_details'),
]




