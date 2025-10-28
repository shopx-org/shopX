from django.urls import path
from . import views
from shipping.views import AddressesView

app_name = 'dashboards'
urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('personal-info/', views.PersonalInfoView.as_view(), name='personal_info'),
    path("change-phone-otp/", views.ChangePhoneOtpView.as_view(), name="change_phone_otp"),
    path("addresses/", AddressesView.as_view(), name="addresses"),
]