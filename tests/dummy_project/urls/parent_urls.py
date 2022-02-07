"""parent urls for tests."""

from django.urls import include, path

from tests.dummy_project import views

urlpatterns = [
    path('child_urls/', include('tests.dummy_project.urls.child_urls')),
    path('articles/<int:year>/', views.year_archive),
]
