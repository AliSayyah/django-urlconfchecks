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
