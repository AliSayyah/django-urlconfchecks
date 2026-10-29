"""Quick and dirty URL checker."""

import collections.abc as cabc
import fnmatch
import functools
import inspect
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

    _mark_optional_regex_groups(parsed, parser, repeat_ops, optional)
    return optional


def _regex_group_numbers(tokens, parser, repeat_ops) -> set[int]:
    """Return capture group numbers found in parsed regex tokens."""
    groups: set[int] = set()
    for operation, argument in tokens:
        if operation is parser.SUBPATTERN:
            group_number, _, _, nested = argument
            if group_number:
                groups.add(group_number)
            groups.update(_regex_group_numbers(nested, parser, repeat_ops))
        elif operation in repeat_ops:
            groups.update(_regex_group_numbers(argument[2], parser, repeat_ops))
        elif operation is parser.BRANCH:
            for branch in argument[1]:
                groups.update(_regex_group_numbers(branch, parser, repeat_ops))
    return groups


def _mark_optional_regex_groups(tokens, parser, repeat_ops, optional: set[int], inherited_optional=False):
    """Mark parsed regex groups that can be absent from a match."""
    for operation, argument in tokens:
        if operation is parser.SUBPATTERN:
            _mark_optional_subpattern(argument, parser, repeat_ops, optional, inherited_optional)
        elif operation in repeat_ops:
            _mark_optional_repeat(argument, parser, repeat_ops, optional, inherited_optional)
        elif operation is parser.BRANCH:
            _mark_optional_branch(argument, parser, repeat_ops, optional, inherited_optional)


def _mark_optional_subpattern(argument, parser, repeat_ops, optional, inherited_optional):
    """Mark a subpattern group and inspect its nested tokens."""
    group_number, _, _, nested = argument
    if group_number and inherited_optional:
        optional.add(group_number)
    _mark_optional_regex_groups(nested, parser, repeat_ops, optional, inherited_optional)


def _mark_optional_repeat(argument, parser, repeat_ops, optional, inherited_optional):
    """Inspect a repeated token and propagate its optionality."""
    minimum, _, nested = argument
    _mark_optional_regex_groups(nested, parser, repeat_ops, optional, inherited_optional or minimum == 0)


def _mark_optional_branch(argument, parser, repeat_ops, optional, inherited_optional):
    """Mark groups that are absent from at least one alternation branch."""
    branches = argument[1]
    branch_groups = [_regex_group_numbers(branch, parser, repeat_ops) for branch in branches]
    for branch in branches:
        _mark_optional_regex_groups(branch, parser, repeat_ops, optional, inherited_optional)
    all_groups = set().union(*branch_groups) if branch_groups else set()
    for group_number in all_groups:
        if any(group_number not in groups for groups in branch_groups):
            optional.add(group_number)


def _make_callback_repr(callback):
    view_class = getattr(callback, "view_class", None)
    if view_class is not None and hasattr(view_class, "as_view"):
        target = view_class.as_view
    elif isinstance(callback, functools.partial):
        target = callback.func
    else:
        target = callback
    qualname = getattr(target, "__qualname__", type(target).__qualname__)
    module = getattr(target, "__module__", type(target).__module__)
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
    """Check one leaf route against the arguments Django passes."""
    url_pattern = route.pattern
    callback = url_pattern.callback
    cbv_handlers = _get_cbv_handlers(callback)
    if cbv_handlers is not None:
        errors: list[Problem] = []
        for handler, callback_repr, class_repr in cbv_handlers:
            errors.extend(
                _check_callable_route(
                    route,
                    handler,
                    callback_repr,
                    unknown_converters,
                    is_cbv_handler=True,
                    class_repr=class_repr,
                )
            )
        return errors

    try:
        return _check_callable_route(route, callback, _make_callback_repr(callback), unknown_converters)
    except (TypeError, ValueError):
        if _has_cbv_attributes(callback):
            return []
        raise


