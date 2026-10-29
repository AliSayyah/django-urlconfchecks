"""Tests for `django_urlconfchecks` package."""

import typing as t

import pytest
from django.core import checks
from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import URLPattern, URLResolver, resolve
from django.urls.resolvers import RoutePattern, get_resolver

from django_urlconfchecks.check import (
    _DEFAULT_SILENCED_VIEWS,
    _get_callable_globals,
    _instance_is_compatible,
    _optional_regex_groups,
    _type_is_compatible,
    _walk_routes,
    check_url_args_match,
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


def test_future_annotations_are_resolved():
    """Test that deferred annotations are resolved before type compatibility checks."""
    with override_settings(ROOT_URLCONF='tests.dummy_project.urls.future_annotations'):
        errors = check_url_signatures(None)
        assert not errors


def test_future_converter_return_annotations_are_resolved():
    """Test that deferred converter return annotations are resolved before checking view types."""
    with override_settings(ROOT_URLCONF='tests.dummy_project.urls.future_converter_annotations'):
        errors = check_url_signatures(None)
        assert not errors


def test_future_converter_return_annotation_mismatches_are_still_reported():
    """Test that resolved deferred converter annotations are still checked for compatibility."""
    with override_settings(ROOT_URLCONF='tests.dummy_project.urls.future_converter_annotation_mismatch'):
        errors = check_url_signatures(None)
        assert [error.id for error in errors] == ['urlchecker.E002']
        assert "annotated type str does not match expected `int`" in errors[0].msg


def test_future_annotation_mismatches_are_still_reported():
    """Test that resolved deferred annotations are still checked for compatibility."""
    with override_settings(ROOT_URLCONF='tests.dummy_project.urls.future_annotation_mismatch'):
        errors = check_url_signatures(None)
        assert [error.id for error in errors] == ['urlchecker.E002']
        assert "annotated type int does not match expected `str`" in errors[0].msg


def test_unresolved_future_annotations_are_treated_as_unknown():
    """Test that unresolved deferred annotations do not become hard type mismatches."""
    with override_settings(ROOT_URLCONF='tests.dummy_project.urls.future_unresolved_annotations'):
        errors = check_url_signatures(None)
        assert [error.id for error in errors] == ['urlchecker.W003']


def test_future_annotations_are_resolved_for_default_args():
    """Test that deferred annotations are resolved before checking default argument types."""
    with override_settings(ROOT_URLCONF='tests.dummy_project.urls.future_default_args'):
        errors = check_url_signatures(None)
        assert [error.id for error in errors] == ['urlchecker.E005']
        assert "default argument '2024' in urlconf, type str, does not match annotated type int" in errors[0].msg


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
        routes = get_all_routes(resolver, {})
        assert len(list(routes)) == 3


def test_child_urls_checked():
    """Test that child urls are checked.

    Returns:
        None
    """
    with override_settings(ROOT_URLCONF='tests.dummy_project.urls.parent_urls'):
        resolver = get_resolver()
        routes = get_all_routes(resolver, {})
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
    assert get_converter_output_type(converter_urls.YearConverterViaSubclass()) is int
    assert get_converter_output_type(converter_urls.YearConverterAsFloat()) is float
    assert get_converter_output_type(converter_urls.BoolConverter()) is bool

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


def test_untyped_converter_warnings_are_deduplicated_per_class():
    """Emit one W002 warning for each untyped converter class."""
    with override_settings(ROOT_URLCONF="tests.dummy_project.urls.w002_dedup"):
        errors = check_url_signatures(None)

    warning_ids = [error.id for error in errors if error.id.startswith("urlchecker.W002")]
    assert warning_ids == [
        "urlchecker.W002.tests.dummy_project.urls.w002_dedup.SharedUntypedConverter",
        "urlchecker.W002.tests.dummy_project.urls.w002_dedup.FirstUntypedConverter",
        "urlchecker.W002.tests.dummy_project.urls.w002_dedup.SecondUntypedConverter",
    ]


def test_path_kwargs():
    """Test that kwargs specified in path(kwargs=...) are included in analysis."""
    with override_settings(ROOT_URLCONF='tests.dummy_project.urls.path_kwargs_urls'):
        errors = check_url_signatures(None)
        assert len(errors) == 4

        assert error_eql(
            errors[0],
            checks.Error(
                msg="View tests.dummy_project.views.year_archive signature contains `year` parameter "
                "without default or URLconf parameter",
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
                "parameter `year`, can't check type.",
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
    assert len(errors) > 0
    for error in errors:
        assert error.obj.pattern._route.startswith('bad-')


@override_settings(ROOT_URLCONF='tests.dummy_project.urls.parameterized_generics')
def test_parameterized_generics():
    errors = check_url_signatures(None)

    expected = {
        ('urlchecker.E002', 'bad-2-with-val/<path:val>'),
        ('urlchecker.E005', 'bad-2-with-kwarg1/'),
        ('urlchecker.E005', 'bad-2-with-kwarg2/'),
        ('urlchecker.E002', 'bad-tuple-with-val/<path:val>'),
        ('urlchecker.E005', 'bad-tuple-wronglen/'),
        ('urlchecker.E005', 'bad-tuple-wrong-elem/'),
        ('urlchecker.E005', 'bad-tuple-variadic/'),
        ('urlchecker.E005', 'bad-dict/'),
        ('urlchecker.E005', 'bad-set/'),
    }

    seen = {(error.id, error.obj.pattern._route) for error in errors}

    assert seen == expected


@override_settings(ROOT_URLCONF='tests.dummy_project.urls.parameterized_generics')
def test_optional_parameterized_generics_accepts_none_or_list():
    # No errors for optional list when kwargs provide a matching list
    errors = check_url_signatures(None)
    assert not any('optional_list_view' in e.msg for e in errors)


@override_settings(ROOT_URLCONF='tests.dummy_project.urls.parameterized_generics')
def test_container_defaults_match_annotations():
    """Good container defaults should not raise errors."""
    errors = check_url_signatures(None)
    good_routes = {
        'good-2-with-kwarg2/',
        'good-optional-list/',
        'good-tuple-fixed/',
        'good-tuple-variadic/',
        'good-dict/',
        'good-set/',
    }
    error_routes = {e.obj.pattern._route for e in errors}
    assert good_routes.isdisjoint(error_routes)


@override_settings(ROOT_URLCONF='tests.dummy_project.urls.includes')
def test_includes():
    # Positive and negative tests that parameters collected by `path` should be
    # taken into account by routes that are `include`d
    errors = check_url_signatures(None)
    assert len(errors) > 0
    for error in errors:
        assert error.obj.pattern._route.startswith('bad-')


@override_settings(ROOT_URLCONF='tests.dummy_project.urls.annotated_union')
def test_annotated_and_union_annotations():
    """Annotated and Union annotations should be treated as compatible if any member matches."""
    errors = check_url_signatures(None)
    assert errors == []


def _route_semantics_results():
    with override_settings(ROOT_URLCONF="tests.dummy_project.urls.route_semantics"):
        routes = {str(route.pattern.pattern) for route in _walk_routes(get_resolver())}
        errors = check_url_signatures(None)
    grouped = {route: [] for route in routes}
    for error in errors:
        grouped[str(error.obj.pattern)].append(error)
    return routes, grouped


_ROUTE_SEMANTICS_CASES = [
    pytest.param("good/", [], None, id="include-good"),
    pytest.param("wrong-type/", ["urlchecker.E005"], "include() kwargs", id="include-wrong-type"),
    pytest.param("untyped/", ["urlchecker.W003"], "parameter `flag`", id="include-untyped"),
    pytest.param("extra/", ["urlchecker.E006"], "include() kwargs", id="include-extra"),
    pytest.param("nested/", [], None, id="include-nested"),
    pytest.param("child-override/", [], None, id="include-child-override"),
    pytest.param("capture-override/", [], None, id="include-capture-override"),
    pytest.param("parent-ok/", [], None, id="regex-parent-ok"),
    pytest.param("parent-missing/", ["urlchecker.E003"], "does not contain `slug`", id="regex-parent-missing"),
    pytest.param("parent-int/", ["urlchecker.E002"], "expected `str` from urlconf", id="regex-parent-int"),
    pytest.param("child-converter/<int:year>/", [], None, id="regex-parent-child-converter"),
    pytest.param("nested-regex/<int:year>/", [], None, id="regex-nested"),
    pytest.param(r"^regex-leaf/(?P<slug>[-\w]+)/$", [], None, id="re-path-leaf-ok"),
    pytest.param(
        r"^regex-leaf-int/(?P<slug>[-\w]+)/$",
        ["urlchecker.E002"],
        "expected `str` from urlconf",
        id="re-path-leaf-int",
    ),
    pytest.param(
        r"^regex-leaf-missing/(?P<slug>[-\w]+)/$",
        ["urlchecker.E003"],
        "does not contain `slug`",
        id="re-path-leaf-missing",
    ),
    pytest.param(
        r"^regex-leaf-extra/(?P<slug>[-\w]+)/$",
        ["urlchecker.E004"],
        "`missing` parameter",
        id="re-path-leaf-required-extra",
    ),
    pytest.param(
        r"^regex-leaf-untyped/(?P<slug>[-\w]+)/$",
        ["urlchecker.W003"],
        "parameter `slug`",
        id="re-path-leaf-untyped",
    ),
    pytest.param(r"^regex-leaf-extra-value/$", [], None, id="re-path-leaf-extra-kwargs"),
    pytest.param(
        r"^regex-leaf-kwargs/$",
        ["urlchecker.W001"],
        "*args or **kwarg syntax",
        id="re-path-leaf-varkw",
    ),
    pytest.param(r"^positional/(\w+)/(\w+)/$", [], None, id="positional-ok"),
    pytest.param(
        r"^positional-too-many/(\w+)/(\w+)/$",
        ["urlchecker.E007"],
        "receives 2 positional argument(s)",
        id="positional-too-many",
    ),
    pytest.param(
        r"^positional-too-few/(\w+)/$",
        ["urlchecker.E004"],
        "`second` parameter",
        id="positional-too-few",
    ),
    pytest.param(r"^(?P<slug>\w+)/$", [], None, id="parent-positional-dropped-by-child-name"),
    pytest.param(
        r"^positional-star/(\w+)/$",
        ["urlchecker.W001"],
        "*args or **kwarg syntax",
        id="positional-varargs",
    ),
    pytest.param(
        "varkw-mismatch/<int:pk>/",
        ["urlchecker.W001", "urlchecker.E002"],
        "expected `int` from urlconf",
        id="star-varkw-named-parameter",
    ),
    pytest.param(
        "varkw-required/",
        ["urlchecker.W001", "urlchecker.E004"],
        "`required` parameter",
        id="star-varkw-required-parameter",
    ),
    pytest.param(
        "varkw-extra/",
        ["urlchecker.W001"],
        "*args or **kwarg syntax",
        id="star-varkw-unmatched-extra",
    ),
    pytest.param(
        r"^star-varargs-surplus/(\w+)/(\w+)/$",
        ["urlchecker.W001"],
        "*args or **kwarg syntax",
        id="star-varargs-surplus",
    ),
    pytest.param(
        r"^star-varargs-named/(\w+)/$",
        ["urlchecker.W001", "urlchecker.E002"],
        "expected `str` from urlconf",
        id="star-varargs-named-parameter",
    ),
    pytest.param("default-good/<int:pk>/", [], None, id="default-overrides-capture-ok"),
    pytest.param(
        "default-wrong/<int:pk>/",
        ["urlchecker.E005"],
        "default argument 'wrong'",
        id="default-overrides-capture-wrong-type",
    ),
]


@pytest.mark.parametrize("route, expected_ids, message_fragment", _ROUTE_SEMANTICS_CASES)
def test_route_semantics_case(route, expected_ids, message_fragment):
    routes, grouped = _route_semantics_results()
    assert route in routes
    errors = grouped[route]
    assert [error.id for error in errors] == expected_ids
    if message_fragment:
        assert any(message_fragment in error.msg for error in errors)


def test_route_semantics_table_covers_every_fixture_route():
    routes, _ = _route_semantics_results()
    expected_routes = {case.values[0] for case in _ROUTE_SEMANTICS_CASES}
    assert routes == expected_routes


@override_settings(ROOT_URLCONF="tests.dummy_project.urls.route_semantics")
def test_re_path_views_can_be_silenced():
    with override_settings(URLCONFCHECKS_SILENCED_VIEWS={"tests.dummy_project.views.regex_slug_int_view": "E002"}):
        errors = check_url_signatures(None)
    assert not any("regex_slug_int_view" in error.msg and error.id == "urlchecker.E002" for error in errors)


@override_settings(ROOT_URLCONF="tests.dummy_project.urls.regex_optional")
def test_optional_regex_groups_warn_only_without_a_view_default():
    errors = check_url_signatures(None)
    assert [error.id for error in errors] == ["urlchecker.W004"]
    assert "parameter `page` is captured by an optional regex group but has no default" in errors[0].msg


@override_settings(ROOT_URLCONF="tests.dummy_project.urls.i18n_routes")
def test_i18n_patterns_with_include_do_not_crash():
    assert check_url_signatures(None) == []


@override_settings(ROOT_URLCONF="tests.dummy_project.urls.route_clean_urls")
def test_clean_routes_resolve_and_call_without_type_error():
    assert check_url_signatures(None) == []
    request_factory = RequestFactory()
    for url in ("/include/", "/regex/example/", "/positional/one/two/", "/default/7/"):
        match = resolve(url)
        match.func(request_factory.get(url), *match.args, **match.kwargs)


def test_regex_optional_group_parser_handles_alternatives():
    import re

    regex = re.compile(r"^(?:foo(?P<first>\d+)|bar(?P<second>\d+))?$")
    assert _optional_regex_groups(regex) == {1, 2}


def test_legacy_checker_and_type_helpers_cover_edge_cases():
    def no_parameters():
        return None

    pattern = URLPattern(RoutePattern("none/"), no_parameters)
    errors = check_url_args_match(pattern, {})
    assert [error.id for error in errors] == ["urlchecker.E001"]
    assert not _type_is_compatible(__import__("inspect").Parameter.empty, str)
    assert _type_is_compatible(str, object)
    assert _instance_is_compatible("value", object)


def test_checker_handles_missing_root_urlconf_and_non_urlpattern_entries():
    with override_settings(ROOT_URLCONF=None):
        assert check_url_signatures(None) == []

    from django_urlconfchecks.check import _walk_routes

    resolver = t.cast(URLResolver, type("Resolver", (), {"url_patterns": [object()]})())
    assert list(_walk_routes(resolver)) == []


def test_callable_globals_resolves_bound_methods():
    class Example:
        def method(self):
            return None

    assert _get_callable_globals(Example().method) == globals()
