from django.urls import path
from . import views
from shipping.views import AddressesView
from .views import *

app_name = 'dashboards'
urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('personal-info/', views.PersonalInfoView.as_view(), name='personal_info'),
    path("change-phone-otp/", views.ChangePhoneOtpView.as_view(), name="change_phone_otp"),
    path("addresses/", AddressesView.as_view(), name="addresses"),
    path('my-comments/', views.UserCommentsView.as_view(), name='user_comments'),
    path('delete-comment/<int:pk>/', DeleteCommentAjaxView.as_view(), name='delete_comment'),

]