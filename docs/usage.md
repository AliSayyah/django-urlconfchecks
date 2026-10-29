# Usage

You can use this package in different ways:

### As a Django app

Add `django_urlconfchecks` to your `INSTALLED_APPS` list in your `settings.py` file.

```python
    INSTALLED_APPS = [
    ...
    'django_urlconfchecks',
]
```

Now, if there is any error, you can check it when you run `python manage.py check` or when your django server runs or
reloads with `python manage.py runserver`.

The checker follows Django's resolver argument passing for `path()`, `re_path()`, nested `include()` calls, converter and regex captures, positional regex groups, and URL pattern keyword arguments. It also checks Django and DRF class-based view handlers, including inherited handlers and DRF ViewSet actions. `urlchecker.E007` reports too many positional regex arguments, and `urlchecker.W004` warns when an optional regex capture has no default in the view signature. `urlchecker.W001` is reported for function views with star arguments; Django and DRF handlers use star arguments without that warning.

The error codes are `E001` (missing request parameter), `E002` (converter type mismatch), `E003` (missing URL parameter), `E004` (required parameter without a URL source), `E005` (extra argument type mismatch), `E006` (unexpected extra argument), and `E007` (too many positional URL arguments). Warnings are `W001` (star arguments on function views), `W002` (unknown converter output), `W003` (missing annotation), `W004` (optional regex capture without a default), and `W005` (view signature could not be inspected).

### As a command line tool

`urlconfchecks` uses the `Typer` module to parse command line arguments.

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

`--urlconf` is optional, and if not specified, app will try to find the manage.py in your current directory for
accessing the main URLConf module.

Example:

```bash
$ urlconfchecks --urlconf my_project.urls

  Done. No errors found.
```

### As a pre-commit hook
Make sure you have `pre-commit` installed and if not, install it with `pip install pre-commit && pre-commit install`.

Then, add the following to your `.pre-commit-config.yaml` file:

```yaml
  - repo: https://github.com/AliSayyah/django-urlconfchecks
    rev: v0.15.0
    hooks:
      - id: django-urlconfchecks
```

Run `pre-commit run` to check all URLConfs for errors.

### In VS Code

The checks run as part of `python manage.py check`, so you can run that command
from a VS Code task or terminal. You can also run the standalone `urlconfchecks`
command. For example, save this as `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Check URLConfs",
      "type": "shell",
      "command": "urlconfchecks",
      "problemMatcher": [],
      "group": "test"
    }
  ]
}
```

The task leaves output in the terminal because the human-readable CLI output
does not use a stable `file:line:message` format. The pre-commit hook above is
also available for checks before each commit.

## Configuration defaults

You can set defaults in `pyproject.toml` so teams don’t repeat flags:

```toml
[tool.urlconfchecks]
quiet = true
format = "json"
silenced_views = { "myproj.views.legacy_view" = "E002" }
```

Notes:

- CLI flags override these values.
- Built-in silencers remain; custom entries are merged.
- To point to a specific config file, set `URLCONFCHECKS_PYPROJECT=/path/to/pyproject.toml`.


## Silencing errors and warnings

You can silence specific errors and warnings as described in the [System check
framework
documentation](https://docs.djangoproject.com/en/stable/topics/checks/).

For example:

```python
SILENCED_SYSTEM_CHECKS = [
    "urlchecker.W003“,
]
```

However, this turns off the check for all view functions. Instead of this you
can use the `URLCONFCHECKS_SILENCED_VIEWS` setting for more fine grained
silencing. The value must be a dictionary:

- whose keys are fully qualified dotted paths to view functions or callables,
  with globbing syntax allowed, e.g. `"my_project.views.my_view"` or
  `"other_project.*"`. For a class-based view, use a handler name such as
  `"my_project.views.ArticleView.get"`, `"my_project.views.ArticleView.*"`
  for all handlers, or `"my_project.views.ArticleView"` for the whole class.

- whose values are comma separated lists of warning or error IDs (without the
  `urlchecker` prefix), e.g. `"E001,W003”`


The default value of `URLCONFCHECKS_SILENCED_VIEWS` is below. If you override it
in your `settings.py`, you will probably want to include the following and add
more items:

```python
URLCONFCHECKS_SILENCED_VIEWS = {
    "*.View.as_view": "W001",  # legacy/unresolved CBV callbacks
    "django.views.generic.base.RedirectView": "W001",
    "django.contrib.*": "W003",  # admin etc.
}
```
