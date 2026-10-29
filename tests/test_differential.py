"""Deterministic differential test: the checker must agree with Django's resolver and call path.

Each case builds a random view signature and a random route (path converters, named or unnamed
regex groups, parent captures through include(), include() and path() kwargs), resolves a real URL
and calls the view. Signature errors must be reported exactly when the call raises TypeError.
"""

import sys
import types
import uuid

from django.http import HttpResponse
from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import clear_url_caches, include, path, re_path, resolve
from hypothesis import given, settings
from hypothesis import strategies as st

from django_urlconfchecks.check import check_url_signatures

SIGNATURE_ERRORS = {"urlchecker.E001", "urlchecker.E003", "urlchecker.E004", "urlchecker.E006", "urlchecker.E007"}
PARAM_NAMES = ("c0", "c1", "c2", "p", "k", "e", "z")
KINDS = ("positional_only", "positional", "keyword_only")


@st.composite
def _cases(draw):
    request_mode = draw(st.sampled_from(("positional", "positional", "positional", "keyword_only", "missing")))
    params = []
    for name in draw(st.lists(st.sampled_from(PARAM_NAMES), unique=True, max_size=5)):
        # Without a positional `request`, positional params would receive the request under another
        # name, which the checker flags by name (E001) on purpose; keep those cases out.
        kind = draw(st.sampled_from(KINDS)) if request_mode == "positional" else "keyword_only"
        params.append((name, kind, draw(st.booleans())))
    return {
        "request_mode": request_mode,
        "params": params,
        "varargs": draw(st.booleans()),
        "varkw": draw(st.booleans()),
        "route": draw(st.sampled_from(("path", "named_regex", "positional_regex"))),
        "captures": draw(st.integers(min_value=0, max_value=3)),
        "parent": draw(st.sampled_from((None, "path", "named_regex", "positional_regex"))),
        "include_kwargs": draw(st.sampled_from(({}, {"k": 1}, {"c0": 1}))),
        "path_kwargs": draw(st.sampled_from(({}, {"e": 1}, {"c1": 1}))),
    }


def _signature_source(case):
    positional_only, positional, keyword_only = [], [], []
    for name, kind, has_default in case["params"]:
        {"positional_only": positional_only, "positional": positional, "keyword_only": keyword_only}[kind].append(
            (name, has_default)
        )
    if case["request_mode"] == "positional":
        (positional_only or positional).insert(0, ("request", False))
    elif case["request_mode"] == "keyword_only":
        keyword_only.insert(0, ("request", False))

    # Positional parameters after a defaulted one must have defaults too.
    rendered, defaulted = [], False
    for name, has_default in positional_only + positional:
        defaulted = defaulted or has_default
        rendered.append(f"{name}=1" if defaulted else name)
    if positional_only:
        rendered.insert(len(positional_only), "/")
    if case["varargs"]:
        rendered.append("*args")
    elif keyword_only:
        rendered.append("*")
    rendered += [f"{name}=1" if has_default else name for name, has_default in keyword_only]
    if case["varkw"]:
        rendered.append("**kwargs")
    return ", ".join(rendered)


def _leaf(case, view):
    count, names = case["captures"], [f"c{i}" for i in range(case["captures"])]
    if case["route"] == "path":
        route, pattern = "".join(f"<int:{name}>/" for name in names), path
    elif case["route"] == "named_regex":
        route, pattern = "^" + "".join(f"(?P<{name}>[0-9]+)/" for name in names) + "$", re_path
    else:
        route, pattern = "^" + "([0-9]+)/" * count + "$", re_path
    return pattern(f"leaf/{route}" if pattern is path else route.replace("^", "^leaf/", 1), view, case["path_kwargs"])


def _urlpatterns(case, view):
    leaf = _leaf(case, view)
    leaf_url = "leaf/" + "3/" * case["captures"]
    parent, include_kwargs = case["parent"], case["include_kwargs"]
    if parent is None and not include_kwargs:
        return [leaf], "/" + leaf_url
    if parent == "path":
        parent_pattern, parent_url = path("p/<int:p>/", include([leaf]), include_kwargs), "p/2/"
    elif parent == "named_regex":
        parent_pattern, parent_url = re_path(r"^p/(?P<p>[0-9]+)/", include([leaf]), include_kwargs), "p/2/"
    elif parent == "positional_regex":
        parent_pattern, parent_url = re_path(r"^p/([0-9]+)/", include([leaf]), include_kwargs), "p/2/"
    else:
        parent_pattern, parent_url = path("p/", include([leaf]), include_kwargs), "p/"
    return [parent_pattern], "/" + parent_url + leaf_url


def _run_case(case):
    module_name = f"tests._differential_{uuid.uuid4().hex}"
    namespace = {"HttpResponse": HttpResponse, "__name__": module_name}
    source = _signature_source(case)
    exec(f"def view({source}):\n    return HttpResponse()", namespace)
    urlpatterns, url = _urlpatterns(case, namespace["view"])

    module = types.ModuleType(module_name)
    module.__dict__["urlpatterns"] = urlpatterns
    sys.modules[module_name] = module
    try:
        with override_settings(ROOT_URLCONF=module_name, URLCONFCHECKS_SILENCED_VIEWS={}):
            clear_url_caches()
            errors = check_url_signatures(None)
            match = resolve(url)
            try:
                match.func(RequestFactory().get(url), *match.args, **match.kwargs)
                runtime_error = None
            except TypeError as exc:
                runtime_error = str(exc)
    finally:
        clear_url_caches()
        sys.modules.pop(module_name, None)

    reported = sorted(error.id for error in errors if error.id in SIGNATURE_ERRORS)
    assert bool(reported) == (runtime_error is not None), (
        f"def view({source}) at {url}: checker reported {reported}, Django call raised {runtime_error!r}"
    )


@settings(derandomize=True, max_examples=500, deadline=None)
@given(_cases())
def test_checker_matches_django_argument_binding(case):
    _run_case(case)
