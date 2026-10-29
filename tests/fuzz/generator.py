"""Shared case generation for the CLI fuzzer and the Hypothesis test.

The generator only depends on the small chooser protocol below.  This keeps the
shape of generated cases identical for a seeded CLI run and for Hypothesis while
still allowing Hypothesis to shrink individual choices.  Cases are built with
ordinary Django URL objects so the oracle exercises the same resolver code used
by applications.
"""

from __future__ import annotations

import functools
import re
import uuid
from dataclasses import dataclass, replace
from typing import Annotated, Any, Literal, NewType, Protocol, TypeVar, cast

from django.http import HttpResponse
from django.urls import include, path, re_path, register_converter
from django.views import View

UserId = NewType("UserId", int)
UserName = NewType("UserName", str)
UserUUID = NewType("UserUUID", uuid.UUID)
BoundInt = TypeVar("BoundInt", bound=int)
BoundStr = TypeVar("BoundStr", bound=str)
BoundUUID = TypeVar("BoundUUID", bound=uuid.UUID)

_SOURCE_IMPORTS = (
    "from typing import Annotated, Any, Literal, NewType, TypeVar\n"
    "import uuid\n"
    "UserId = NewType('UserId', int)\n"
    "UserName = NewType('UserName', str)\n"
    "UserUUID = NewType('UserUUID', uuid.UUID)\n"
    "BoundInt = TypeVar('BoundInt', bound=int)\n"
    "BoundStr = TypeVar('BoundStr', bound=str)\n"
    "BoundUUID = TypeVar('BoundUUID', bound=uuid.UUID)\n"
)


class Chooser(Protocol):
    """The choices needed by :func:`generate_case`."""

    def choose(self, options: tuple[Any, ...]) -> Any:
        """Choose one item."""

    def integer(self, low: int, high: int) -> int:
        """Choose an integer in the inclusive range."""

    def boolean(self) -> bool:
        """Choose a boolean."""


class RandomChooser:
    """Adapter around :class:`random.Random`."""

    def __init__(self, random):
        self.random = random

    def choose(self, options):
        return self.random.choice(options)

    def integer(self, low, high):
        return self.random.randint(low, high)

    def boolean(self):
        return bool(self.random.getrandbits(1))


class HypothesisChooser:
    """Adapter around a Hypothesis ``st.data()`` object."""

    def __init__(self, data):
        self.data = data

    def choose(self, options):
        from hypothesis import strategies as st

        return self.data.draw(st.sampled_from(options))

    def integer(self, low, high):
        from hypothesis import strategies as st

        return self.data.draw(st.integers(min_value=low, max_value=high))

    def boolean(self):
        from hypothesis import strategies as st

        return self.data.draw(st.booleans())


@dataclass(frozen=True)
class Case:
    """A fully built URLconf and its source-level reproduction."""

    name: str
    urlpatterns: list[Any]
    variants: tuple[str, ...]
    view_source: str
    urlpatterns_source: str
    shape: str
    expected_type_mismatch: bool = False
    type_checkable: bool = True
    binding_checkable: bool = True
    calls: tuple[tuple[str, str], ...] = ()
    target_pattern: Any = None


@dataclass(frozen=True)
class _Spec:
    family: str
    route: str
    captures: tuple[str, ...]
    nesting: int
    include_style: str
    extra: bool
    optional_default: bool
    signature: str
    annotation: str
    decorate: str
    async_view: bool
    type_mismatch: bool
    request_mode: str
    view_names: tuple[str, ...]
    positional_only: tuple[str, ...]
    positional: tuple[str, ...]
    keyword_only: tuple[str, ...]
    defaults: tuple[str, ...]
    extra_names: tuple[str, ...]
    include_kw_name: str | None
    path_kw_name: str | None
    cbv_handlers: tuple[str, ...]
    cbv_setup: bool
    cbv_dispatch: bool
    cbv_descriptor: str
    cbv_mixin: bool
    drf_style: str
    drf_route: str
    drf_format: bool


_ROUTES = (
    "static",
    "int",
    "str",
    "slug",
    "uuid",
    "path",
    "custom",
    "named",
    "unnamed",
    "optional",
    "alt",
    "lookaround",
)
_SIGNATURES = ("normal", "defaults", "positional_only", "keyword_only_extra", "varargs", "varkw", "both")
_ANNOTATIONS = (
    "native",
    "optional",
    "union",
    "any",
    "object",
    "literal",
    "newtype",
    "typevar",
    "annotated",
    "string",
    "list",
)


