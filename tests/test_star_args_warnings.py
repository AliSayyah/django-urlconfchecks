"""W001 (view takes *args/**kwargs) is reported once per view, with a hint."""

import functools
import sys
import types
import uuid

from django.http import HttpResponse
from django.test.utils import override_settings
from django.urls import clear_url_caches, include, path

from django_urlconfchecks.check import check_url_signatures


def _check(patterns, silenced=None):
    name = f"tests._star_args_{uuid.uuid4().hex}"
    module = types.ModuleType(name)
    module.__dict__["urlpatterns"] = patterns
    sys.modules[name] = module
    try:
        with override_settings(ROOT_URLCONF=name, URLCONFCHECKS_SILENCED_VIEWS=silenced or {}):
            clear_url_caches()
            return check_url_signatures(None)
    finally:
        clear_url_caches()
        sys.modules.pop(name, None)


def permission_required(view):
    """A decorator without functools.wraps, like many real-world permission decorators."""

    def wrapper(request, *args, **kwargs):
        return view(request, *args, **kwargs)

    return wrapper


def wrapped_permission_required(view):
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        return view(request, *args, **kwargs)

    return wrapper


@permission_required
def detail(request, pk: int):
    return HttpResponse()


@permission_required
def edit(request, pk: int):
    return HttpResponse()


def forwarding(request, *args, **kwargs):
    return HttpResponse()


def named_and_star(request, pk: str, **kwargs):
    return HttpResponse()


WRAPPER = f"{__name__}.permission_required.<locals>.wrapper"


def test_one_w001_per_view_with_route_count():
    problems = _check(
        [
            path("a/<int:pk>/", detail),
            path("b/<int:pk>/", edit),
            path("c/", include([path("<int:pk>/", detail)])),
        ]
    )
    assert [p.id for p in problems] == ["urlchecker.W001"]
    assert problems[0].msg == (
        f"View {WRAPPER} signature contains *args or **kwarg syntax, can't properly check args (used by 3 routes)"
    )
    assert str(problems[0].obj.pattern) == "a/<int:pk>/"


def test_w001_hint_suggests_functools_wraps_and_a_package_glob():
    (problem,) = _check([path("a/<int:pk>/", detail)])
    assert "(used by" not in problem.msg
    assert "functools.wraps" in problem.hint
    assert '{"tests.*": "W001"}' in problem.hint


def test_different_views_get_separate_warnings():
    problems = _check([path("a/<int:pk>/", detail), path("f/", forwarding), path("g/", forwarding)])
    assert [p.id for p in problems] == ["urlchecker.W001", "urlchecker.W001"]
    assert WRAPPER in problems[0].msg and "(used by 2 routes)" not in problems[0].msg
    assert f"{__name__}.forwarding signature" in problems[1].msg and problems[1].msg.endswith("(used by 2 routes)")


def test_silenced_view_is_not_reported_or_counted():
    problems = _check([path("a/<int:pk>/", detail), path("b/<int:pk>/", edit)], silenced={f"{__name__}.*": "W001"})
    assert problems == []


def test_other_problems_on_star_args_views_stay_per_route():
    problems = _check([path("a/<int:pk>/", named_and_star), path("b/<int:pk>/", named_and_star)])
    assert [p.id for p in problems] == ["urlchecker.W001", "urlchecker.E002", "urlchecker.E002"]
    assert problems[0].msg.endswith("(used by 2 routes)")
    assert [str(p.obj.pattern) for p in problems[1:]] == ["a/<int:pk>/", "b/<int:pk>/"]


def test_decorator_with_functools_wraps_is_checked_through():
    """What the hint promises: with functools.wraps the real view signature is checked."""

    @wrapped_permission_required
    def view(request, pk: str):
        return HttpResponse()

    problems = _check([path("a/<int:pk>/", view)])
    assert [p.id for p in problems] == ["urlchecker.E002"]
