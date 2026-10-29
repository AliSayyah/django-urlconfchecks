"""Quick and dirty URL checker."""

import collections.abc as cabc
import fnmatch
import functools
import types
import typing as t
import uuid
from dataclasses import dataclass
from inspect import Parameter, _empty, signature
from typing import Any, get_args, get_origin

from django.conf import settings
from django.core import checks
from django.urls import URLPattern, URLResolver, converters, get_resolver
from django.urls.resolvers import RegexPattern, RoutePattern

Problem = checks.Error | checks.Warning


@dataclass(frozen=True)
class _RouteArgument:
    """Describe one argument that Django can pass to a URL callback."""

    kind: str
    value: Any = Parameter.empty
    optional: bool = False


@dataclass(frozen=True)
class _RouteInfo:
    """A URL pattern and the arguments accumulated on the way to it."""

    pattern: URLPattern
    kwargs: dict[str, _RouteArgument]
    positional: tuple[_RouteArgument, ...]


# Update docs about default value if you change this:
_DEFAULT_SILENCED_VIEWS = {
    # for CBVs
    "*.View.as_view": "W001",
    # RedirectView is used in a way that makes it appear directly, and it has **kwargs
    "django.views.generic.base.RedirectView": "W001",
    # Django contrib views currently don’t have type annotations:
    "django.contrib.*": "W003",
}


@checks.register(checks.Tags.urls)
def check_url_signatures(app_configs, **kwargs) -> list[Problem]:
    """Check that all callbacks in the main urlconf have the correct signature.

    Args:
        app_configs: A list of AppConfig instances that will be checked.
        **kwargs: Not used.

    Returns:
        A list of errors.
    """
    if not getattr(settings, 'ROOT_URLCONF', None):
        return []

    resolver = get_resolver()
    errors = []
    silencers = _build_view_silencers(getattr(settings, "URLCONFCHECKS_SILENCED_VIEWS", _DEFAULT_SILENCED_VIEWS))
    unknown_converters = set()
    for route in _walk_routes(resolver):
        errors.extend(_check_route_info(route, unknown_converters))
    return _filter_errors(errors, silencers)


def get_all_routes(resolver: URLResolver, parent_converters: dict) -> cabc.Iterable[tuple[URLPattern, dict]]:
    """Recursively get all routes from the resolver."""
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLResolver):
            if hasattr(pattern, 'pattern') and pattern.pattern is not None:
                # This handles cases involving `include` where the parent `path`
                # may have captured some parameters in its first argument. Those
                # parameters will also need to be passed down.
                new_parent_converters = {**parent_converters, **getattr(pattern.pattern, "converters", {})}
            else:
                new_parent_converters = parent_converters
            yield from get_all_routes(pattern, new_parent_converters)
        else:
            if isinstance(pattern.pattern, RoutePattern):
                yield pattern, parent_converters


def _walk_routes(resolver: URLResolver) -> cabc.Iterable[_RouteInfo]:
    """Yield leaf URL patterns with the arguments Django passes to them.

    ``URLResolver.resolve()`` merges arguments from an include before it
    returns the child match.  This walker follows the same precedence rules:
    captures are overridden by include kwargs, and child captures/defaults
    override everything inherited from a parent resolver.  Positional captures
    are prepended only while the merged kwargs dictionary is empty.
    """
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLResolver):
            resolver_kwargs, resolver_args = _pattern_arguments(pattern.pattern)
            resolver_kwargs.update(
                {
                    name: _RouteArgument("include_extra", value, optional=False)
                    for name, value in getattr(pattern, "default_kwargs", {}).items()
                }
            )
            for child in _walk_routes(pattern):
                kwargs = {**resolver_kwargs, **child.kwargs}
                positional = child.positional
                if not kwargs:
                    positional = resolver_args + positional
                yield _RouteInfo(child.pattern, kwargs, positional)
            continue

        if not isinstance(pattern, URLPattern):
            continue
        kwargs, positional = _pattern_arguments(pattern.pattern)
        kwargs.update(
            {name: _RouteArgument("extra", value, optional=False) for name, value in pattern.default_args.items()}
        )
        yield _RouteInfo(pattern, kwargs, positional)


