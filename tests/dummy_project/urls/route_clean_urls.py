"""Clean routes used by the resolver/callback end-to-end test."""

from django.urls import include, path, re_path

from tests.dummy_project import views

urlpatterns = [
    path("include/", include([path("", views.include_flag_view)]), {"flag": True}),
    re_path(r"^regex/(?P<slug>[-\w]+)/$", views.regex_slug_view),
    re_path(r"^positional/(\w+)/(\w+)/$", views.positional_view),
    path("default/<int:pk>/", views.default_pk_view, {"pk": 42}),
]