def _check_callable_route(
    route: _RouteInfo,
    callback,
    callback_repr: str,
    unknown_converters: set[type],
    *,
    is_cbv_handler: bool = False,
    class_repr: str | None = None,
) -> list[Problem]:
    """Check one callable using the arguments accumulated for a URL route."""
    url_pattern = route.pattern
    sig = _get_signature(callback)
    if is_cbv_handler:
        sig = _drop_handler_self(sig)
    parameters = sig.parameters
    has_varargs, has_varkw = _star_argument_flags(parameters)
    errors: list[Problem] = []

    _append_star_args_warning(errors, url_pattern, callback_repr, has_varargs or has_varkw, is_cbv_handler)
    used_from_sig = _check_request_parameter(errors, url_pattern, callback_repr, sig, has_varargs or has_varkw)
    _check_route_kwargs(
        errors,
        route,
        url_pattern,
        callback_repr,
        parameters,
        has_varkw,
        used_from_sig,
        unknown_converters,
    )
    _check_positional_arguments(errors, route, url_pattern, callback_repr, parameters, has_varargs, used_from_sig)
    _check_leftover_required_parameters(errors, url_pattern, callback_repr, parameters, used_from_sig)
    # Record which view (and CBV class) each problem is about, for ViewSilencer.
    for error in errors:
        if error.obj is url_pattern:
            setattr(error, _VIEW_NAME_ATTR, callback_repr)
            if class_repr is not None:
                setattr(error, _VIEW_CLASS_NAME_ATTR, class_repr)
    return errors


_VIEW_NAME_ATTR = "_urlchecker_view_name"
_VIEW_CLASS_NAME_ATTR = "_urlchecker_view_class_name"

_HANDLER_MISSING = object()
_HANDLER_SKIP = object()
_HANDLER_INVALID = object()


def _get_cbv_handlers(callback):
    """Return resolved CBV handlers, or ``None`` for an ordinary callback."""
    try:
        view_class = getattr(callback, "view_class", None)
    except Exception:
        view_class = None
    if isinstance(view_class, type):
        return _get_django_handlers(view_class)

    try:
        view_class = getattr(callback, "cls", None)
        actions = getattr(callback, "actions", None)
    except Exception:
        return None
    if isinstance(view_class, type) and isinstance(actions, cabc.Mapping):
        return _get_viewset_handlers(view_class, actions)
    return None


def _has_cbv_attributes(callback) -> bool:
    """Return whether a callback advertises CBV metadata, even if it is malformed."""
    for name in ("view_class", "cls", "actions"):
        try:
            if inspect.getattr_static(callback, name, None) is not None:
                return True
        except Exception:
            continue
    return False


def _class_repr(view_class) -> str:
    """Return the stable dotted name used for CBV handlers and silencing."""
    return f"{view_class.__module__}.{view_class.__qualname__}"


def _get_django_handlers(view_class):
    """Resolve Django/APIView methods exposed by a class-based view."""
    method_names = _django_handler_names(view_class)
    if method_names is None:
        return None

    class_repr = _class_repr(view_class)
    handlers = []
    for name in method_names:
        handler = _resolve_class_handler(view_class, name)
        if handler is _HANDLER_MISSING:
            continue
        if handler is _HANDLER_SKIP:
            continue
        if handler is _HANDLER_INVALID:
            return None
        handlers.append((handler, f"{class_repr}.{name}", class_repr))

    dispatch = _resolve_explicit_dispatch(view_class)
    if dispatch is _HANDLER_INVALID:
        return None
    if dispatch not in (_HANDLER_MISSING, _HANDLER_SKIP):
        handlers.append((dispatch, f"{class_repr}.dispatch", class_repr))
    return handlers


def _django_handler_names(view_class):
    """Return the HTTP handler names that should be inspected."""
    try:
        method_names = tuple(view_class.http_method_names)
    except Exception:
        return None
    return tuple(
        name for name in method_names if isinstance(name, str) and (name != "head" or _has_explicit_head(view_class))
    )