def generate_case(chooser: Chooser) -> Case:
    """Choose and build one case using the supplied chooser."""
    route = chooser.choose(_ROUTES)
    family = chooser.choose(_families())
    route = "int" if family == "drf" else route
    captures = _capture_names(route, chooser)
    spec = _choose_spec(chooser, family, route, captures)
    return _build(spec)


def _families():
    """Return available view families, including DRF when installed."""
    families = ("function", "function", "function", "cbv", "async", "decorated", "partial")
    try:
        import rest_framework  # noqa: F401
    except ImportError as exc:
        del exc
        return families
    return families + ("drf",)


def _capture_names(route: str, chooser: Chooser) -> tuple[str, ...]:
    """Choose the number of captures that a route can safely contain."""
    if route == "static":
        count = 0
    elif route in {"path", "custom", "optional", "alt", "lookaround"}:
        count = 1
    else:
        count = chooser.integer(1, 2)
    return tuple(f"p{i}" for i in range(count))


def _choose_spec(chooser: Chooser, family: str, route: str, captures: tuple[str, ...]) -> _Spec:
    """Choose the remaining dimensions of one case."""
    nesting = chooser.integer(0, 3)
    view_names, include_kw_name, path_kw_name = _choose_route_names(chooser, captures, nesting)
    request_mode, positional_only, positional, keyword_only = _choose_parameter_kinds(chooser, view_names)
    extra_names = tuple(f"extra{index}" for index in range(chooser.integer(0, 2)))
    spec = _Spec(
        family=family,
        route=route,
        captures=captures,
        nesting=nesting,
        include_style=chooser.choose(("list", "tuple")),
        extra=chooser.boolean(),
        optional_default=chooser.boolean(),
        signature=chooser.choose(_SIGNATURES),
        annotation=chooser.choose(_ANNOTATIONS),
        decorate=chooser.choose(("none", "wraps", "opaque")),
        async_view=chooser.boolean(),
        type_mismatch=chooser.boolean() if route not in {"static", "lookaround"} else False,
        request_mode=request_mode,
        view_names=view_names,
        positional_only=positional_only,
        positional=positional,
        keyword_only=keyword_only,
        defaults=tuple(name for name in view_names + extra_names if chooser.boolean()),
        extra_names=extra_names,
        include_kw_name=include_kw_name,
        path_kw_name=path_kw_name,
        cbv_handlers=chooser.choose((("get",), ("post",), ("get", "post"))),
        cbv_setup=chooser.boolean(),
        cbv_dispatch=chooser.boolean(),
        cbv_descriptor=chooser.choose(("normal", "staticmethod", "classmethod", "callable")),
        cbv_mixin=chooser.boolean(),
        drf_style=chooser.choose(("api", "router")),
        drf_route=chooser.choose(("list", "retrieve", "action_detail", "action_collection")),
        drf_format=chooser.boolean(),
    )
    if spec.decorate == "opaque":
        spec = replace(spec, signature="both", optional_default=True)
    if spec.family == "partial" and route in {"optional", "alt"}:
        spec = replace(spec, optional_default=True)
    if spec.family != "cbv":
        spec = replace(spec, cbv_handlers=("get",), cbv_setup=False, cbv_dispatch=False)
    if spec.family != "drf":
        spec = replace(spec, drf_style="api")
    return spec


def _choose_route_names(chooser, captures, nesting):
    """Choose route kwargs and the explicit names retained by the view."""
    route_names = list(captures) + [f"parent{index}" for index in range(nesting)]
    include_kw_name = chooser.choose((None, None, "extra", "p0", "parent0")) if nesting else None
    path_kw_name = chooser.choose((None, None, "path_extra", "p0", "parent0"))
    for name in (include_kw_name, path_kw_name):
        if name and name not in route_names:
            route_names.append(name)
    return tuple(name for name in route_names if chooser.boolean()), include_kw_name, path_kw_name


def _choose_parameter_kinds(chooser, view_names):
    """Choose request placement and parameter kinds."""
    request_mode = chooser.choose(("positional", "positional_only", "keyword_only", "varargs_only", "varkw_only"))
    positional_only = _choose_positional_only(chooser, view_names, request_mode)
    positional = _choose_positional(chooser, view_names, request_mode, positional_only)
    keyword_only = _choose_keyword_only(view_names, request_mode, positional_only, positional)
    return request_mode, positional_only, positional, keyword_only


