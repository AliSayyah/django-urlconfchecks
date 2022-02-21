"""child urls for test."""

from django.urls import path

from tests.dummy_project import views

urlpatterns = [
    path('articles/<str:year>/<str:month>/', views.month_archive),
    path('articles/<str:year>/<int:month>/<slug:slug>/', views.article_detail),
]