def _pattern_arguments(pattern) -> tuple[dict[str, _RouteArgument], tuple[_RouteArgument, ...]]:
    """Return the captures produced by a Django URL pattern."""
    if isinstance(pattern, RoutePattern):
        return (
            {name: _RouteArgument("converter", converter) for name, converter in pattern.converters.items()},
            (),
        )

    if isinstance(pattern, RegexPattern):
        regex = pattern.regex
        if regex.groupindex:
            optional_groups = _optional_regex_groups(regex)
            return (
                {
                    name: _RouteArgument("regex", str, group_number in optional_groups)
                    for name, group_number in regex.groupindex.items()
                },
                (),
            )
        return {}, tuple(_RouteArgument("regex", str) for _ in range(regex.groups))

    # LocalePrefixPattern and other non-capturing resolver patterns expose no
    # captures.  Do not inspect their ``regex`` property: it is a language
    # prefix, not a RegexPattern match with view arguments.
    return {}, ()


def _optional_regex_groups(regex) -> set[int]:
    """Return capturing group numbers that can be absent from a match.

    The parser is an internal ``re`` API, so parsing failures simply disable
    W004.  The common optional forms and groups inside optional alternations
    are handled without attempting to reason about general regex semantics.
    """
    try:
        import re

        parser = getattr(re, "_parser", None)
        if parser is None:
            return set()
        parsed = parser.parse(regex.pattern, regex.flags)
    except Exception:
        return set()

    optional: set[int] = set()
    repeat_ops = {parser.MAX_REPEAT, parser.MIN_REPEAT}
    if hasattr(parser, "POSSESSIVE_REPEAT"):
        repeat_ops.add(parser.POSSESSIVE_REPEAT)

    def group_numbers(tokens):
        found = set()
        for operation, argument in tokens:
            if operation is parser.SUBPATTERN:
                group_number, _, _, nested = argument
                if group_number:
                    found.add(group_number)
                found.update(group_numbers(nested))
            elif operation in repeat_ops:
                found.update(group_numbers(argument[2]))
            elif operation is parser.BRANCH:
                found.update(*(group_numbers(branch) for branch in argument[1]))
        return found

    def visit(tokens, inherited_optional=False):
        for operation, argument in tokens:
            if operation is parser.SUBPATTERN:
                group_number, _, _, nested = argument
                if group_number and inherited_optional:
                    optional.add(group_number)
                visit(nested, inherited_optional)
            elif operation in repeat_ops:
                minimum, _, nested = argument
                visit(nested, inherited_optional or minimum == 0)
            elif operation is parser.BRANCH:
                branches = argument[1]
                branch_groups = [group_numbers(branch) for branch in branches]
                for branch in branches:
                    visit(branch, inherited_optional)
                all_groups = set().union(*branch_groups) if branch_groups else set()
                for group_number in all_groups:
                    if any(group_number not in groups for groups in branch_groups):
                        optional.add(group_number)

    visit(parsed)
    return optional


def _make_callback_repr(callback):
    if hasattr(callback, "view_class"):
        qualname = callback.view_class.as_view.__qualname__
        module = callback.view_class.as_view.__module__
    elif isinstance(callback, functools.partial):
        qualname = callback.func.__qualname__
        module = callback.func.__module__
    else:
        qualname = callback.__qualname__
        module = callback.__module__
    return f"{module}.{qualname}"


def _get_signature(callable_obj):
    """Return a signature, resolving deferred annotations when possible."""
    try:
        return signature(callable_obj, eval_str=True)
    except Exception:
        sig = signature(callable_obj)
        return _resolve_signature_annotations(sig, callable_obj)


def _resolve_signature_annotations(sig, callable_obj):
    globalns = _get_callable_globals(callable_obj)
    parameters = [
        parameter.replace(annotation=_resolve_annotation(parameter.annotation, globalns))
        for parameter in sig.parameters.values()
    ]
    return sig.replace(
        parameters=parameters,
        return_annotation=_resolve_annotation(sig.return_annotation, globalns),
    )


def _get_callable_globals(callable_obj):
    if isinstance(callable_obj, functools.partial):
        callable_obj = callable_obj.func
    if hasattr(callable_obj, "__func__"):
        callable_obj = callable_obj.__func__
    return getattr(callable_obj, "__globals__", {})


def _resolve_annotation(annotation, globalns):
    if not isinstance(annotation, str):
        return annotation
    try:
        return eval(annotation, globalns)
    except Exception:
        return Parameter.empty


