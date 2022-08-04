"""child urls for test."""

from django.urls import path

from tests.dummy_project import views

urlpatterns = [
    path('articles/<str:year>/<str:month>/', views.month_archive),
    path('articles/<str:year>/<int:month>/<slug:slug>/', views.article_detail),
    path('<slug:slug>/', views.bad_view),
    path('special-case/<int:param>/', views.special_case),
]
