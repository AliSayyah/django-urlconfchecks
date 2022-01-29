"""Incorrect URLs."""
from django.urls import path

from tests import views

urlpatterns = [
    path('articles/<str:year>/', views.year_archive),
    path('articles/<int:year>/<int:month>/', views.month_archive),
    path('articles/<int:year>/<int:month>/<slug:slug>/', views.article_detail),
]
