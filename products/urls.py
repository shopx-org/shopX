from django.urls import path
from .views import  ProductListView, CategoryProductListView, ProductDetailView
from products import  views


app_name = 'products'
urlpatterns = [
    path("products/", ProductListView.as_view(), name='product_list'),
    # دسته با مسیر درختی (electronics/mobile/ ...)
    path("c/<path:path>/", CategoryProductListView.as_view(), name='category'),
    path("p/<slug:slug>/", ProductDetailView.as_view(), name='product_detail'),

    # path('product/', views.product_detail_view, name='product_details'),
]