def _choose_positional_only(chooser, names, request_mode):
    """Choose positional-only names."""
    return tuple(name for name in names if request_mode == "positional_only" and chooser.boolean())


def _choose_positional(chooser, names, request_mode, positional_only):
    """Choose positional-or-keyword names."""
    if request_mode in {"keyword_only", "varargs_only", "varkw_only"}:
        return ()
    return tuple(name for name in names if name not in positional_only and chooser.boolean())


def _choose_keyword_only(names, request_mode, positional_only, positional):
    """Choose keyword-only names."""
    if request_mode == "keyword_only":
        return names
    if request_mode in {"varargs_only", "varkw_only"}:
        return ()
    return tuple(name for name in names if name not in positional_only and name not in positional)


def _build(spec: _Spec) -> Case:
    if spec.family == "drf" and spec.drf_style == "router":
        return _build_drf_router(spec)
    names = spec.captures
    annotation = _annotation(spec.annotation, spec.route, spec.type_mismatch)
    parameter_names = list(spec.view_names) + list(spec.extra_names)
    annotated = [(name, annotation if name in names else "int") for name in parameter_names]
    signature = _signature(spec, annotated, spec.optional_default or spec.nesting == 0)
    view, view_source = _make_view(spec, annotated, signature)
    leaf, leaf_url, leaf_source = _leaf(spec, view)
    patterns, source_expr, url_prefix = _wrap_patterns(spec, leaf, leaf_source)
    variants = _variants(spec, "".join(reversed(url_prefix)), leaf_url)
    shape = _shape(spec, len(names))
    expected_type_mismatch = _expected_type_mismatch(spec)
    type_checkable = _type_checkable(spec)
    calls = tuple((url, method) for url in variants for method in _methods(spec))
    return Case(
        "generated",
        patterns,
        tuple(variants),
        view_source,
        "from django.urls import include, path, re_path\nurlpatterns = " + source_expr,
        shape,
        expected_type_mismatch,
        type_checkable,
        spec.decorate != "opaque",
        calls,
        leaf,
    )


def _build_drf_router(spec: _Spec) -> Case:
    """Build one randomly selected route from a registered DRF router."""
    from rest_framework import response, routers, viewsets
    from rest_framework.decorators import action
    from rest_framework.urlpatterns import format_suffix_patterns

    class FuzzSet(viewsets.ViewSet):
        def list(self, request):
            return response.Response()

        def retrieve(self, request, pk):
            return response.Response()

        @action(detail=True, methods=["get"], url_path=r"items/(?P<item>[0-9]+)")
        def item(self, request, pk, item):
            return response.Response()

        @action(detail=False, methods=["get"], url_path="summary")
        def summary(self, request):
            return response.Response()

    router = routers.SimpleRouter()
    router.register("fuzz", FuzzSet, basename="fuzz")
    patterns = format_suffix_patterns(router.urls) if spec.drf_format else router.urls
    wanted = {
        "list": "fuzz-list",
        "retrieve": "fuzz-detail",
        "action_detail": "fuzz-item",
        "action_collection": "fuzz-summary",
    }[spec.drf_route]
    target = next((pattern for pattern in patterns if pattern.name == wanted), patterns[0])
    route_text = str(target.pattern)
    if spec.drf_route == "list":
        url = "/fuzz/"
    elif spec.drf_route == "retrieve":
        url = "/fuzz/1/"
    elif spec.drf_route == "action_detail":
        url = "/fuzz/1/items/2/"
    else:
        url = "/fuzz/summary/"
    if spec.drf_format:
        url = url.rstrip("/") + ".json/"
    source = (
        "from rest_framework import response, routers, viewsets\n"
        "from rest_framework.decorators import action\n\n"
        "class FuzzSet(viewsets.ViewSet):\n"
        "    def list(self, request): return response.Response()\n"
        "    def retrieve(self, request, pk): return response.Response()\n"
        "    @action(detail=True, methods=['get'], url_path=r'items/(?P<item>[0-9]+)')\n"
        "    def item(self, request, pk, item): return response.Response()\n"
        "    @action(detail=False, methods=['get'], url_path='summary')\n"
        "    def summary(self, request): return response.Response()\n"
        "router = routers.SimpleRouter(); router.register('fuzz', FuzzSet, basename='fuzz')\n"
        "urlpatterns = router.urls\n"
    )
    shape = f"drf:router:{spec.drf_route}:{spec.drf_format}:{route_text}"
    return Case(
        "generated-drf-router",
        [target],
        (url,),
        source,
        source,
        shape,
        False,
        True,
        True,
        ((url, "GET"),),
        target,
    )


