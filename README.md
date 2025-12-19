# Django UrlConf Checks

![django-urlconfchecks logo](logo.png)

[![pypi](https://img.shields.io/pypi/v/django-urlconfchecks.svg)](https://pypi.org/project/django-urlconfchecks/)
[![python](https://img.shields.io/pypi/pyversions/django-urlconfchecks.svg)](https://pypi.org/project/django-urlconfchecks/)
[![Build Status](https://github.com/AliSayyah/django-urlconfchecks/actions/workflows/dev.yml/badge.svg)](https://github.com/AliSayyah/django-urlconfchecks/actions/workflows/dev.yml)
[![codecov](https://codecov.io/gh/AliSayyah/django-urlconfchecks/branch/main/graphs/badge.svg)](https://codecov.io/github/AliSayyah/django-urlconfchecks)
[![License](https://img.shields.io/github/license/AliSayyah/django-urlconfchecks.svg)](https://www.gnu.org/licenses/gpl-3.0.en.html)

Static checker that keeps your URL patterns and view annotations in sync, using Django’s built-in check framework.

* [Documentation](https://AliSayyah.github.io/django-urlconfchecks)
* [GitHub](https://github.com/AliSayyah/django-urlconfchecks)
* [PyPI](https://pypi.org/project/django-urlconfchecks/)

## Key features

* Detects mismatches between URL converters/default kwargs and view annotations (ints, UUIDs, container generics, etc.).
* Works as a Django system check (`manage.py check`) or standalone CLI.
* Honors custom converters and fine-grained silencing per view.
* Pre-commit friendly; CI-ready with machine-readable output.

## Installation

    pip install django-urlconfchecks

Compatibility:

| Python | Django |
| --- | --- |
| 3.10–3.12 | 4.2 – <6.1 |
| 3.13 | 5.1.3 – <6.1 |
| 3.14 | 5.2.8 – <6.1 |

## Quick start

1) Install: `pip install django-urlconfchecks`
2) From your project root (where `manage.py` lives): `urlconfchecks`
   * Or target a specific module: `urlconfchecks --urlconf myproj.urls`
3) Optional: add defaults in `pyproject.toml`:

   ```toml
   [tool.urlconfchecks]
   quiet = true
   format = "json"
   silenced_views = { "myproj.views.legacy_view" = "E002" }
   ```

   CLI flags always override these defaults.

## Usage

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
      -q, --quiet           Suppress human-readable output; exit codes still set.
      -f, --format TEXT     Output format. Supported: json.
      --install-completion  Install completion for the current shell.
      --show-completion     Show completion for the current shell, to copy it or
                            customize the installation.
      --help                Show this message and exit.
```

### As a pre-commit hook

Add the following to your `.pre-commit-config.yaml` file:

```yaml
  - repo: https://github.com/AliSayyah/django-urlconfchecks
    rev: v0.13.0
    hooks:
      - id: django-urlconfchecks
```

For more information, see the [usage documentation](https://alisayyah.github.io/django-urlconfchecks/usage/).

## What it catches (example)

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

Output:

```
(urlchecker.E002) For parameter `year`, annotated type int does not match expected `str` from urlconf
```

JSON (`--format json`):

```json
{
  "errors": [
    {
      "id": "urlchecker.E002",
      "message": "View myproj.views.year_archive for parameter `year`, annotated type int does not match expected `str` from urlconf",
      "obj": "<URLPattern 'articles/<str:year>/'>",
      "hint": null
    }
  ],
  "warnings": [],
  "total_errors": 1,
  "total_warnings": 0
}
```

## Credits

* [Luke Plant](https://github.com/spookylukey) for providing the idea and the initial code.
* This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and
  the [waynerv/cookiecutter-pypackage](https://github.com/waynerv/cookiecutter-pypackage) project template.
