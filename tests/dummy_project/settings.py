"""Settings module for dummy_project."""
DEBUG = True
USE_TZ = True
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
    }
}
ROOT_URLCONF = ("tests.dummy_project.urls.correct_urls",)
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sites",
    "django_urlconfchecks",
]
SECRET_KEY = "secret"
