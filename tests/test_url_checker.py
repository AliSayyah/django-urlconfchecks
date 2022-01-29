#!/usr/bin/env python
"""Tests for `django_urlconfchecks` package."""

from django.conf import settings
from django.core import checks
from django.test.utils import override_settings
from django.urls import URLPattern
from django.urls.resolvers import RoutePattern

from django_urlconfchecks.url_checker import check_url_signatures
from tests.views import year_archive

settings.configure()


def route_pattern_eql(route_pattern: RoutePattern, expected_route_pattern: RoutePattern) -> bool:
    return (
        route_pattern._route == expected_route_pattern._route
        and route_pattern._is_endpoint == expected_route_pattern._is_endpoint
    )


def url_pattern_eql(urlpatterns: URLPattern, expected_urlpatterns: URLPattern) -> bool:
    return (
        urlpatterns.callback == expected_urlpatterns.callback
        and urlpatterns.default_args == expected_urlpatterns.default_args
        and route_pattern_eql(urlpatterns.pattern, expected_urlpatterns.pattern)
    )


def error_eql(error: checks.Error, expected_error: checks.Error) -> bool:
    return (
        error.msg == expected_error.msg
        and error.hint == expected_error.hint
        and error.id == expected_error.id
        and url_pattern_eql(error.obj, expected_error.obj)
    )


@override_settings(ROOT_URLCONF='tests.urls.correct_urls')
def test_correct_urls():
    errors = check_url_signatures(None)
    assert not errors


@override_settings(ROOT_URLCONF='tests.urls.incorrect_urls')
def test_incorrect_urls():
    errors = check_url_signatures(None)
    expected_error = checks.Error(
        'For parameter `year`, annotated type int does not match expected `str` from urlconf',
        hint=None,
        obj=URLPattern(
            pattern=RoutePattern(route='articles/<str:year>/', is_endpoint=True), callback=year_archive, default_args={}
        ),
        id='urlchecker.E002',
    )
    assert len(errors) == 1

    assert error_eql(errors[0], expected_error)
