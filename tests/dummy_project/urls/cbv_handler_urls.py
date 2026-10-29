"""URL patterns for Django class-based view handler checks."""

from django.urls import include, path, re_path

from tests.dummy_project.cbv_views import (
    AsyncView,
    BadView,
    CleanView,
    DispatchView,
    ExplicitHeadView,
    ExtraView,
    IncludeView,
    InheritedBadView,
    NoRequestView,
    RequiredView,
    StarView,
)

urlpatterns = [
    path("clean/<int:pk>/", CleanView.as_view()),
    path("bad/<int:pk>/", BadView.as_view()),
    path("no-request/<int:pk>/", NoRequestView.as_view()),
    path("required/<int:pk>/", RequiredView.as_view()),
    path("star/<int:pk>/", StarView.as_view()),
    path("dispatch/<int:pk>/", DispatchView.as_view()),
    path("head/<int:pk>/", ExplicitHeadView.as_view()),
    path("async/<int:pk>/", AsyncView.as_view()),
    path("inherited-bad/<int:pk>/", InheritedBadView.as_view()),
    path("include/", include([path("<int:pk>/", IncludeView.as_view())]), {"flag": True}),
    re_path(r"^regex/(?P<pk>\d+)/$", CleanView.as_view()),
    path("extra/", ExtraView.as_view(), {"flag": "wrong"}),
]
