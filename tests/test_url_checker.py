#!/usr/bin/env python
"""Tests for `django_urlconfchecks` package."""

from django.conf import settings
from django.core import checks
from django.test.utils import override_settings
from django.urls import URLPattern
from django.urls.resolvers import RoutePattern, get_resolver

from django_urlconfchecks.url_checker import check_url_signatures, get_all_routes
from tests.utils import error_eql
from tests.views import year_archive

settings.configure()


@override_settings(ROOT_URLCONF='tests.urls.correct_urls')
def test_correct_urls():
    """Test that no errors are raised when the urlconf is correct.

    Returns:
         None
    """
    errors = check_url_signatures(None)
    assert not errors


@override_settings(ROOT_URLCONF='tests.urls.incorrect_urls')
def test_incorrect_urls():
    """Test that errors are raised when the urlconf is incorrect.

    Returns:
        None
    """
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


@override_settings(ROOT_URLCONF='tests.urls.correct_urls')
def test_all_urls_checked():
    """Test that all urls are checked.

    Returns:
        None
    """
    resolver = get_resolver()
    routes = get_all_routes(resolver)
    assert len(list(routes)) == 3


@override_settings(ROOT_URLCONF='tests.urls.parent_urls')
def test_child_urls_checked():
    """Test that child urls are checked.

    Returns:
        None
    """
    resolver = get_resolver()
    routes = get_all_routes(resolver)
    assert len(list(routes)) == 3
