"""Tests for Django and Django REST framework class-based view checks."""

import pytest
from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import resolve

from django_urlconfchecks.check import check_url_signatures


def _errors_by_route(errors):
    grouped = {}
    for error in errors:
        grouped.setdefault(str(error.obj.pattern), []).append(error)
    return grouped


_P = "tests.dummy_project.cbv_views."

# (leaf route as str(pattern), expected problem ids in order, message fragments)
CBV_HANDLER_CASES = [
    pytest.param("clean/<int:pk>/", [], [], id="clean-get-inherited-and-post"),
    pytest.param("<int:pk>/", [], [], id="include-kwargs-reach-handler"),
    pytest.param(
        "bad/<int:pk>/",
        ["urlchecker.E002", "urlchecker.E003"],
        [f"{_P}BadView.get for parameter `pk`", f"{_P}BadView.post signature does not contain `pk`"],
        id="faulty-get-and-post-reported-separately",
    ),
    pytest.param("no-request/<int:pk>/", ["urlchecker.E001"], [f"{_P}NoRequestView.get signature"], id="no-request"),
    pytest.param(
        "required/<int:pk>/", ["urlchecker.E004"], ["`required` parameter without default"], id="extra-required"
    ),
    pytest.param("star/<int:pk>/", ["urlchecker.E002"], [f"{_P}StarView.get"], id="star-args-named-param-checked"),
    pytest.param("dispatch/<int:pk>/", ["urlchecker.E002"], [f"{_P}DispatchView.dispatch"], id="explicit-dispatch"),
    pytest.param("head/<int:pk>/", ["urlchecker.E002"], [f"{_P}ExplicitHeadView.head"], id="explicit-head"),
    pytest.param("async/<int:pk>/", ["urlchecker.E002"], [f"{_P}AsyncView.post"], id="async-handlers"),
    pytest.param(
        "inherited-bad/<int:pk>/",
        ["urlchecker.E003"],
        [f"View {_P}InheritedBadView.get signature does not contain `pk`"],
        id="inherited-handler-reported-under-url-class",
    ),
    pytest.param("extra/", ["urlchecker.E005"], [f"{_P}ExtraView.get: for parameter `flag`"], id="path-kwargs"),
    pytest.param(
        r"^regex/(?P<pk>\d+)/$",
        ["urlchecker.E002", "urlchecker.E002"],
        [f"{_P}CleanView.get", f"{_P}CleanView.post"],
        id="re-path-captures-are-str",
    ),
]


@pytest.fixture
def cbv_handler_problems():
    with override_settings(
        ROOT_URLCONF="tests.dummy_project.urls.cbv_handler_urls",
        URLCONFCHECKS_SILENCED_VIEWS={},
    ):
        return _errors_by_route(check_url_signatures(None))


@pytest.mark.parametrize("route, expected_ids, fragments", CBV_HANDLER_CASES)
def test_cbv_handler_case(cbv_handler_problems, route, expected_ids, fragments):
    problems = cbv_handler_problems.get(route, [])
    assert [problem.id for problem in problems] == expected_ids
    for problem, fragment in zip(problems, fragments, strict=True):
        assert fragment in problem.msg


def test_cbv_handler_cases_cover_every_fixture_route():
    from tests.dummy_project.urls import cbv_handler_urls

    def leaf_routes(patterns):
        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):
                yield from leaf_routes(pattern.url_patterns)
            else:
                yield str(pattern.pattern)

    assert sorted(leaf_routes(cbv_handler_urls.urlpatterns)) == sorted(
        str(case.values[0]) for case in CBV_HANDLER_CASES
    )


def test_cbv_handlers_never_get_w001_or_implicit_head(cbv_handler_problems):
    problems = [problem for problems in cbv_handler_problems.values() for problem in problems]
    assert not any(problem.id == "urlchecker.W001" for problem in problems)
    assert not any(f"{_P}BadView.head" in problem.msg for problem in problems)


@override_settings(
    ROOT_URLCONF="tests.dummy_project.urls.cbv_generic_urls",
    URLCONFCHECKS_SILENCED_VIEWS={},
)
def test_django_generic_views_do_not_produce_new_messages():
    assert check_url_signatures(None) == []


@override_settings(ROOT_URLCONF="tests.dummy_project.urls.cbv_handler_urls")
def test_cbv_handler_silencing_supports_methods_and_classes():
    bad_get = "tests.dummy_project.cbv_views.BadView.get"
    bad_class = "tests.dummy_project.cbv_views.BadView"

    with override_settings(URLCONFCHECKS_SILENCED_VIEWS={bad_get: "E002"}):
        errors = check_url_signatures(None)
        assert [error.id for error in errors if ".BadView." in error.msg] == ["urlchecker.E003"]

    with override_settings(URLCONFCHECKS_SILENCED_VIEWS={f"{bad_class}.*": "E002,E003"}):
        errors = check_url_signatures(None)
        assert not any(".BadView." in error.msg for error in errors)

    with override_settings(URLCONFCHECKS_SILENCED_VIEWS={bad_class: "E002,E003"}):
        errors = check_url_signatures(None)
        assert not any(".BadView." in error.msg for error in errors)


@override_settings(ROOT_URLCONF="tests.dummy_project.urls.cbv_handler_urls")
def test_cbv_routes_resolve_and_bad_handler_raises_type_error():
    request_factory = RequestFactory()
    clean = resolve("/clean/7/")
    clean.func(request_factory.get("/clean/7/"), *clean.args, **clean.kwargs)
    clean_post = resolve("/clean/7/")
    clean_post.func(request_factory.post("/clean/7/"), *clean_post.args, **clean_post.kwargs)

    bad = resolve("/bad/7/")
    with pytest.raises(TypeError):
        bad.func(request_factory.post("/bad/7/"), *bad.args, **bad.kwargs)

    required = resolve("/required/7/")
    with pytest.raises(TypeError):
        required.func(request_factory.get("/required/7/"), *required.args, **required.kwargs)


def test_drf_cbv_handlers_and_viewset_actions():
    pytest.importorskip("rest_framework")
    with override_settings(
        ROOT_URLCONF="tests.dummy_project.urls.drf_cbv_urls",
        URLCONFCHECKS_SILENCED_VIEWS={},
    ):
        grouped = _errors_by_route(check_url_signatures(None))
    assert [error.id for error in grouped["bad/<int:pk>/"]] == ["urlchecker.E002"]
    assert [error.id for error in grouped["^bad/(?P<pk>[^/.]+)/$"]] == ["urlchecker.E002"]
    broken_action = grouped["^bad/(?P<pk>[^/.]+)/broken/$"]
    assert [error.id for error in broken_action] == ["urlchecker.E003"]
    assert "BadViewSet.broken signature does not contain `pk`" in broken_action[0].msg
    assert not any(
        "ArticleAPIView" in error.msg or "ArticleViewSet" in error.msg
        for errors in grouped.values()
        for error in errors
    )