def check_url_args_match(
    url_pattern: URLPattern, parent_converters: dict, unknown_converters: set[type] | None = None
) -> list[Problem]:
    """Check one URL pattern using the legacy converter-only route interface."""
    if unknown_converters is None:
        unknown_converters = set()
    kwargs, positional = _pattern_arguments(url_pattern.pattern)
    kwargs = {
        **{name: _RouteArgument("converter", converter) for name, converter in parent_converters.items()},
        **kwargs,
    }
    kwargs.update(
        {name: _RouteArgument("extra", value, optional=False) for name, value in url_pattern.default_args.items()}
    )
    return _check_route_info(_RouteInfo(url_pattern, kwargs, positional), unknown_converters)


def _check_route_info(route: _RouteInfo, unknown_converters: set[type]) -> list[Problem]:
    """Check one leaf route against the arguments Django will pass."""
    url_pattern = route.pattern
    callback = url_pattern.callback
    callback_repr = _make_callback_repr(callback)
    errors: list[Problem] = []
    sig = _get_signature(callback)
    parameters = sig.parameters

    has_varargs = any(parameter.kind is Parameter.VAR_POSITIONAL for parameter in parameters.values())
    has_varkw = any(parameter.kind is Parameter.VAR_KEYWORD for parameter in parameters.values())
    has_star_args = has_varargs or has_varkw
    if has_star_args:
        errors.append(
            checks.Warning(
                f"View {callback_repr} signature contains *args or **kwarg syntax, can't properly check args",
                obj=url_pattern,
                id="urlchecker.W001",
            )
        )

    used_from_sig: list[str] = []
    parameter_list = list(sig.parameters)
    if parameter_list and parameter_list[0] == "self":
        # HACK: we need to find some nice way to detect closures/bound methods,
        # while also getting the final signature.
        parameter_list.pop(0)
        used_from_sig.append("self")

    if not parameter_list or parameter_list[0] != "request":
        if not has_star_args:
            if parameter_list:
                message = (
                    f"View {callback_repr} signature does not start with `request` parameter, "
                    f"found `{parameter_list[0]}`."
                )
            else:
                message = f"View {callback_repr} signature does not have `request` parameter."
            errors.append(checks.Error(message, obj=url_pattern, id="urlchecker.E001"))
    else:
        used_from_sig.append("request")

    for name, argument in route.kwargs.items():
        parameter = parameters.get(name)
        if parameter is None:
            if has_varkw:
                continue
            if argument.kind in {"extra", "include_extra"}:
                if argument.kind == "include_extra":
                    message = (
                        f"View {callback_repr} is being passed additional unexpected parameter `{name}` "
                        "from include() kwargs"
                    )
                else:
                    message = (
                        f"View {callback_repr} is being passed additional unexpected "
                        f"parameter `{name}` from default arguments in urlconf"
                    )
                errors.append(checks.Error(message, obj=url_pattern, id="urlchecker.E006"))
            else:
                errors.append(
                    checks.Error(
                        f"View {callback_repr} signature does not contain `{name}` parameter",
                        obj=url_pattern,
                        id="urlchecker.E003",
                    )
                )
            continue

        used_from_sig.append(name)
        if argument.kind == "converter":
            urlconf_type = get_converter_output_type(argument.value)
            if urlconf_type is Parameter.empty:
                converter = argument.value
                obj = converter.__class__
                if obj not in unknown_converters:
                    unknown_converters.add(obj)
                    errors.append(
                        checks.Warning(
                            f"Don't know output type for converter {obj.__module__}.{obj.__name__},"
                            " can't verify URL signatures.",
                            obj=obj,
                            id=f"urlchecker.W002.{obj.__module__}.{obj.__name__}",
                        )
                    )
            else:
                _check_typed_argument(errors, url_pattern, callback_repr, name, urlconf_type, parameter.annotation)
        elif argument.kind == "regex":
            _check_typed_argument(errors, url_pattern, callback_repr, name, str, parameter.annotation)
            if argument.optional and parameter.default is Parameter.empty:
                errors.append(
                    checks.Warning(
                        f"View {callback_repr} parameter `{name}` is captured by an optional regex group "
                        "but has no default",
                        obj=url_pattern,
                        id="urlchecker.W004",
                    )
                )
        else:
            _check_extra_argument(errors, url_pattern, callback_repr, name, argument, parameter.annotation)

    positional_parameters = [
        (name, parameter)
        for name, parameter in parameters.items()
        if name not in {"self", "request"}
        and parameter.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(route.positional) > len(positional_parameters) and not has_varargs:
        errors.append(
            checks.Error(
                f"View {callback_repr} receives {len(route.positional)} positional argument(s) from the URL pattern "
                f"but its signature only accepts {len(positional_parameters)}",
                obj=url_pattern,
                id="urlchecker.E007",
            )
        )

    for _argument, (name, parameter) in zip(route.positional, positional_parameters, strict=False):
        used_from_sig.append(name)
        _check_typed_argument(errors, url_pattern, callback_repr, name, str, parameter.annotation)

    # Anything left over must have a default argument in the view signature.
    for name, parameter in parameters.items():
        if name in used_from_sig:
            continue
        if parameter.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD):
            continue
        if parameter.default == Parameter.empty:
            errors.append(
                checks.Error(
                    f"View {callback_repr} signature contains `{name}` parameter without default or URLconf parameter",
                    obj=url_pattern,
                    id="urlchecker.E004",
                )
            )

    return errors


