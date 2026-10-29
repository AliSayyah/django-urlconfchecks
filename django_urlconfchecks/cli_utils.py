"""Utils for cli."""

import importlib
import os
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from os import devnull

import django
import typer
from django.conf import settings


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

        django.setup()
    if urlconf:
        settings.ROOT_URLCONF = urlconf


def get_manage():
    """Get the path to manage.py and import it with `importlib.import_module`."""
    try:
        manage = importlib.import_module("manage", ".")
    except ImportError:
        typer.secho(
            "Could not find manage.py in current directory or subdirectories.\n"
            "Make sure you are in the project root directory where manage.py exists."
            "Or you can specify your main urlconf module path with -u or --urlconf option.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1) from None
    else:
        main = getattr(manage, 'main', None)
        if main:
            # main() sets DJANGO_SETTINGS_MODULE, then runs Django's command line on sys.argv.
            # Hide our own CLI flags from it, or Django treats them as an unknown command and exits.
            argv = sys.argv
            sys.argv = ["manage.py"]
            try:
                with suppress_std():
                    main()
            finally:
                sys.argv = argv
            return
