"""URLs using path(kwargs=)."""
from django.urls import path

from tests.dummy_project import views

urlpatterns = [
    # This one is valid, should produce no error
    path('articles-2020/', views.year_archive, kwargs={'year': 2020}),
    # This one is missing 'year',
    path('articles-2021/', views.year_archive),
    # This one has wrong type:
    path('articles-2022/', views.year_archive, kwargs={'year': '2022'}),
    # This one has extra arg which will cause type error:
    path('articles-2023/', views.year_archive, kwargs={'year': 2023, 'other': 123}),
    # This one is not typed, can't check
    path('articles-2024/', views.year_archive_untyped, kwargs={'year': 2024}),
]
