"""CLI module for django_urlconfchecks."""
from typing import Optional

from django.core.checks import Error

from django_urlconfchecks import __version__
from django_urlconfchecks.cli_utils import setup_django

try:
    import django
except ImportError:
    raise ImportError('django_urlconfchecks requires django. Install it with `pip install django`.')
import typer

app = typer.Typer()


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        typer.echo(f"Django Urlconf Checks Version: {__version__}")
        raise typer.Exit()


# noinspection PyUnusedLocal
@app.command()
def run(
    version: Optional[bool] = typer.Option(None, "--version", callback=version_callback),
    urlconf: Optional[str] = typer.Option(None, "-u", "--urlconf", help="Specify the URLconf to check."),
) -> None:
    """Check all URLConfs for errors."""
    if django.VERSION[0:2] < (3, 2):
        typer.secho("Django version 3.2 or higher is required.", fg=typer.colors.RED)
        raise typer.Exit(1)

    setup_django(urlconf=urlconf)

    from django_urlconfchecks.check import check_url_signatures

    errors = check_url_signatures(None)
    if errors:
        typer.secho(f"{len(errors)} error{'s' if len(errors) > 1 else ''} found:", fg=typer.colors.BRIGHT_RED)

        for error in errors:
            if isinstance(error, Error):
                typer.secho(f"\t{error}", fg=typer.colors.RED)
            else:
                typer.secho(f"\t{error}", fg=typer.colors.YELLOW)
        raise typer.Exit(1)
    else:
        typer.secho("Done. No errors found.", fg=typer.colors.GREEN)
        raise typer.Exit(0)
