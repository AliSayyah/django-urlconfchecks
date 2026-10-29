"""An i18n URL resolver with an included route."""

from django.conf.urls.i18n import i18n_patterns
from django.urls import include, path

from tests.dummy_project import views

urlpatterns = i18n_patterns(
    path("i18n/", include([path("", views.include_flag_view)]), {"flag": True}),
)
