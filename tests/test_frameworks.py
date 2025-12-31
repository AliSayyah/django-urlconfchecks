"""Framework integration tests."""

import pytest
from django.conf import settings
from django.core import checks
from django.test.utils import override_settings

from django_urlconfchecks.check import check_url_signatures


def _installed_apps_with(extra_app: str) -> list[str]:
    installed_apps = list(settings.INSTALLED_APPS)
    if extra_app not in installed_apps:
        installed_apps.append(extra_app)
    return installed_apps


def _error_messages(messages):
    return [msg for msg in messages if isinstance(msg, checks.Error) or msg.id.startswith("urlchecker.E")]


def test_drf_viewset_urls_supported():
    pytest.importorskip("rest_framework")
    with override_settings(
        ROOT_URLCONF="tests.dummy_project.urls.drf_urls",
        INSTALLED_APPS=_installed_apps_with("rest_framework"),
    ):
        messages = check_url_signatures(None)
    assert _error_messages(messages) == []


def test_django_ninja_urls_supported():
    pytest.importorskip("ninja")
    with override_settings(ROOT_URLCONF="tests.dummy_project.urls.ninja_urls"):
        messages = check_url_signatures(None)
    assert _error_messages(messages) == []
