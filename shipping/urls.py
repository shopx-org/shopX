from django.urls import path
from . import views

app_name = 'shipping'

urlpatterns = [
    # path("set-default/", views.set_default_address, name="set_default_address"),
    path('set-default-address/', views.set_default_address, name='set_default_address'),
]