def _check_typed_argument(errors, url_pattern, callback_repr, name, urlconf_type, sig_type):
    """Check a converter or regex capture against a view annotation."""
    if sig_type == Parameter.empty:
        errors.append(
            checks.Warning(
                f"View {callback_repr} missing type annotation for parameter `{name}`, can't check type.",
                obj=url_pattern,
                id="urlchecker.W003",
            )
        )
    elif not _type_is_compatible(urlconf_type, sig_type):
        errors.append(
            checks.Error(
                f"View {callback_repr} for parameter `{name}`,"
                f" annotated type {_name_type(sig_type)} does not match"
                f" expected `{_name_type(urlconf_type)}` from urlconf",
                obj=url_pattern,
                id="urlchecker.E002",
            )
        )


def _check_extra_argument(errors, url_pattern, callback_repr, name, argument, sig_type):
    """Check a path(), re_path(), or include() extra keyword argument."""
    if sig_type == Parameter.empty:
        errors.append(
            checks.Warning(
                f"View {callback_repr} missing type annotation for parameter `{name}`, can't check type.",
                obj=url_pattern,
                id="urlchecker.W003",
            )
        )
    elif not _instance_is_compatible(argument.value, sig_type):
        if argument.kind == "include_extra":
            source = "include() kwargs"
        else:
            source = "urlconf"
        errors.append(
            checks.Error(
                f"View {callback_repr}: for parameter `{name}`,"
                f" default argument {repr(argument.value)} in {source}, type {_name_type(type(argument.value))},"
                f" does not match annotated type {_name_type(sig_type)} from view signature",
                obj=url_pattern,
                id="urlchecker.E005",
            )
        )


def _type_is_compatible(passed_type, accepted_type) -> bool:
    """Compare a converter return type to an annotation."""
    if passed_type is Parameter.empty:
        return False

    passed_candidates = _iter_type_candidates(passed_type, include_none=True) or (passed_type,)
    accepted_candidates = _iter_type_candidates(accepted_type, include_none=False)

    for passed in passed_candidates:
        for candidate in accepted_candidates:
            if _type_candidate_matches(passed, candidate):
                return True
    return False


def _type_candidate_matches(passed_type, candidate) -> bool:
    if candidate in (Any, object):
        return True

    # Unions are handled by the caller (_iter_type_candidates splits them)
    origin_candidate = get_origin(candidate)

    origin_passed = get_origin(passed_type)

    if origin_candidate:
        try:
            base_matches = issubclass(origin_passed or passed_type, origin_candidate)
        except TypeError:
            return False
        return base_matches

    try:
        return issubclass(origin_passed or passed_type, candidate)
    except TypeError:
        return False


def _instance_is_compatible(instance, accepted_type) -> bool:
    return any(
        _instance_candidate_matches(instance, candidate)
        for candidate in _iter_type_candidates(accepted_type, include_none=True)
    )


