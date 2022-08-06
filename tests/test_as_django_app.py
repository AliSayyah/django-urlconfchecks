"""Test module as a django app."""


def test_app_is_recognized():
    """Test that the app is recognized by Django.

    Returns:
        None
    """
    from django.apps import apps

    assert apps.is_installed('django_urlconfchecks')
