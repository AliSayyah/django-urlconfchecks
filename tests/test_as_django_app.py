"""Test module as a django app."""
import os

import django


def test_app_is_recognized():
    """Test that the app is recognized by Django.

    Returns:
        None
    """
    from django.apps import apps

    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.dummy_project.settings'
    django.setup()
    assert apps.is_installed('django_urlconfchecks')