def _resolve_explicit_dispatch(view_class):
    """Return an explicit dispatch handler, or a sentinel when there is none."""
    dispatch = _resolve_class_handler(view_class, "dispatch")
    if dispatch in (_HANDLER_MISSING, _HANDLER_SKIP, _HANDLER_INVALID):
        return dispatch
    if _dispatch_has_explicit_parameters(dispatch):
        return dispatch
    return _HANDLER_MISSING


def _get_viewset_handlers(view_class, actions):
    """Resolve the action methods selected by a DRF ViewSet callback."""
    class_repr = _class_repr(view_class)
    handlers = []
    try:
        action_names = tuple(dict.fromkeys(actions.values()))
    except Exception:
        return None
    for name in action_names:
        if not isinstance(name, str):
            return None
        handler = _resolve_class_handler(view_class, name)
        if handler is _HANDLER_MISSING or handler is _HANDLER_INVALID:
            return None
        if handler is _HANDLER_SKIP:
            continue
        handlers.append((handler, f"{class_repr}.{name}", class_repr))
    return handlers


def _resolve_class_handler(view_class, name):
    """Resolve a normal function handler while rejecting descriptors that cannot be handlers."""
    try:
        raw_handler = inspect.getattr_static(view_class, name)
    except AttributeError:
        return _HANDLER_MISSING
    except Exception:
        return _HANDLER_INVALID
    if isinstance(raw_handler, (staticmethod, classmethod)):
        return _HANDLER_SKIP
    try:
        handler = getattr(view_class, name)
    except Exception:
        return _HANDLER_INVALID
    if not callable(handler):
        return _HANDLER_INVALID
    try:
        _get_signature(handler)
    except Exception:
        return _HANDLER_INVALID
    return handler


def _has_explicit_head(view_class) -> bool:
    """Return whether ``head`` is defined independently of ``get`` in the MRO."""
    head = _resolve_class_handler(view_class, "head")
    if head in (_HANDLER_MISSING, _HANDLER_SKIP, _HANDLER_INVALID):
        return False
    get = _resolve_class_handler(view_class, "get")
    if get not in (_HANDLER_MISSING, _HANDLER_SKIP, _HANDLER_INVALID) and head is get:
        return False
    return True


def _drop_handler_self(sig):
    """Remove the unbound handler's instance parameter before checking it."""
    parameters = list(sig.parameters.values())
    if parameters:
        parameters.pop(0)
    return sig.replace(parameters=parameters)


def _dispatch_has_explicit_parameters(dispatch) -> bool:
    """Return whether an overridden dispatch has parameters worth checking."""
    try:
        sig = _drop_handler_self(_get_signature(dispatch))
    except Exception:
        return False
    parameters = tuple(sig.parameters.values())
    if any(
        parameter.name != "request" and parameter.kind not in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD)
        for parameter in parameters
    ):
        return True
    return not any(parameter.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD) for parameter in parameters)


def _star_argument_flags(parameters) -> tuple[bool, bool]:
    """Return whether a signature has ``*args`` or ``**kwargs``."""
    has_varargs = any(parameter.kind is Parameter.VAR_POSITIONAL for parameter in parameters.values())
    has_varkw = any(parameter.kind is Parameter.VAR_KEYWORD for parameter in parameters.values())
    return has_varargs, has_varkw


def _append_star_args_warning(errors, url_pattern, callback_repr, has_star_args, is_cbv_handler=False):
    """Append W001 when a view uses variable positional or keyword arguments."""
    if has_star_args and not is_cbv_handler:
        errors.append(
            checks.Warning(
                f"View {callback_repr} signature contains *args or **kwarg syntax, can't properly check args",
                obj=url_pattern,
                id="urlchecker.W001",
            )
        )


