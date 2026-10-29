"""Optional named regex groups for W004 tests."""

from django.urls import re_path

from tests.dummy_project import views

urlpatterns = [
    re_path(r"^optional/(?P<page>\d+)?/$", views.regex_optional_view),
    re_path(r"^optional-default/(?P<page>\d+)?/$", views.regex_optional_default_view),
]
