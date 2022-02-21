"""Utils for cli."""
import importlib
import os
import sys
import typing as t
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


def setup_django(urlconf: t.Optional[str]):
    """We need to set up Django before running checks.

    For running checks, we need to access UrlConf module correctly;
    so we use manage.py to set the `DJANGO_SETTINGS_MODULE`.

    Returns:
        str: the path to the settings.py
    """
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
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())

    try:
        manage = importlib.import_module("manage", ".")
    except ImportError:
        typer.secho(
            "Could not find manage.py in current directory or subdirectories.\n"
            "Make sure you are in the project root directory where manage.py exists."
            "Or you can specify your main urlconf module path with -u or --urlconf option.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    else:
        main = getattr(manage, 'main', None)
        if main:
            with suppress_std():
                main()
            return
