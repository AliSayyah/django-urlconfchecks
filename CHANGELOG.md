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
