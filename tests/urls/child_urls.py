"""child urls for test."""

from django.urls import path

from tests import views

urlpatterns = [
    path('articles/<int:year>/<int:month>/', views.month_archive),
    path('articles/<int:year>/<int:month>/<slug:slug>/', views.article_detail),
]
