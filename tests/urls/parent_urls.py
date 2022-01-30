"""parent urls for tests."""

from django.urls import include, path

from tests import views

urlpatterns = [
    path('child_urls/', include('tests.urls.child_urls')),
    path('articles/<int:year>/', views.year_archive),
]
