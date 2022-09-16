# Django UrlConf Checks

[![pypi](https://img.shields.io/pypi/v/django-urlconfchecks.svg)](https://pypi.org/project/django-urlconfchecks/)
[![python](https://img.shields.io/pypi/pyversions/django-urlconfchecks.svg)](https://pypi.org/project/django-urlconfchecks/)
[![Build Status](https://github.com/AliSayyah/django-urlconfchecks/actions/workflows/dev.yml/badge.svg)](https://github.com/AliSayyah/django-urlconfchecks/actions/workflows/dev.yml)
[![codecov](https://codecov.io/gh/AliSayyah/django-urlconfchecks/branch/main/graphs/badge.svg)](https://codecov.io/github/AliSayyah/django-urlconfchecks)
[![License](https://img.shields.io/github/license/AliSayyah/django-urlconfchecks.svg)](https://www.gnu.org/licenses/gpl-3.0.en.html)

django-urlconfchecks is a static type checker that checks your URLconf parameter types with argument types specified in associated views.
It leverages the Django's static check system.

* [Documentation](https://AliSayyah.github.io/django-urlconfchecks)
* [GitHub](https://github.com/AliSayyah/django-urlconfchecks)
* [PyPI](https://pypi.org/project/django-urlconfchecks/)

## Installation

    pip install django-urlconfchecks

Python 3.7 or later is required. However, before Python 3.10 some checks
relating to `Optional` types in view signatures are skipped due to stdlib
limitations.

## Usage

You can use this package in different ways:

### As a Django app

Add `django_urlconfchecks` to your `INSTALLED_APPS` list in your `settings.py` file.

```python
    INSTALLED_APPS = [
    ...
    'django_urlconfchecks',
]
```

### As a command line tool

Run this command from the root of your project, were `manage.py` is located:

```bash
$ urlconfchecks --help

    Usage: urlconfchecks [OPTIONS]

      Check all URLConfs for errors.

    Options:
      --version
      -u, --urlconf PATH    Specify the URLconf to check.
      --install-completion  Install completion for the current shell.
      --show-completion     Show completion for the current shell, to copy it or
                            customize the installation.
      --help                Show this message and exit.
```

### As a pre-commit hook

Add the following to your `.pre-commit-config.yaml` file:

```yaml
  - repo: https://github.com/AliSayyah/django-urlconfchecks
    rev: v0.8.0
    hooks:
      - id: django-urlconfchecks
```

For more information, see the [usage documentation](https://alisayyah.github.io/django-urlconfchecks/usage/).

## Features

Using this package, URL pattern types will automatically be matched with associated views, and in case of mismatch, an
error will be raised.

Example:

```python
# urls.py
from django.urls import path

from . import views

urlpatterns = [
    path('articles/<str:year>/', views.year_archive),
    path('articles/<int:year>/<int:month>/', views.month_archive),
    path('articles/<int:year>/<int:month>/<slug:slug>/', views.article_detail),
]
```

```python
# views.py

def year_archive(request, year: int):
    pass


def month_archive(request, year: int, month: int):
    pass


def article_detail(request, year: int, month: int, slug: str):
    pass
```

output will be:

```
(urlchecker.E002) For parameter `year`, annotated type int does not match expected `str` from urlconf
```

* TODO:
    - Handle type checking parameterized generics e.g. `typing.List[int]`, `list[str]` etc.
    - Should only warn for each unhandled Converter once.
    - Regex patterns perhaps? (only RoutePattern supported at the moment).

## Credits

- [Luke Plant](https://github.com/spookylukey) for providing the idea and the initial code.
- This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and
  the [waynerv/cookiecutter-pypackage](https://github.com/waynerv/cookiecutter-pypackage) project template.
