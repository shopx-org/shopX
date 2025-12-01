from django.urls import path
from .views import faq_view

app_name = "faq"

urlpatterns = [
    path("", faq_view, name="faqs"),
]
