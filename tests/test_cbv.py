"""Tests for Django and Django REST framework class-based view checks."""

import pytest
from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import resolve

from django_urlconfchecks.check import check_url_signatures


def _errors_by_route(errors):
    grouped = {}
    for error in errors:
        grouped.setdefault(str(error.obj.pattern), []).append(error)
    return grouped


@override_settings(
    ROOT_URLCONF="tests.dummy_project.urls.cbv_handler_urls",
    URLCONFCHECKS_SILENCED_VIEWS={},
)
def test_django_cbv_handlers_use_the_route_checker():
    grouped = _errors_by_route(check_url_signatures(None))

    assert "clean/<int:pk>/" not in grouped
    assert "include/<int:pk>/" not in grouped
    assert [error.id for error in grouped["bad/<int:pk>/"]] == ["urlchecker.E002", "urlchecker.E003"]
    assert all("BadView." in error.msg for error in grouped["bad/<int:pk>/"])
    assert [error.id for error in grouped["no-request/<int:pk>/"]] == ["urlchecker.E001"]
    assert [error.id for error in grouped["required/<int:pk>/"]] == ["urlchecker.E004"]
    assert [error.id for error in grouped["star/<int:pk>/"]] == ["urlchecker.E002"]
    assert [error.id for error in grouped["dispatch/<int:pk>/"]] == ["urlchecker.E002"]
    assert [error.id for error in grouped["head/<int:pk>/"]] == ["urlchecker.E002"]
    assert ".head" in grouped["head/<int:pk>/"][0].msg
    assert [error.id for error in grouped["async/<int:pk>/"]] == ["urlchecker.E002"]
    inherited = grouped["inherited-bad/<int:pk>/"]
    assert [error.id for error in inherited] == ["urlchecker.E003"]
    assert "View tests.dummy_project.cbv_views.InheritedBadView.get signature" in inherited[0].msg
    assert [error.id for error in grouped["extra/"]] == ["urlchecker.E005"]
    assert [error.id for error in grouped["^regex/(?P<pk>\\d+)/$"]] == [
        "urlchecker.E002",
        "urlchecker.E002",
    ]
    assert not any("BadView.head" in error.msg for error in grouped["bad/<int:pk>/"])
    assert not any(error.id == "urlchecker.W001" for errors in grouped.values() for error in errors)


@override_settings(
    ROOT_URLCONF="tests.dummy_project.urls.cbv_generic_urls",
    URLCONFCHECKS_SILENCED_VIEWS={},
)
def test_django_generic_views_do_not_produce_new_messages():
    assert check_url_signatures(None) == []


@override_settings(ROOT_URLCONF="tests.dummy_project.urls.cbv_handler_urls")
def test_cbv_handler_silencing_supports_methods_and_classes():
    bad_get = "tests.dummy_project.cbv_views.BadView.get"
    bad_class = "tests.dummy_project.cbv_views.BadView"

    with override_settings(URLCONFCHECKS_SILENCED_VIEWS={bad_get: "E002"}):
        errors = check_url_signatures(None)
        assert [error.id for error in errors if ".BadView." in error.msg] == ["urlchecker.E003"]

    with override_settings(URLCONFCHECKS_SILENCED_VIEWS={f"{bad_class}.*": "E002,E003"}):
        errors = check_url_signatures(None)
        assert not any(".BadView." in error.msg for error in errors)

    with override_settings(URLCONFCHECKS_SILENCED_VIEWS={bad_class: "E002,E003"}):
        errors = check_url_signatures(None)
        assert not any(".BadView." in error.msg for error in errors)


@override_settings(ROOT_URLCONF="tests.dummy_project.urls.cbv_handler_urls")
def test_cbv_routes_resolve_and_bad_handler_raises_type_error():
    request_factory = RequestFactory()
    clean = resolve("/clean/7/")
    clean.func(request_factory.get("/clean/7/"), *clean.args, **clean.kwargs)
    clean_post = resolve("/clean/7/")
    clean_post.func(request_factory.post("/clean/7/"), *clean_post.args, **clean_post.kwargs)

    bad = resolve("/bad/7/")
    with pytest.raises(TypeError):
        bad.func(request_factory.post("/bad/7/"), *bad.args, **bad.kwargs)

    required = resolve("/required/7/")
    with pytest.raises(TypeError):
        required.func(request_factory.get("/required/7/"), *required.args, **required.kwargs)


def test_drf_cbv_handlers_and_viewset_actions():
    pytest.importorskip("rest_framework")
    with override_settings(
        ROOT_URLCONF="tests.dummy_project.urls.drf_cbv_urls",
        URLCONFCHECKS_SILENCED_VIEWS={},
    ):
        grouped = _errors_by_route(check_url_signatures(None))
    assert [error.id for error in grouped["bad/<int:pk>/"]] == ["urlchecker.E002"]
    assert [error.id for error in grouped["^bad/(?P<pk>[^/.]+)/$"]] == ["urlchecker.E002"]
    broken_action = grouped["^bad/(?P<pk>[^/.]+)/broken/$"]
    assert [error.id for error in broken_action] == ["urlchecker.E003"]
    assert "BadViewSet.broken signature does not contain `pk`" in broken_action[0].msg
    assert not any(
        "ArticleAPIView" in error.msg or "ArticleViewSet" in error.msg
        for errors in grouped.values()
        for error in errors
    )
