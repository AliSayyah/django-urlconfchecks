"""Utils for cli."""

import os
import runpy
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout, suppress
from os import devnull
from pathlib import Path

import django
import typer
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@contextmanager
def suppress_std():
    """A context manager that redirects stdout and stderr to devnull."""
    with open(devnull, 'w') as fnull:
        with redirect_stderr(fnull) as err, redirect_stdout(fnull) as out:
            yield err, out


def setup_django(urlconf: str | None):
    """We need to set up Django before running checks.

    For running checks, we need to access UrlConf module correctly;
    so we use manage.py to set the `DJANGO_SETTINGS_MODULE`.

    Returns:
        str: the path to the settings.py
    """
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())

    if not settings.configured:
        if urlconf:
            settings.configure(ROOT_URLCONF=urlconf)
        else:
            get_manage()

        try:
            django.setup()
        except ImproperlyConfigured as exc:
            typer.secho(
                f"Could not set up Django: {exc}\n"
                "Set DJANGO_SETTINGS_MODULE, or specify your main urlconf module path with -u or --urlconf.",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1) from None
    if urlconf:
        settings.ROOT_URLCONF = urlconf


def get_manage():
    """Run ./manage.py the way `python manage.py` does, so it sets `DJANGO_SETTINGS_MODULE`.

    manage.py usually sets the settings module (and sometimes sys.path) only under
    `if __name__ == "__main__":`, so it has to be run as a script rather than imported.
    """
    manage_path = Path.cwd() / "manage.py"
    if not manage_path.is_file():
        typer.secho(
            "Could not find manage.py in current directory or subdirectories.\n"
            "Make sure you are in the project root directory where manage.py exists."
            "Or you can specify your main urlconf module path with -u or --urlconf option.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    # manage.py then runs Django's command line on sys.argv. Hide our own CLI flags from it,
    # or Django treats them as an unknown command and exits; with no command it prints help.
    argv = sys.argv
    sys.argv = [str(manage_path)]
    try:
        with suppress_std(), suppress(SystemExit):
            runpy.run_path(str(manage_path), run_name="__main__")
    finally:
        sys.argv = argv