def _methods(spec: _Spec) -> tuple[str, ...]:
    """Return HTTP methods exercised by this case."""
    if spec.family == "cbv":
        return tuple(name.upper() for name in spec.cbv_handlers)
    if spec.family == "drf" and spec.drf_route in {"action_detail", "action_collection"}:
        return ("GET", "POST")
    return ("GET",)


def _make_view(spec: _Spec, annotated: list[tuple[str, str]], signature: str):
    """Create a callback and source text for a view family."""
    view_source = _view_source(signature, spec.async_view)
    namespace: dict[str, Any] = {
        "HttpResponse": HttpResponse,
        "uuid": uuid,
        "re": re,
        "Any": Any,
        "Literal": Literal,
        "Annotated": Annotated,
        "UserId": UserId,
        "UserName": UserName,
        "UserUUID": UserUUID,
        "BoundInt": BoundInt,
        "BoundStr": BoundStr,
        "BoundUUID": BoundUUID,
    }
    # The exec is deliberately limited to generated view definitions.  It is the
    # same mechanism applications use for annotations with forward references.
    exec(view_source, namespace)  # noqa: S102
    view = namespace["view"]
    view.__module__ = "tests.fuzz.generated"
    view = _decorate(view, spec.decorate)
    if spec.family == "partial":
        view = functools.partial(view)
    if spec.family == "cbv":
        view, view_source = _cbv_view(spec, annotated, spec.optional_default or spec.nesting == 0)
    if spec.family == "drf":
        view, view_source = _drf_view(spec, annotated, spec.optional_default or spec.nesting == 0)
    if spec.family == "async":
        view_source = _view_source(signature, True)
        exec(view_source, namespace)  # noqa: S102
        view = namespace["view"]
        view.__module__ = "tests.fuzz.generated"
    if spec.family == "decorated":
        view = _decorate(view, "wraps")
    try:
        view.__module__ = "tests.fuzz.generated"
    except Exception as exc:
        del exc

    return view, view_source


def _wrap_patterns(spec: _Spec, leaf, leaf_source: str):
    """Wrap a leaf pattern in the requested include depth."""
    patterns: list[Any] = [leaf]
    url_prefix: list[str] = []
    source_expr = f"[{leaf_source}]"
    for level in range(spec.nesting):
        name = f"parent{level}"
        capture = f"<int:{name}>/"
        if spec.include_style == "tuple" and level == 0:
            target: Any = (patterns, f"app{level}")
            target_source = f"({source_expr}, 'app{level}')"
        else:
            target = patterns
            target_source = source_expr
        if level == 0 and spec.include_kw_name:
            parent = path(capture, include(target), {spec.include_kw_name: 3})
            source = f"path({capture!r}, include({target_source}), {{{spec.include_kw_name!r}: 3}})"
        else:
            parent = path(capture, include(target))
            source = f"path({capture!r}, include({target_source}))"
        patterns = [parent]
        url_prefix.append(f"{level + 2}/")
        source_expr = f"[{source}]"

    return patterns, source_expr, url_prefix


def _shape(spec: _Spec, count: int) -> str:
    """Describe the structural dimensions used for mismatch de-duplication."""
    return f"{spec.family}:{spec.route}:{count}:{spec.nesting}:{spec.signature}:{spec.extra}:{spec.optional_default}"


def _expected_type_mismatch(spec: _Spec) -> bool:
    """Return whether the generated annotation is an intentional type violation."""
    view_names = _effective_view_names(spec)
    route_mismatch = _route_type_mismatch(spec, view_names)
    return route_mismatch or _kwarg_type_mismatch(spec, view_names)


def _effective_view_names(spec):
    """Return names that are explicit in the generated signature."""
    if spec.request_mode in {"varargs_only", "varkw_only"}:
        return set()
    return set(spec.view_names) | set(spec.extra_names)


