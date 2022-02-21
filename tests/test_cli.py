"""Test module for cli."""
from typer.testing import CliRunner

from django_urlconfchecks import __version__
from django_urlconfchecks.cli import app

runner = CliRunner()


def test_cli_help():
    """Test help."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Show this message and exit." in result.output


def test_cli_version():
    """Test version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"Django Urlconf Checks Version: {__version__}\n" in result.output


def test_cli_urlconf_correct():
    """Test when all urlconfs are corect.."""
    result = runner.invoke(app, ["--urlconf", "tests.dummy_project.urls.correct_urls"])
    assert "Done. No errors found." in result.output
    assert result.exit_code == 0


def test_cli_urlconf_incorrect_one_error():
    """Test when one urlconf is incorrect."""
    result = runner.invoke(app, ["--urlconf", "tests.dummy_project.urls.incorrect_urls"])
    assert (
        "1 error found:\n"
        "\t<URLPattern 'articles/<str:year>/'>: (urlchecker.E002) For parameter `year`,"
        " annotated type int does not match expected `str` from urlconf\n" in result.output
    )
    assert result.exit_code == 1


def test_cli_urlconf_incorrect_multiple_errors():
    """Test when multiple urlconfs are incorrect."""
    result = runner.invoke(app, ["--urlconf", "tests.dummy_project.urls.child_urls"])
    assert (
        "3 errors found:\n"
        "\t<URLPattern 'articles/<str:year>/<str:month>/'>: (urlchecker.E002) For parameter `year`,"
        " annotated type int does not match expected `str` from urlconf\n"
        "\t<URLPattern 'articles/<str:year>/<str:month>/'>: (urlchecker.E002) For parameter `month`,"
        " annotated type int does not match expected `str` from urlconf\n"
        "\t<URLPattern 'articles/<str:year>/<int:month>/<slug:slug>/'>: (urlchecker.E002) For parameter `year`,"
        " annotated type int does not match expected `str` from urlconf\n" == result.output
    )
    assert result.exit_code == 1
