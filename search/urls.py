# search/urls.py
from django.urls import path
from . import views

app_name = "search"

urlpatterns = [
    path("", views.search_results, name="search_results"),
    path("suggest/", views.search_suggest, name="search_suggest"),
]