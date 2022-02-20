"""CLI module for django_urlconfchecks."""
import os
from pathlib import Path
from typing import Optional

from django.core.checks import Error

from django_urlconfchecks import __version__

try:
    import django
except ImportError:
    raise ImportError('django_urlconfchecks requires django. Install it with `pip install django`.')
import typer

app = typer.Typer()


def find_settings_module() -> Optional[str]:
    """Find the settings.py in current directory and subdirectories.

    Returns:
        str: the path to the settings.py
    """
    current_dir = Path(os.getcwd())
    for path in current_dir.glob('**/settings.py'):
        return str(path.relative_to(current_dir)).replace("/", ".").replace(".py", "")
    return None


SETTINGS = find_settings_module()


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        typer.echo(f"Django Urlconf Checks Version: {__version__}")
        raise typer.Exit()


# noinspection PyUnusedLocal
@app.command()
def run(
    settings: str = typer.Option(
        default=SETTINGS,
        help="The settings module to use.\nurlconfchecks will try to find the settings automatically.",
        show_default=True,
    ),
    version: Optional[bool] = typer.Option(None, "--version", callback=version_callback),
) -> int:
    """Check all URLConfs for errors.

    Args:
        settings (str): The settings module to use.
        version (bool, optional): Show version. Defaults to None.

    Returns:
        None
    """
    if not django.VERSION[0:2] >= (3, 2):
        typer.secho("Django version 3.2 or higher is required.", fg=typer.colors.RED)
        return 1

    if SETTINGS is None:
        typer.secho("settings.py not found.", fg=typer.colors.RED)
        typer.secho("Please specify the settings module path with the --settings option.", fg=typer.colors.YELLOW)
        return 1

    os.environ['DJANGO_SETTINGS_MODULE'] = settings
    print(os.environ['DJANGO_SETTINGS_MODULE'] + " is used.")
    django.setup()

    typer.secho(
        f"Using settings module: {settings}\nIf this module is not correct,"
        f" please specify path with --settings option.",
        fg=typer.colors.GREEN,
    )

    from django_urlconfchecks.check import check_url_signatures

    errors = check_url_signatures(None)
    if errors:
        typer.secho(f"{len(errors)} errors found:", fg=typer.colors.BRIGHT_RED)
        for error in errors:
            if isinstance(error, Error):
                typer.secho(f"{error}", fg=typer.colors.RED)
            else:
                typer.secho(f"{error}", fg=typer.colors.YELLOW)
        return 1

    typer.secho("Done. No errors found.", fg=typer.colors.GREEN)
    return 0
