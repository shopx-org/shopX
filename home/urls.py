from django.urls import path
from . import views
from .views import *

app_name = 'home'
urlpatterns = [
    path('', Home.as_view(), name='home'),
    path("terms/", Terms.as_view(), name="terms"),

]