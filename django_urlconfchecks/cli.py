"""CLI module for django_urlconfchecks."""
import importlib
import os
import sys
from typing import Optional

from django.core.checks import Error

from django_urlconfchecks import __version__
from django_urlconfchecks.cli_utils import suppress_std

try:
    import django
except ImportError:
    raise ImportError('django_urlconfchecks requires django. Install it with `pip install django`.')
import typer

app = typer.Typer()


def setup_django():
    """Find the settings.py in current directory and subdirectories.

    Returns:
        str: the path to the settings.py
    """
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())

    try:
        manage = importlib.import_module("manage", ".")
    except ImportError as e:
        typer.secho(
            "Could not find manage.py in current directory or subdirectories.\n"
            "Make sure you are in the project root directory where manage.py exists.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    else:
        main = getattr(manage, 'main', None)
        if main:
            with suppress_std():
                main()
            django.setup()
            return


setup_django()


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        typer.echo(f"Django Urlconf Checks Version: {__version__}")
        raise typer.Exit()


# noinspection PyUnusedLocal
@app.command()
def run(
    version: Optional[bool] = typer.Option(None, "--version", callback=version_callback),
) -> None:
    """Check all URLConfs for errors.

    Args:
        version (bool, optional): Show version. Defaults to None.

    Returns:
        None
    """
    if not django.VERSION[0:2] >= (3, 2):
        typer.secho("Django version 3.2 or higher is required.", fg=typer.colors.RED)
        typer.Exit(1)

    from django_urlconfchecks.check import check_url_signatures

    errors = check_url_signatures(None)
    if errors:
        typer.secho(f"{len(errors)} error{'s' if len(errors) > 1 else ''} found:", fg=typer.colors.BRIGHT_RED)

        for error in errors:
            if isinstance(error, Error):
                typer.secho(f"\t{error}", fg=typer.colors.RED)
            else:
                typer.secho(f"\t{error}", fg=typer.colors.YELLOW)
        typer.Exit(1)
    else:
        typer.secho("Done. No errors found.", fg=typer.colors.GREEN)
        typer.Exit(0)
