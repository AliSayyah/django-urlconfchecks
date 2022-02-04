# django-UrlConfChecks

[![pypi](https://img.shields.io/pypi/v/django-urlconfchecks.svg)](https://pypi.org/project/django-urlconfchecks/)
[![python](https://img.shields.io/pypi/pyversions/django-urlconfchecks.svg)](https://pypi.org/project/django-urlconfchecks/)
[![Build Status](https://github.com/AliSayyah/django-urlconfchecks/actions/workflows/dev.yml/badge.svg)](https://github.com/AliSayyah/django-urlconfchecks/actions/workflows/dev.yml)
[![codecov](https://codecov.io/gh/AliSayyah/django-urlconfchecks/branch/main/graphs/badge.svg)](https://codecov.io/github/AliSayyah/django-urlconfchecks)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/AliSayyah/django-urlconfchecks/main.svg)](https://results.pre-commit.ci/latest/github/AliSayyah/django-urlconfchecks/main)

a python package for type checking the urls and associated views

* Documentation: <https://AliSayyah.github.io/django-urlconfchecks>
* GitHub: <https://github.com/AliSayyah/django-urlconfchecks>
* PyPI: <https://pypi.org/project/django-urlconfchecks/>
* Free software: GPL3
## Installation

    pip install django-urlconfchecks

## Usage

Add this to your settings.py imports:

    import django_urlconfchecks
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

def special_case(request):
    pass


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

* TODO
    - Fine-grained methods for silencing checks.
    - Should only warn for each unhandled Converter once
    - Regex patterns perhaps? (only RoutePattern supported at the moment)

## Credits

- [Luke Plant](https://github.com/spookylukey) for providing the idea and the initial code.
- This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and
  the [waynerv/cookiecutter-pypackage](https://github.com/waynerv/cookiecutter-pypackage) project template.
