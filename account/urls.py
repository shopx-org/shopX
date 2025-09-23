# from django.urls import path
# from . import views
#
# app_name = "account"
# urlpatterns = [
#     path('password-login/', views.PasswordLoginView.as_view(), name='password_login'),
#     path('otp-login/', views.OtpLoginView.as_view(), name='otp_login'),
#     path('check-otp/', views.CheckOtpView.as_view(), name='check_otp'),
#     path('logout/', views.LogoutView.as_view(), name='logout'),
#     path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
#     path('reset-verify/', views.ResetVerifyOtpView.as_view(), name='reset_verify'),
#     path('set-password/', views.SetPasswordView.as_view(), name='set_password'),
# ]
# account/urls.py
from django.urls import path
from . import views

app_name = "account"

urlpatterns = [
    path("password-login/", views.PasswordLoginView.as_view(), name="password_login"),
    path("otp-login/", views.OtpLoginView.as_view(), name="otp_login"),
    path("check-otp/", views.CheckOtpView.as_view(), name="check_otp"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("forgot-password/", views.ForgotPasswordView.as_view(), name="forgot_password"),
    path("reset-verify/", views.ResetVerifyOtpView.as_view(), name="reset_verify"),
    path("set-password/", views.SetPasswordView.as_view(), name="set_password"),
]