def _route_type_mismatch(spec, view_names):
    """Check converter and regex values against generated annotations."""
    mismatch = spec.type_mismatch or spec.annotation in {"list", "string"}
    if spec.route == "unnamed":
        return bool(spec.positional or spec.positional_only) and mismatch
    route_names = (set(spec.captures) - {spec.path_kw_name}) & view_names - set(spec.positional_only)
    return (
        bool(route_names) and mismatch or (spec.route == "uuid" and spec.annotation == "literal" and bool(route_names))
    )


def _kwarg_type_mismatch(spec, view_names):
    """Check integer values supplied by path/include kwargs."""
    for name in (spec.include_kw_name, spec.path_kw_name):
        if not name or name not in view_names:
            continue
        expected = "int" if name.startswith(("parent", "extra")) else _expected_annotation(spec.route)
        if not _annotation_accepts_integer(spec.annotation, expected, spec.type_mismatch):
            return True
    return False


def _annotation_accepts_integer(mode: str, expected: str, forced_mismatch: bool) -> bool:
    """Return whether a generated annotation accepts an integer extra value."""
    if forced_mismatch and expected != "int":
        return True
    if mode in {"any", "object", "union"}:
        return True
    if expected == "int" and mode in {"native", "optional", "newtype", "typevar", "annotated", "literal"}:
        return True
    return False


def _type_checkable(spec: _Spec) -> bool:
    """Return whether this signature permits a meaningful type comparison."""
    if spec.family != "function" or spec.decorate != "none":
        return False
    if spec.include_kw_name or spec.path_kw_name or spec.request_mode != "positional":
        return False
    if spec.signature in {"positional_only", "varargs", "varkw", "both"}:
        return False
    return not (spec.route == "unnamed" and spec.signature == "keyword_only_extra")


def _annotation(mode: str, route: str, mismatch: bool) -> str:
    expected = _expected_annotation(route)
    if mismatch:
        return "str" if expected == "int" else "int"
    forms = {
        "native": expected,
        "optional": f"{expected} | None",
        "union": f"int | {expected}" if expected != "int" else "int | str",
        "any": "Any",
        "object": "object",
        "literal": "Literal[1, 2]" if expected == "int" else "Literal['abc']",
        "newtype": "UserId" if expected == "int" else ("UserUUID" if expected == "uuid.UUID" else "UserName"),
        "typevar": "BoundInt" if expected == "int" else ("BoundUUID" if expected == "uuid.UUID" else "BoundStr"),
        "annotated": f"Annotated[{expected}, 'fuzz']",
        "string": repr(expected),
        "list": "list[int]",
    }
    return forms[mode]


def _expected_annotation(route: str) -> str:
    """Return the type emitted by a route family."""
    if route == "uuid":
        return "uuid.UUID"
    if route in {"str", "slug", "path", "named", "unnamed", "optional", "alt", "lookaround"}:
        return "str"
    return "int"


def _signature(spec: _Spec, annotated: list[tuple[str, str]], optional_default: bool) -> str:
    annotation_map = dict(annotated)
    positional_only, positional, keyword_only = _signature_names(spec, annotation_map)
    defaulted = _signature_defaults(spec, positional_only, positional, keyword_only, optional_default)
    if spec.request_mode == "varkw_only":
        return "**kwargs"
    positional_only, positional, keyword_only = _request_sections(
        spec.request_mode, positional_only, positional, keyword_only
    )
    return _render_signature(spec, annotation_map, positional_only, positional, keyword_only, defaulted)


def _request_sections(request_mode, positional_only, positional, keyword_only):
    """Place the request parameter in the selected signature section."""
    if request_mode == "positional_only":
        return ["request", *positional_only], positional, keyword_only
    if request_mode == "positional":
        return positional_only, ["request", *positional], keyword_only
    if request_mode == "varargs_only":
        return positional_only, [], keyword_only
    return positional_only, positional, ["request", *keyword_only]


def _render_signature(spec, annotation_map, positional_only, positional, keyword_only, defaulted):
    """Render the three signature sections and star arguments."""
    parts = _render_base_sections(annotation_map, positional_only, positional, defaulted)
    return ", ".join(_append_star_sections(spec, annotation_map, parts, keyword_only, defaulted))


