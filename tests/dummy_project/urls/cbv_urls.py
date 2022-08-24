"""CBV urls for tests."""

from django.urls import include, path

from tests.dummy_project import views

urlpatterns = [
    path('cbv_view/', views.CBVView.as_view()),
]