def _instance_candidate_matches(instance, candidate) -> bool:
    if candidate in (Any, object):
        return True

    # None handling
    if instance is None:
        return candidate is type(None)

    origin = get_origin(candidate)
    args = get_args(candidate)

    if origin:
        if not isinstance(instance, origin):
            return False

        # Homogeneous containers (list/set/frozenset/Sequence/etc.)
        if origin in {list, set, frozenset} or issubclass(origin, (cabc.Sequence, cabc.Set)) and origin is not tuple:
            inner = args[0] if args else Any
            return all(_instance_is_compatible(item, inner) for item in instance)

        # Tuples: fixed length or variadic tuple[T, ...]
        if origin is tuple or issubclass(origin, tuple):
            if not args:
                return True
            if len(args) == 2 and args[1] is Ellipsis:
                inner = args[0]
                return all(_instance_is_compatible(item, inner) for item in instance)
            if len(args) != len(instance):
                return False
            return all(_instance_is_compatible(item, ann) for item, ann in zip(instance, args, strict=True))

        # Mappings / dicts
        if origin in {dict} or issubclass(origin, cabc.Mapping):
            key_type = args[0] if args else Any
            value_type = args[1] if len(args) > 1 else Any
            return all(
                _instance_is_compatible(k, key_type) and _instance_is_compatible(v, value_type)
                for k, v in instance.items()
            )

        # Fallback: if it's the right origin and we can't/don't want to inspect contents
        return True

    try:
        return isinstance(instance, candidate)
    except TypeError:
        return False


def _iter_type_candidates(annotation, include_none: bool) -> tuple[t.Any, ...]:
    """Return a tuple of acceptable types for compatibility checks."""
    if annotation is Parameter.empty:
        return ()

    annotation = _unwrap_annotated(annotation)
    origin = get_origin(annotation)
    args = get_args(annotation)

    # PEP 604 unions (X | Y) and typing.Union
    if origin in (t.Union, types.UnionType):
        candidates = args
    else:
        candidates = (annotation,)

    if not include_none:
        candidates = tuple(c for c in candidates if c is not type(None))

    return candidates


def _unwrap_annotated(annotation):
    """Peel off typing.Annotated layers, returning the underlying type."""
    while get_origin(annotation) is t.Annotated:
        annotation = get_args(annotation)[0]
    return annotation


def _name_type(type_hint):
    # Things like `Optional[int]`:
    # - repr() does a better job than `__name__`
    # - `__name__` is not available in some Python versions.
    return type_hint.__name__ if (hasattr(type_hint, "__name__") and isinstance(type_hint, type)) else repr(type_hint)


ConverterOutputType: t.TypeAlias = type[int] | type[str] | type[uuid.UUID] | type[_empty]

CONVERTER_TYPES: dict[type, ConverterOutputType] = {
    converters.IntConverter: int,
    converters.StringConverter: str,
    converters.UUIDConverter: uuid.UUID,
    converters.SlugConverter: str,
    converters.PathConverter: str,
}


def get_converter_output_type(converter) -> ConverterOutputType:
    """Return the type that the converter will output."""
    return _converter_output_type_for_class(converter.__class__)


@functools.cache
def _converter_output_type_for_class(converter_cls) -> ConverterOutputType:
    """Cached resolution of converter output type by class."""
    for cls in converter_cls.__mro__:
        if cls in CONVERTER_TYPES:
            return CONVERTER_TYPES[cls]

        if hasattr(cls, "to_python"):
            sig = _get_signature(cls.to_python)
            if sig.return_annotation != Parameter.empty:
                return t.cast(ConverterOutputType, sig.return_annotation)

    return Parameter.empty


class ViewSilencer:
    """Utility that checks whether errors for a view or set of views should be ignored."""

    def __init__(self, view_glob: str, errors: cabc.Iterable[str]):
        self.view_glob = view_glob
        self.errors = set(errors)

    def matches(self, error: Problem):
        """Returns True if this silencer matches the given error or warning."""
        url_pattern = error.obj
        if not isinstance(url_pattern, URLPattern):
            # Some other error, eg. for a convertor
            return False
        if error.id not in self.errors:
            return False

        view_name = _make_callback_repr(url_pattern.callback)
        if fnmatch.fnmatch(view_name, self.view_glob):
            return True
        return False


def _build_view_silencers(silenced_views: dict[str, str]) -> list[ViewSilencer]:
    return [
        ViewSilencer(view_glob=view_glob, errors=[f"urlchecker.{error}" for error in error_list.split(",")])
        for view_glob, error_list in silenced_views.items()
    ]


def _filter_errors(errors: list[Problem], silencers: list[ViewSilencer]) -> list[Problem]:
    return [error for error in errors if not any(silencer.matches(error) for silencer in silencers)]