def _render_base_sections(annotation_map, positional_only, positional, defaulted):
    """Render positional and keyword-only parameter sections."""
    parts: list[str] = []
    if positional_only:
        parts.extend(_render_parameters({**annotation_map, "request": "Any"}, positional_only, defaulted).split(", "))
        parts.append("/")
    if positional:
        parts.extend(_render_parameters({**annotation_map, "request": "Any"}, positional, defaulted).split(", "))
    return parts


def _append_star_sections(spec, annotation_map, parts, keyword_only, defaulted):
    """Append varargs, keyword separators, and kwargs."""
    needs_star = spec.request_mode == "keyword_only" or bool(keyword_only)
    if spec.request_mode == "varargs_only" or spec.signature in {"varargs", "both"}:
        parts.append("*args")
        needs_star = False
    elif needs_star:
        parts.append("*")
    if keyword_only:
        parts.extend(_render_parameters({**annotation_map, "request": "Any"}, keyword_only, defaulted).split(", "))
    if spec.signature in {"varargs", "both"} and "*args" not in parts:
        parts.append("*args")
    if spec.signature in {"varkw", "both"}:
        parts.append("**kwargs")
    if not parts:
        parts.append("request")
    return parts


def _signature_names(spec, annotation_map):
    """Select signature sections from names that have annotations."""
    positional_only = _known_names(spec.positional_only, annotation_map)
    positional = _known_names(spec.positional, annotation_map, positional_only)
    keyword_only = _known_names(spec.keyword_only, annotation_map)
    keyword_only.extend(_known_names(spec.extra_names, annotation_map, keyword_only))
    return positional_only, positional, keyword_only


def _known_names(names, annotation_map, excluded=()):
    """Keep names with annotations and remove a previous section."""
    return [name for name in names if name in annotation_map and name not in excluded]


def _signature_defaults(spec, positional_only, positional, keyword_only, optional_default):
    """Choose defaults while preserving Python's positional ordering rules."""
    defaulted = set(positional_only + positional) if optional_default or spec.signature == "defaults" else set()
    defaulted.update(spec.defaults)
    defaulted.intersection_update(positional_only + positional + keyword_only)
    seen_default = False
    for name in positional_only + positional:
        seen_default = seen_default or name in defaulted
        if seen_default:
            defaulted.add(name)
    return defaulted


def _render_parameters(annotation_map, names, defaulted):
    """Render valid Python parameters for one signature section."""
    rendered = []
    for name in names:
        value = f"{name}: {annotation_map[name]}"
        if name in defaulted:
            value += " = 1"
        rendered.append(value)
    return ", ".join(rendered)


def _view_source(signature: str, is_async: bool) -> str:
    prefix = "async " if is_async else ""
    return (
        "from django.http import HttpResponse\n" + _SOURCE_IMPORTS + "\n"
        f"{prefix}def view({signature}):\n    return HttpResponse()\n"
    )


def _decorate(view, mode):
    if mode == "none":
        return view

    def decorator(function):
        @functools.wraps(function) if mode == "wraps" else (lambda wrapped: wrapped)
        def wrapper(*args, **kwargs):
            return function(*args, **kwargs)

        return wrapper

    return decorator(view)


def _cbv_view(spec: _Spec, annotated: list[tuple[str, str]], defaults: bool):
    params = _signature(spec, annotated, defaults)
    handler_body = "        return HttpResponse()\n"
    lines = ["from django.http import HttpResponse", "from django.views import View", ""]
    lines.insert(0, _SOURCE_IMPORTS.rstrip())
    if spec.cbv_mixin:
        lines.append("class FuzzMixin:")
        if "get" in spec.cbv_handlers:
            lines.extend([f"    def get(self, {params}):", handler_body])
        else:
            lines.append("    pass")
        lines.append("")
    lines.append("class FuzzView(FuzzMixin, View):" if spec.cbv_mixin else "class FuzzView(View):")
    if not spec.cbv_mixin:
        for method in spec.cbv_handlers:
            lines.extend(_cbv_handler_lines(method, params, spec.cbv_descriptor, handler_body))
    elif "post" in spec.cbv_handlers:
        lines.extend(_cbv_handler_lines("post", params, "normal", handler_body))
    if spec.cbv_setup:
        lines.extend([f"    def setup(self, {params}):", "        self.request = request", ""])
    if spec.cbv_dispatch:
        lines.extend([f"    def dispatch(self, {params}):", handler_body])
    if lines[-1] in {"class FuzzView(View):", "class FuzzView(FuzzMixin, View):"}:
        lines.append("    pass")
    source = "\n".join(lines).rstrip() + "\n"
    namespace = {
        "View": View,
        "HttpResponse": HttpResponse,
        "Any": Any,
        "Literal": Literal,
        "Annotated": Annotated,
        "UserId": UserId,
        "UserName": UserName,
        "UserUUID": UserUUID,
        "BoundInt": BoundInt,
        "BoundStr": BoundStr,
        "BoundUUID": BoundUUID,
    }
    exec(source, namespace)  # noqa: S102
    namespace["FuzzView"].__module__ = "tests.fuzz.generated"
    view_class = cast(type[View], namespace["FuzzView"])
    return view_class.as_view(), source


