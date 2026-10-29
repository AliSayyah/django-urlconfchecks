"""Test module for cli."""

import json
import os
import subprocess
import sys
import textwrap

import pytest
from django.conf import settings
from django.utils.functional import empty
from typer.testing import CliRunner

from django_urlconfchecks import __version__
from django_urlconfchecks.cli import app
from django_urlconfchecks.cli_utils import get_manage

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


@pytest.fixture
def django_project(tmp_path):
    """A minimal Django project with a standard manage.py, outside the test settings."""
    (tmp_path / "manage.py").write_text(
        textwrap.dedent(
            """
            import os
            import sys


            def main():
                os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proj.settings")
                from django.core.management import execute_from_command_line

                execute_from_command_line(sys.argv)


            if __name__ == "__main__":
                main()
            """
        )
    )
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "__init__.py").write_text("")
    (proj / "settings.py").write_text('SECRET_KEY = "x"\nROOT_URLCONF = "proj.urls"\nINSTALLED_APPS = []\n')
    (proj / "views.py").write_text("def good(request, pk: int): ...\n\n\ndef bad(request, pk: str): ...\n")
    (proj / "urls.py").write_text(
        "from django.urls import path\n\nfrom proj import views\n\n"
        'urlpatterns = [path("good/<int:pk>/", views.good), path("bad/<int:pk>/", views.bad)]\n'
    )
    (proj / "good_urls.py").write_text(
        'from django.urls import path\n\nfrom proj import views\n\nurlpatterns = [path("<int:pk>/", views.good)]\n'
    )
    return tmp_path


def _run_cli(cwd, *args):
    env = {k: v for k, v in os.environ.items() if k not in ("DJANGO_SETTINGS_MODULE", "URLCONFCHECKS_PYPROJECT")}
    return subprocess.run(
        # -P: like the installed `urlconfchecks` script, don't put the current directory on sys.path.
        [sys.executable, "-P", "-c", "from django_urlconfchecks.cli import app; app()", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_cli_manage_py_human_output(django_project):
    result = _run_cli(django_project)
    assert result.returncode == 1
    assert "1 error(s), 0 warning(s) found:" in result.stdout
    assert "(urlchecker.E002) View proj.views.bad for parameter `pk`" in result.stdout


@pytest.mark.parametrize("flag", ["-f", "--format"])
def test_cli_manage_py_json_output(django_project, flag):
    """Flags must reach our CLI, not manage.py's command line."""
    result = _run_cli(django_project, flag, "json")
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["total_errors"] == 1
    assert payload["errors"][0]["id"] == "urlchecker.E002"


@pytest.mark.parametrize("flag", ["-q", "--quiet"])
def test_cli_manage_py_quiet(django_project, flag):
    result = _run_cli(django_project, flag)
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == ""

    (django_project / "proj" / "urls.py").write_text("from proj.good_urls import urlpatterns  # noqa: F401\n")
    result = _run_cli(django_project, flag)
    assert result.returncode == 0
    assert result.stdout == ""


def test_cli_manage_py_clean_project(django_project):
    (django_project / "proj" / "urls.py").write_text("from proj.good_urls import urlpatterns  # noqa: F401\n")
    result = _run_cli(django_project)
    assert result.returncode == 0
    assert result.stdout == "Done. No errors found.\n"


def test_cli_urlconf_from_project_directory(django_project):
    """--urlconf must be able to import modules from the current directory."""
    result = _run_cli(django_project, "--urlconf", "proj.good_urls")
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "Done. No errors found.\n"

    result = _run_cli(django_project, "-u", "proj.urls", "-f", "json")
    assert result.returncode == 1
    assert json.loads(result.stdout)["total_errors"] == 1


def test_get_manage_hides_and_restores_argv(django_project, monkeypatch):
    seen = django_project / "seen_argv.json"
    (django_project / "manage.py").write_text(
        "import json\nimport os\nimport sys\n\n"
        'if __name__ == "__main__":\n'
        '    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proj.settings")\n'
        f"    open({str(seen)!r}, 'w').write(json.dumps(sys.argv))\n"
    )
    monkeypatch.chdir(django_project)
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
    monkeypatch.setattr(sys, "argv", ["urlconfchecks", "-f", "json"])

    get_manage()

    assert json.loads(seen.read_text()) == [str(django_project / "manage.py")]
    assert sys.argv == ["urlconfchecks", "-f", "json"]
    assert os.environ["DJANGO_SETTINGS_MODULE"] == "proj.settings"


# Real-world manage.py layouts. healthchecks, babybuddy, netbox, paperless-ngx and others set
# DJANGO_SETTINGS_MODULE only under `if __name__ == "__main__":`, without a main() function.
MAIN_GUARD_ONLY = """
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proj.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
"""

EXITS_AFTERWARDS = MAIN_GUARD_ONLY + "    sys.exit(0)\n"


@pytest.mark.parametrize("manage_py", [MAIN_GUARD_ONLY, EXITS_AFTERWARDS], ids=["main-guard-only", "sys-exit"])
def test_cli_manage_py_layouts(django_project, manage_py):
    (django_project / "manage.py").write_text(manage_py)
    result = _run_cli(django_project, "-f", "json")
    assert result.returncode == 1, result.stderr
    assert json.loads(result.stdout)["total_errors"] == 1


def test_cli_manage_py_that_extends_sys_path(django_project):
    """Settings living in a directory that manage.py adds to sys.path (e.g. `src/`)."""
    src = django_project / "src"
    src.mkdir()
    (django_project / "proj").rename(src / "proj")
    (django_project / "manage.py").write_text(
        "import os\nimport sys\n\n"
        'if __name__ == "__main__":\n'
        '    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))\n'
        '    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proj.settings")\n'
    )
    result = _run_cli(django_project, "-f", "json")
    assert result.returncode == 1, result.stderr
    assert json.loads(result.stdout)["total_errors"] == 1


def test_cli_manage_py_without_settings_module(django_project):
    """manage.py that relies on the environment (e.g. a .env file) gets a clear message, not a traceback."""
    (django_project / "manage.py").write_text('import sys\n\nif __name__ == "__main__":\n    pass\n')
    result = _run_cli(django_project)
    assert result.returncode == 1
    assert "Could not set up Django:" in result.stdout
    assert "Set DJANGO_SETTINGS_MODULE" in result.stdout
    assert "Traceback" not in result.stdout + result.stderr
