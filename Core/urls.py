# core/urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('comment/<str:app_label>/<str:model_name>/<int:object_id>/', views.add_comment, name='add_comment'),
    path('vote/', views.like_dislike_toggle, name='like_dislike_toggle'),
    path('rate/', views.add_rating, name='add_rating'), 
    path('get_user_rating/', views.get_user_rating, name='get_user_rating'),
    path("wishlist/status/", views.wishlist_status, name="wishlist_status"),
    path("wishlist/toggle/", views.toggle_wishlist, name="toggle_wishlist"),
    path("wishlist/", views.wishlist_page, name="wishlist_page"),
    path("about/", views.about_view, name="about"),
]