def _cbv_handler_lines(method: str, params: str, descriptor: str, body: str) -> list[str]:
    """Render one CBV handler, including descriptor and callable-object forms."""
    if descriptor == "callable":
        return [
            "    class CallableHandler:",
            f"        def __call__(self, {params}):",
            "            return HttpResponse()",
            f"    {method} = CallableHandler()",
        ]
    if descriptor == "staticmethod":
        return ["    @staticmethod", f"    def {method}({params}):", body]
    if descriptor == "classmethod":
        return ["    @classmethod", f"    def {method}(cls, {params}):", body]
    return [f"    def {method}(self, {params}):", body]


def _drf_view(spec: _Spec, annotated: list[tuple[str, str]], defaults: bool):
    """Build a small DRF APIView when the optional dependency is installed."""
    from rest_framework.response import Response
    from rest_framework.views import APIView

    params = _signature(spec, annotated, defaults)
    source = (
        "from rest_framework.response import Response\nfrom rest_framework.views import APIView\n"
        + _SOURCE_IMPORTS
        + "\n"
        f"class FuzzAPI(APIView):\n    def get(self, {params}):\n"
        "        return Response()\n"
    )
    namespace = {
        "APIView": APIView,
        "Response": Response,
        "Any": Any,
        "Literal": Literal,
        "Annotated": Annotated,
        "UserId": UserId,
        "UserName": UserName,
        "UserUUID": UserUUID,
        "BoundInt": BoundInt,
        "BoundStr": BoundStr,
        "BoundUUID": BoundUUID,
    }
    exec(source, namespace)  # noqa: S102
    namespace["FuzzAPI"].__module__ = "tests.fuzz.generated"
    view_class = cast(type[APIView], namespace["FuzzAPI"])
    return view_class.as_view(), source


def _leaf(spec: _Spec, view):
    builders = {
        "static": _static_leaf,
        "named": _named_leaf,
        "unnamed": _unnamed_leaf,
        "optional": _optional_leaf,
        "alt": _alt_leaf,
        "lookaround": _lookaround_leaf,
    }
    if spec.route in builders:
        return builders[spec.route](spec, view)
    return _converter_leaf(spec, view)


def _static_leaf(spec, view):
    kwargs = {spec.path_kw_name: 4} if spec.path_kw_name else {}
    suffix = f", {kwargs!r}" if kwargs else ""
    return path("f/", view, kwargs), "/f/", f"path('f/', view{suffix})"


def _converter_leaf(spec, view):
    converter = "fuzzint" if spec.route == "custom" else spec.route
    if spec.route == "custom":
        build_custom_converter()
    route = "f/" + "/".join(f"<{converter}:{name}>" for name in spec.captures) + "/"
    values = {
        "int": "3",
        "str": "abc",
        "slug": "abc-3",
        "uuid": "12345678-1234-5678-1234-567812345678",
        "path": "a/b",
        "fuzzint": "7",
    }
    value_path = "/".join(values[converter] for _name in spec.captures)
    kwargs = {spec.path_kw_name: 4} if spec.path_kw_name else {}
    suffix = f", {kwargs!r}" if kwargs else ""
    return path(route, view, kwargs), "/f/" + value_path + "/", f"path({route!r}, view{suffix})"


def _named_leaf(spec, view):
    route = "^f/" + "/".join(f"(?P<{name}>[a-z]+)" for name in spec.captures) + "/$"
    url = "/f/" + "/".join("abc" for _name in spec.captures) + "/"
    kwargs = {spec.path_kw_name: 4} if spec.path_kw_name else {}
    suffix = f", {kwargs!r}" if kwargs else ""
    return re_path(route, view, kwargs), url, f"re_path({route!r}, view{suffix})"


