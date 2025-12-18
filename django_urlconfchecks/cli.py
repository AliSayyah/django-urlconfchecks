"""CLI module for django_urlconfchecks."""

from typing import Literal, Optional

from django.core.checks import Error

from django_urlconfchecks import __version__
from django_urlconfchecks.cli_utils import setup_django
from django_urlconfchecks.config import load_config

try:
    import django
except ImportError:
    raise ImportError('django_urlconfchecks requires django. Install it with `pip install django`.') from None
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
    quiet: Optional[bool] = typer.Option(
        None, "--quiet", "-q", help="Suppress human-friendly output; exit codes still set."
    ),
    format: Optional[Literal["json"]] = typer.Option(None, "--format", "-f", help="Output format. Supported: json."),
) -> None:
    """Check all URLConfs for errors."""
    if django.VERSION[0:2] < (4, 2):
        typer.secho("Django version 4.2 or higher is required.", fg=typer.colors.RED)
        raise typer.Exit(1)

    config = load_config()

    setup_django(urlconf=urlconf)

    resolved_quiet = quiet if quiet is not None else bool(config.quiet)
    resolved_format = format or (config.format if config.format in (None, "json") else None)

    from django_urlconfchecks.check import _DEFAULT_SILENCED_VIEWS, check_url_signatures

    if config.silenced_views and not getattr(django.conf.settings, "URLCONFCHECKS_SILENCED_VIEWS", None):
        merged_silencers = {**_DEFAULT_SILENCED_VIEWS, **config.silenced_views}
        django.conf.settings.URLCONFCHECKS_SILENCED_VIEWS = merged_silencers

    errors = check_url_signatures(None)
    warnings = [e for e in errors if not isinstance(e, Error)]
    errors_only = [e for e in errors if isinstance(e, Error)]

    if resolved_format == "json":
        _print_json(errors, errors_only, warnings)
    elif not resolved_quiet:
        _print_human(errors, errors_only, warnings)

    raise typer.Exit(1 if errors_only else 0)


def _print_human(all_issues, errors_only, warnings):
    if all_issues:
        typer.secho(f"{len(errors_only)} error(s), {len(warnings)} warning(s) found:", fg=typer.colors.BRIGHT_RED)
        for issue in all_issues:
            if isinstance(issue, Error):
                typer.secho(f"\t{issue}", fg=typer.colors.RED)
            else:
                typer.secho(f"\t{issue}", fg=typer.colors.YELLOW)
    else:
        typer.secho("Done. No errors found.", fg=typer.colors.GREEN)


def _print_json(all_issues, errors_only, warnings):
    import json

    payload = {
        "errors": [_serialize_issue(issue) for issue in errors_only],
        "warnings": [_serialize_issue(issue) for issue in warnings],
        "total_errors": len(errors_only),
        "total_warnings": len(warnings),
    }
    typer.echo(json.dumps(payload))


def _serialize_issue(issue):
    return {
        "id": issue.id,
        "message": issue.msg,
        "obj": str(issue.obj),
        "hint": issue.hint,
    }
