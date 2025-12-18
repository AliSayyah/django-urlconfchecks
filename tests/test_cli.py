"""Test module for cli."""

import json

import pytest
from django.conf import settings
from django.utils.functional import empty
from typer.testing import CliRunner

from django_urlconfchecks import __version__
from django_urlconfchecks.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def configure():
    """Configure."""
    settings._wrapped = empty
    yield
    settings._wrapped = empty


def test_cli_no_manage():
    """Test no manage.py module and no urlconf."""
    result = runner.invoke(app)
    assert result.exit_code == 1
    assert (
        "Could not find manage.py in current directory or subdirectories.\n"
        "Make sure you are in the project root directory where manage.py exists.Or you can specify your main"
        " urlconf module path with -u or --urlconf option.\n" in result.output
    )


def test_cli_urlconf_incorrect_one_error():
    """Test when one urlconf is incorrect."""
    result = runner.invoke(app, ["--urlconf", "tests.dummy_project.urls.incorrect_urls"])
    assert (
        "1 error(s), 0 warning(s) found:\n"
        "\t<URLPattern 'articles/<str:year>/'>: (urlchecker.E002) View"
        " tests.dummy_project.views.year_archive for parameter `year`,"
        " annotated type int does not match expected `str` from urlconf\n" in result.output
    )
    assert result.exit_code == 1


def test_cli_urlconf_incorrect_multiple_errors():
    """Test when multiple urlconfs are incorrect."""
    result = runner.invoke(app, ["--urlconf", "tests.dummy_project.urls.child_urls"])

    assert (
        "5 error(s), 0 warning(s) found:\n"
        "\t<URLPattern 'articles/<str:year>/<str:month>/'>: (urlchecker.E002) View"
        " tests.dummy_project.views.month_archive for parameter `year`,"
        " annotated type int does not match expected `str` from urlconf\n"
        "\t<URLPattern 'articles/<str:year>/<str:month>/'>: (urlchecker.E002) View"
        " tests.dummy_project.views.month_archive for parameter `month`,"
        " annotated type int does not match expected `str` from urlconf\n"
        "\t<URLPattern 'articles/<str:year>/<int:month>/<slug:slug>/'>: (urlchecker.E002) View"
        " tests.dummy_project.views.article_detail for parameter `year`,"
        " annotated type int does not match expected `str` from urlconf\n"
        "\t<URLPattern '<slug:slug>/'>: (urlchecker.E001) View tests.dummy_project.views.bad_view signature "
        "does not start with `request` parameter, found `slug`.\n"
        "\t<URLPattern 'special-case/<int:param>/'>: (urlchecker.E003) View tests.dummy_project.views.special_case "
        "signature does not contain `param` parameter\n" == result.output
    )
    assert result.exit_code == 1


def test_cli_urlconf_correct():
    """Test when all urlconfs are correct."""
    result = runner.invoke(app, ["--urlconf", "tests.dummy_project.urls.correct_urls"])
    assert "Done. No errors found.\n" == result.output
    assert result.exit_code == 0


def test_cli_quiet():
    """Quiet should suppress human output but keep exit code."""
    result = runner.invoke(app, ["--quiet", "--urlconf", "tests.dummy_project.urls.incorrect_urls"])
    assert result.output == ""
    assert result.exit_code == 1


def test_cli_json_output():
    """JSON output should include counts and issues."""
    result = runner.invoke(app, ["--format", "json", "--urlconf", "tests.dummy_project.urls.incorrect_urls"])
    assert result.exit_code == 1
    payload = result.output.strip()
    assert '"total_errors": 1' in payload
    assert '"total_warnings": 0' in payload
    assert '"id": "urlchecker.E002"' in payload


def test_cli_version():
    """Test version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"Django Urlconf Checks Version: {__version__}\n" == result.output


def test_cli_uses_pyproject_defaults(monkeypatch, tmp_path):
    """Pyproject config should set defaults for quiet/format/silenced views."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.urlconfchecks]
quiet = true
format = "json"
silenced_views = { "tests.dummy_project.views.year_archive" = "E002" }
"""
    )
    monkeypatch.setenv("URLCONFCHECKS_PYPROJECT", str(pyproject))

    result = runner.invoke(app, ["--urlconf", "tests.dummy_project.urls.incorrect_urls"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["total_errors"] == 0
    assert payload["total_warnings"] == 0