def _unnamed_leaf(spec, view):
    route = "^f/" + "/".join("([a-z]+)" for _name in spec.captures) + "/$"
    url = "/f/" + "/".join("abc" for _name in spec.captures) + "/"
    kwargs = {spec.path_kw_name: 4} if spec.path_kw_name else {}
    suffix = f", {kwargs!r}" if kwargs else ""
    return re_path(route, view, kwargs), url, f"re_path({route!r}, view{suffix})"


def _optional_leaf(_spec, view):
    route = r"^f/(?P<p0>[a-z]+)?/$"
    kwargs = {_spec.path_kw_name: 4} if _spec.path_kw_name else {}
    suffix = f", {kwargs!r}" if kwargs else ""
    return re_path(route, view, kwargs), "/f//", f"re_path({route!r}, view{suffix})"


def _alt_leaf(_spec, view):
    route = r"^f/(?:(?P<p0>[a-z]+)|[0-9]+)/$"
    kwargs = {_spec.path_kw_name: 4} if _spec.path_kw_name else {}
    suffix = f", {kwargs!r}" if kwargs else ""
    return re_path(route, view, kwargs), "/f/7/", f"re_path({route!r}, view{suffix})"


def _lookaround_leaf(_spec, view):
    route = r"^f/(?=(?P<p0>[a-z]+))[a-z]+/$"
    kwargs = {_spec.path_kw_name: 4} if _spec.path_kw_name else {}
    suffix = f", {kwargs!r}" if kwargs else ""
    return re_path(route, view, kwargs), "/f/abc/", f"re_path({route!r}, view{suffix})"


def _variants(spec: _Spec, prefix: str, leaf_url: str) -> list[str]:
    base = "/" + prefix + leaf_url.lstrip("/")
    if spec.route == "optional":
        present = "/" + prefix + "f/abc/"
        return [base, present]
    if spec.route == "alt":
        return [base, "/" + prefix + "f/abc/"]
    return [base]


def build_custom_converter(name: str = "fuzzint"):
    """Register a typed converter used by callers that want custom coverage."""

    class Converter:
        regex = r"[0-9]+"

        def to_python(self, value: str) -> int:
            return int(value)

        def to_url(self, value: int) -> str:
            return str(value)

    try:
        register_converter(Converter, name)
    except Exception as exc:
        if name not in str(exc):
            raise
    return Converter


def build_untyped_converter(name: str = "fuzzraw"):
    """Register a converter without a return annotation for W002 coverage."""

    class Converter:
        regex = r"[0-9]+"

        def to_python(self, value):
            return int(value)

        def to_url(self, value):
            return str(value)

    try:
        register_converter(Converter, name)
    except Exception as exc:
        if name not in str(exc):
            raise
    return Converter


def build_drf_router_case() -> Case:
    """Return a deterministic ViewSet/router/action case when DRF is available."""
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            ROOT_URLCONF="tests.fuzz._empty",
            SECRET_KEY="fuzz",
            ALLOWED_HOSTS=["*"],
            INSTALLED_APPS=["django.contrib.auth", "django.contrib.contenttypes", "rest_framework"],
        )
        import django

        django.setup()
    from rest_framework import response, routers, viewsets
    from rest_framework.decorators import action

    class FuzzSet(viewsets.ViewSet):
        def list(self, request):
            return response.Response()

        def retrieve(self, request, pk):
            return response.Response()

        @action(detail=True, methods=["get"], url_path=r"items/(?P<item>[0-9]+)")
        def item(self, request, pk, item):
            return response.Response()

    router = routers.SimpleRouter()
    router.register("fuzz", FuzzSet, basename="fuzz")
    source = (
        "class FuzzSet(viewsets.ViewSet):\n"
        "    def list(self, request): ...\n"
        "    def retrieve(self, request, pk): ...\n"
        "    @action(detail=True, methods=['get'], url_path=r'items/(?P<item>[0-9]+)')\n"
        "    def item(self, request, pk, item): ...\n"
    )
    return Case(
        "drf-router",
        router.urls,
        ("/fuzz/", "/fuzz/1/", "/fuzz/1/items/2/"),
        source,
        "from rest_framework.routers import SimpleRouter\nurlpatterns = router.urls",
        "drf-router",
    )
