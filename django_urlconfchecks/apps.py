"""An apps module for django_urlconfchecks."""
from django.apps import AppConfig


class UrlConfChecksConfig(AppConfig):
    """An AppConfig for django_urlconfchecks."""

    name = 'django_urlconfchecks'
    verbose_name = 'URL Conf Checks'

    # noinspection PyUnresolvedReferences
    def ready(self):
        """We only need to import the module to register it as a checker."""
        from django_urlconfchecks import url_checker  # noqa
