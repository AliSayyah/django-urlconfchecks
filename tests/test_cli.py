from typer.testing import CliRunner
from django_urlconfchecks.cli import app
from django_urlconfchecks import __version__


runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Show this message and exit." in result.output


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"Django Urlconf Checks Version: {__version__}\n" in result.output


def test_cli_urlconf_correct():
    result = runner.invoke(app, ["--urlconf", "tests.dummy_project.urls.correct_urls"])
    assert "Done. No errors found." in result.output
    assert result.exit_code == 0



