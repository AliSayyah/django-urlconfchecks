"""Included URL patterns for W002 de-duplication tests."""

from django.urls import path

from tests.dummy_project import views

urlpatterns = [
    path("<w002_shared:year>/", views.year_archive),
]
