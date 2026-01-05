from django.urls import path
from . import views
from .views import *

app_name = 'home'
urlpatterns = [
    path('', Home.as_view(), name='home'),
    path("terms/", Terms.as_view(), name="terms"),
    path('page404/', views.page404, name='page_404'),
    path("page500/", views.page500, name="page_500"),
    path("page403/", views.page403, name="page_403"),
    path("page400/", views.page400, name="page_400"),
    path("page504/", views.page504, name="page_504"),
    path("page503/", views.page503, name="page_503"),
    path("privacy/", views.privacy_policy, name="privacy"),
]
