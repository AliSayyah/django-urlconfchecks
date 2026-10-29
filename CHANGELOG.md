# Changelog

## [0.1.0] - 2022-01-28

### Added

- First release on PyPI.

## [0.2.0] - 2022-01-29

### Added

- Added the actual functionality.
- updated dependencies.

## [0.3.0] - 2022-02-04

### Changed

- fixed a bug that caused the checks to not work. Package is functional now.

## [0.3.1] - 2022-02-07

### Fixed

- fixed a dependency issue that caused the `mkdocs-material-extensions` to install as a runtime dependency.

## [0.4.0] - 2022-02-07

### Changed

- Now, `django_urlconfchecks` is a Django app. This means that it can be installed as a Django app. For more
  information, see [the documentation](https://alisayyah.github.io/django-urlconfchecks/usage/).

## [0.5.0] - 2022-02-21

### Added

- Added two more ways to use the package: a `CLI tool` and a `pre-commit hook`. For more information, see
  the [usage documentation](https://alisayyah.github.io/django-urlconfchecks/usage/).

## [0.6.0] - 2022-04-01

### Fixed

- Fixed a bug that caused `urlconfchecks` to show warnings for Django's `admin` app. Now, `admin` app will be ignored.
  Courtesy @nightboard.

## [0.7.0] - 2022-08-11

### Added

- Added fine-grained method for silencing errors. Courtesy @spookylukey

## [0.7.1] - 2022-08-11

### Added

- Support subclasses of builtin converters.
- More tests.
- Cleanup output text to be more clear and informative.

## [0.7.2] - 2022-08-12

### Added

- Handle default arguments passed via path(kwargs). Courtesy @spookylukey

## [0.7.3] - 2022-08-25

### Fixed

- Fixed an issue where default CBV silencing only worked for django 4

## [0.8.0] - 2022-09-16

### Fixed

- Made error reporting of view reprs consistent with silencer.
- Correctly handle views with Optional arguments.

## [0.9.0] - 2023-02-10

### Fixed

- Fixed crasher when urlconf has optional types. Courtesy @spookylukey
- added python 3.11 support

## [0.10.0] - 2023-08-15

### Added

- Handle cases involving `path` and `include`. Courtesy @spookylukey

## [0.11.0] - 2024-02-27

### Added

- Python 3.12 support
- Django 5 support

### Removed

- Python 3.7 support

## [0.12.0] - 2025-12-18

### Added

- Added python 3.13 and 3.14 support.
- CLI now supports `--format json` to emit structured results with per-type counts and totals.
- CLI gains `--quiet / -q` to suppress normal output while preserving exit codes and summaries.

### Changed

- Dropped python 3.9 support
- Project tooling now uses uv for syncing/building and Ruff for linting/formatting (pre-commit and CI).
- Raised the minimum supported Django version to 4.2 (with targeted upper bounds per Python release).
- Improved type compatibility checks for `typing.Annotated`, `Optional`, and `Union`, and cache URL converter lookups for faster runs.

### Fixed

- Custom boolean path converters are recognized and validated alongside the built-ins.

## [0.13.0] - 2025-12-19

### Added

- Parameterized generics validation: lists, tuples (fixed/variadic), dicts, sets, and optional containers are now type-checked against URL converters and default kwargs.
- Pyproject configuration: `[tool.urlconfchecks]` supports defaults for `quiet`, `format`, and `silenced_views`, with `URLCONFCHECKS_PYPROJECT` override; custom silencers merge with built-ins.

### Fixed

- Container type checking now reports mismatches instead of silently passing parameterized generics.

## [0.13.1] - 2025-12-31

### Fixed

- Handle functools.partial callbacks in _make_callback_repr for Django Ninja or similar frameworks. thanks @joseanoxp

## [0.13.2] - 2026-06-03

### Changed

- Updated the supported version matrix to Python 3.10-3.14 with Django 5.2 and 6.0.

### Fixed

- Resolved false URL signature type mismatches when views or custom converters use `from __future__ import annotations`.

## [0.14.0] - 2026-10-29

### Added

- Support for Django 6.1 and Python 3.15.
- Weekly CI job testing against Django's development branch.

### Changed

- Removed upper bounds on Python, Django and typer so new releases install without waiting for a package update.
- Supported Python versions now follow the Python release cycle; versions are dropped at end-of-life.
- Bumped development and test dependencies to their latest versions.

### Removed

- Python 3.10 support (end-of-life since 2026-10-01), and the `tomli` dependency it required.

## [0.15.0] - 2026-10-29

### Added

- Class-based views are checked: each Django/DRF handler (`get`, `post`, …, an overridden `dispatch`, an explicit `head`) and DRF ViewSet action is checked against the URL's arguments, including handlers inherited from user mixins. Silence them as `module.View.get`, `module.View.*` or `module.View`.
- `re_path()` views are checked: named groups as `str` keyword arguments, unnamed groups as positional arguments.
- `urlchecker.E007` for URLs that pass more positional arguments than the view accepts, and `urlchecker.W004` for parameters fed by an optional regex group without a default.
- VS Code usage documentation, including a ready-to-copy task (#186).

### Changed

- Views with `*args` or `**kwargs` still have their named parameters checked (types, and required parameters without a URL source); this can report additional true positives alongside `W001`.
- `urlchecker.W001` is no longer emitted for class-based view handlers, where `*args`/`**kwargs` are idiomatic.
- Replaced `bump2version` with `bump-my-version` in the development tooling.

### Fixed

- CLI flags (`--format`, `--quiet`, …) silently failed with exit code 1 in projects detected via `manage.py`, because they were passed on to Django's own command line.
- `--urlconf` could not import modules from the current directory when run via the installed `urlconfchecks` command.
- `include()` extra kwargs are passed to child views, and named groups captured by a regex parent reach `path()` children (both were false `E004` errors).
- A `path()` default that overrides a captured value is checked as that default only (previously a false `E006`).
- `W002` is emitted at most once per untyped converter class.

## [Unreleased]

### Fixed

- The CLI now runs `manage.py` the way `python manage.py` does when looking for the settings module. Projects whose `manage.py` sets `DJANGO_SETTINGS_MODULE` only under `if __name__ == "__main__":` without a `main()` function (healthchecks, netbox, paperless-ngx and many others) failed with `ImproperlyConfigured`.
- When the settings module can't be found, the CLI prints a short message suggesting `DJANGO_SETTINGS_MODULE` or `--urlconf` instead of a traceback.
