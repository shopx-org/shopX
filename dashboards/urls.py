from django.urls import path
from . import views

app_name = 'dashboards'
urlpatterns = [
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/personal-info/', views.PersonalInfoView.as_view(), name='personal_info'),
]