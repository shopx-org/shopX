# search/urls.py
from django.urls import path
from . import views
from .api_views import SearchResultsAPI

app_name = "search"

urlpatterns = [
    path("s/", views.search_results, name="search_results"),
    path("suggest/", views.search_suggest, name="search_suggest"),
    path("api/results/", SearchResultsAPI.as_view(), name="search_results_api"),
]