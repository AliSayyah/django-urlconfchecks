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
    rev: 0.5.0
    hooks:
      - id: django-urlconfchecks
```

Run `pre-commit run` to check all URLConfs for errors.
