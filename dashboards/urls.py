from django.urls import  path
from .views import *

app_name = 'dashboards'
urlpatterns = [
    path('dashboard/', user_dashboard, name='dashboard'),
    path('user_profile/', user_profile, name='user_profile'),

]