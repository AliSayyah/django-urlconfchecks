"""Tests for `django_urlconfchecks` package."""
import sys

from django.core import checks
from django.test.utils import override_settings
from django.urls import URLPattern
from django.urls.resolvers import RoutePattern, get_resolver

from django_urlconfchecks.check import (
    _DEFAULT_SILENCED_VIEWS,
    check_url_signatures,
    get_all_routes,
    get_converter_output_type,
)
from tests.dummy_project.urls import converter_urls
from tests.dummy_project.views import year_archive, year_archive_untyped
from tests.utils import error_eql


def test_correct_urls():
    """Test that no errors are raised when the urlconf is correct.

    Returns:
         None
    """
    with override_settings(ROOT_URLCONF='tests.dummy_project.urls.correct_urls'):
        errors = check_url_signatures(None)
        assert not errors


def test_incorrect_urls():
    """Test that errors are raised when the urlconf is incorrect.

    Returns:
        None
    """
    with override_settings(ROOT_URLCONF='tests.dummy_project.urls.incorrect_urls'):
        errors = check_url_signatures(None)
        expected_error = checks.Error(
            'View tests.dummy_project.views.year_archive for parameter `year`, annotated '
            'type int does not match expected `str` from urlconf',
            hint=None,
            obj=URLPattern(
                pattern=RoutePattern(route='articles/<str:year>/', is_endpoint=True),
                callback=year_archive,
                default_args={},
            ),
            id='urlchecker.E002',
        )
        assert len(errors) == 1

        assert error_eql(errors[0], expected_error)


def test_silencing():
    """Test that fine-grained error silencing mechanisms work."""
    # Specific view silenced
    with override_settings(
        ROOT_URLCONF="tests.dummy_project.urls.incorrect_urls",
        URLCONFCHECKS_SILENCED_VIEWS={"tests.dummy_project.views.year_archive": "E002"},
    ):
        assert len(check_url_signatures(None)) == 0

    # Glob pattern
    with override_settings(
        ROOT_URLCONF="tests.dummy_project.urls.incorrect_urls",
        URLCONFCHECKS_SILENCED_VIEWS={"tests.dummy_project.views.*": "E002"},
    ):
        assert len(check_url_signatures(None)) == 0

    # Non-matching silencer
    with override_settings(
        ROOT_URLCONF="tests.dummy_project.urls.incorrect_urls",
        URLCONFCHECKS_SILENCED_VIEWS={"tests.dummy_project.views.month_archive": "E002"},
    ):
        assert len(check_url_signatures(None)) > 0


def test_default_silencing_for_cbv():
    with override_settings(
        ROOT_URLCONF="tests.dummy_project.urls.cbv_urls", URLCONFCHECKS_SILENCED_VIEWS=_DEFAULT_SILENCED_VIEWS
    ):
        assert len(check_url_signatures(None)) == 0


def test_all_urls_checked():
    """Test that all urls are checked.

    Returns:
        None
    """
    with override_settings(ROOT_URLCONF='tests.dummy_project.urls.correct_urls'):
        resolver = get_resolver()
        routes = get_all_routes(resolver)
        assert len(list(routes)) == 3


def test_child_urls_checked():
    """Test that child urls are checked.

    Returns:
        None
    """
    with override_settings(ROOT_URLCONF='tests.dummy_project.urls.parent_urls'):
        resolver = get_resolver()
        routes = get_all_routes(resolver)
        assert len(list(routes)) == 5


def test_admin_urls_ignored():
    """Test that admin urls errors are ignored with default settings.

    Returns:
        None
    """
    with override_settings(ROOT_URLCONF='tests.dummy_project.urls.admin_urls'):
        errors = check_url_signatures(None)
        assert len(errors) == 0


def test_converters():
    assert get_converter_output_type(converter_urls.YearConverterViaSubclass()) == int
    assert get_converter_output_type(converter_urls.YearConverterAsFloat()) == float

    with override_settings(ROOT_URLCONF='tests.dummy_project.urls.converter_urls'):
        errors = check_url_signatures(None)
        assert len(errors) == 2
        assert error_eql(
            errors[0],
            checks.Warning(
                msg="Don't know output type for converter "
                "tests.dummy_project.urls.converter_urls.YearConverterNoTypeHint, can't verify URL signatures.",
                hint=None,
                obj=converter_urls.YearConverterNoTypeHint,
                id='urlchecker.W002.tests.dummy_project.urls.converter_urls.YearConverterNoTypeHint',
            ),
        )
        assert error_eql(
            errors[1],
            checks.Error(
                msg="View tests.dummy_project.views.year_archive for parameter `year`, "
                "annotated type int does not match expected `float` from urlconf",
                hint=None,
                obj=URLPattern(
                    pattern=RoutePattern(route="articles_yyyy_float/<yyyy_float:year>/", is_endpoint=True),
                    callback=year_archive,
                    default_args={},
                ),
                id="urlchecker.E002",
            ),
        )


def test_path_kwargs():
    """Test that kwargs specified in path(kwargs=...) are included in analysis."""
    with override_settings(ROOT_URLCONF='tests.dummy_project.urls.path_kwargs_urls'):
        errors = check_url_signatures(None)
        assert len(errors) == 4

        assert error_eql(
            errors[0],
            checks.Error(
                msg="View tests.dummy_project.views.year_archive signature contains `year` parameter "
                "without default or ULRconf parameter",
                hint=None,
                obj=URLPattern(
                    pattern=RoutePattern(route='articles-2021/', is_endpoint=True),
                    callback=year_archive,
                    default_args={},
                ),
                id="urlchecker.E004",
            ),
        )

        assert error_eql(
            errors[1],
            checks.Error(
                msg="View tests.dummy_project.views.year_archive: for parameter `year`, default argument"
                " '2022' in urlconf, type str, does not match annotated type int from view signature",
                hint=None,
                obj=URLPattern(
                    pattern=RoutePattern(route='articles-2022/', is_endpoint=True),
                    callback=year_archive,
                    default_args={'year': '2022'},
                ),
                id="urlchecker.E005",
            ),
        )

        assert error_eql(
            errors[2],
            checks.Error(
                msg="View tests.dummy_project.views.year_archive is being passed additional unexpected "
                "parameter `other` from default arguments in urlconf",
                hint=None,
                obj=URLPattern(
                    pattern=RoutePattern(route='articles-2023/', is_endpoint=True),
                    callback=year_archive,
                    default_args={'year': 2023, 'other': 123},
                ),
                id="urlchecker.E006",
            ),
        )
        assert error_eql(
            errors[3],
            checks.Warning(
                msg="View tests.dummy_project.views.year_archive_untyped missing type annotation for "
                "parameter `year`, can\'t check type.",
                hint=None,
                obj=URLPattern(
                    pattern=RoutePattern(route='articles-2024/', is_endpoint=True),
                    callback=year_archive_untyped,
                    default_args={'year': 2024},
                ),
                id="urlchecker.W003",
            ),
        )


@override_settings(ROOT_URLCONF='tests.dummy_project.urls.optional_args')
def test_optional_args():
    errors = check_url_signatures(None)
    if sys.version_info >= (3, 10):
        assert len(errors) > 0
    for error in errors:
        assert error.obj.pattern._route.startswith('bad-')


@override_settings(ROOT_URLCONF='tests.dummy_project.urls.parameterized_generics')
def test_parameterized_generics():
    errors = check_url_signatures(None)
    # Currently errors is empty, but at least we didn't crash
    # or falsely return errors for things that are fine
    for error in errors:
        assert error.obj.pattern._route.startswith('bad-')  # pragma: no cover