def _check_request_parameter(errors, url_pattern, callback_repr, sig, has_star_args) -> list[str]:
    """Check the request parameter and return parameters already supplied."""
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
    return used_from_sig


def _check_route_kwargs(
    errors,
    route,
    url_pattern,
    callback_repr,
    parameters,
    has_varkw,
    used_from_sig,
    unknown_converters,
):
    """Check keyword arguments captured or supplied by a route."""
    for name, argument in route.kwargs.items():
        parameter = parameters.get(name)
        if parameter is None:
            if has_varkw:
                continue
            _report_unaccepted_route_argument(errors, url_pattern, callback_repr, name, argument)
            continue

        used_from_sig.append(name)
        _check_route_kwarg_value(
            errors,
            url_pattern,
            callback_repr,
            name,
            argument,
            parameter,
            unknown_converters,
        )


def _report_unaccepted_route_argument(errors, url_pattern, callback_repr, name, argument):
    """Report a route keyword with no matching named view parameter."""
    if argument.kind in {"extra", "include_extra"}:
        if argument.kind == "include_extra":
            message = (
                f"View {callback_repr} is being passed additional unexpected parameter `{name}` from include() kwargs"
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


def _check_route_kwarg_value(errors, url_pattern, callback_repr, name, argument, parameter, unknown_converters):
    """Check one route keyword against its named view parameter."""
    if argument.kind == "converter":
        _check_converter_argument(
            errors, url_pattern, callback_repr, name, argument.value, parameter, unknown_converters
        )
    elif argument.kind == "regex":
        _check_regex_argument(errors, url_pattern, callback_repr, name, argument, parameter)
    else:
        _check_extra_argument(errors, url_pattern, callback_repr, name, argument, parameter.annotation)


def _check_converter_argument(errors, url_pattern, callback_repr, name, converter, parameter, unknown_converters):
    """Check a converter capture against a named view parameter."""
    urlconf_type = get_converter_output_type(converter)
    if urlconf_type is Parameter.empty:
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


def _check_regex_argument(errors, url_pattern, callback_repr, name, argument, parameter):
    """Check a regex capture against a named view parameter."""
    _check_typed_argument(errors, url_pattern, callback_repr, name, str, parameter.annotation)
    if argument.optional and parameter.default is Parameter.empty:
        errors.append(
            checks.Warning(
                f"View {callback_repr} parameter `{name}` is captured by an optional regex group but has no default",
                obj=url_pattern,
                id="urlchecker.W004",
            )
        )


def _positional_parameters(parameters):
    """Return named parameters that can receive positional URL arguments."""
    return [
        (name, parameter)
        for name, parameter in parameters.items()
        if name not in {"self", "request"}
        and parameter.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)
    ]


def _check_positional_arguments(errors, route, url_pattern, callback_repr, parameters, has_varargs, used_from_sig):
    """Map positional URL arguments to named view parameters and check types."""
    positional_parameters = _positional_parameters(parameters)
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


def _check_leftover_required_parameters(errors, url_pattern, callback_repr, parameters, used_from_sig):
    """Report required view parameters with no URL source or default."""
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

        view_name = getattr(error, _VIEW_NAME_ATTR, None) or _make_callback_repr(url_pattern.callback)
        if fnmatch.fnmatch(view_name, self.view_glob):
            return True
        class_name = getattr(error, _VIEW_CLASS_NAME_ATTR, None)
        return class_name is not None and fnmatch.fnmatch(class_name, self.view_glob)


def _build_view_silencers(silenced_views: dict[str, str]) -> list[ViewSilencer]:
    return [
        ViewSilencer(view_glob=view_glob, errors=[f"urlchecker.{error}" for error in error_list.split(",")])
        for view_glob, error_list in silenced_views.items()
    ]


def _filter_errors(errors: list[Problem], silencers: list[ViewSilencer]) -> list[Problem]:
    return [error for error in errors if not any(silencer.matches(error) for silencer in silencers)]
