from django.urls import path
from . import views

app_name = 'dashboards'
urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('personal-info/', views.PersonalInfoView.as_view(), name='personal_info'),
]