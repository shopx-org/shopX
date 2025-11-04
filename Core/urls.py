# core/urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('comment/<str:app_label>/<str:model_name>/<int:object_id>/', views.add_comment, name='add_comment'),
]
