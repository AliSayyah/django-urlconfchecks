"""Quick and dirty URL checker."""
import fnmatch
import typing as t
import uuid
from inspect import Parameter, _empty, signature  # type: ignore[attr-defined]

from django.conf import settings
from django.core import checks
from django.urls import URLPattern, URLResolver, converters, get_resolver
from django.urls.resolvers import RoutePattern

Problem = t.Union[checks.Error, checks.Warning]

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
def check_url_signatures(app_configs, **kwargs) -> t.List[Problem]:
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
    for route in get_all_routes(resolver):
        errors.extend(check_url_args_match(route))
    return _filter_errors(errors, silencers)


def get_all_routes(resolver: URLResolver) -> t.Iterable[URLPattern]:
    """Recursively get all routes from the resolver."""
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLResolver):
            yield from get_all_routes(pattern)
        else:
            if isinstance(pattern.pattern, RoutePattern):
                yield pattern


def _make_callback_repr(callback):
    if hasattr(callback, "view_class"):
        qualname = callback.view_class.as_view.__qualname__
        module = callback.view_class.as_view.__module__
    else:
        qualname = callback.__qualname__
        module = callback.__module__
    return f"{module}.{qualname}"


def check_url_args_match(url_pattern: URLPattern) -> t.List[Problem]:
    """Check that all callbacks in the main urlconf have the correct signature."""
    callback = url_pattern.callback
    callback_repr = _make_callback_repr(callback)
    errors = []
    sig = signature(callback)
    parameters = sig.parameters

    # We need to match everything defined in route definition, plus the kwargs
    # passed to path if any, against the signature of the view function.

    # Overall strategy:

    # 1. For all arguments captured by the RoutePattern, check they are in the
    #    view sig and that the type matches.

    # 2. For any parameter left in the view sig we didn't see yet,
    #    check that it either has a default arg in the sig,
    #    or that we can get it from the default_args in the URLPattern (and the type matches)

    # 3. For anything left over in URLPattern.default_arguments, complain.

    has_star_args = False
    if any(p.kind in [Parameter.VAR_KEYWORD, Parameter.VAR_POSITIONAL] for p in parameters.values()):
        errors.append(
            checks.Warning(
                f'View {callback_repr} signature contains *args or **kwarg syntax, can\'t properly check args',
                obj=url_pattern,
                id='urlchecker.W001',
            )
        )
        has_star_args = True

    used_from_sig = []
    parameter_list = list(sig.parameters)
    if parameter_list and parameter_list[0] == 'self':
        # HACK: we need to find some nice way to detect closures/bound methods,
        # while also getting the final signature.
        parameter_list.pop(0)
        used_from_sig.append('self')

    if not parameter_list or parameter_list[0] != 'request':
        if not has_star_args:
            if parameter_list:
                message = (
                    f'View {callback_repr} signature does not start with `request` parameter, '
                    f'found `{parameter_list[0]}`.'
                )
            else:
                message = f'View {callback_repr} signature does not have `request` parameter.'
            errors.append(
                checks.Error(
                    message,
                    obj=url_pattern,
                    id='urlchecker.E001',
                )
            )
    else:
        used_from_sig.append('request')

    # Everything in RoutePattern must be in signature
    for name, converter in url_pattern.pattern.converters.items():
        if has_star_args:
            used_from_sig.append(name)
        elif name in sig.parameters:
            used_from_sig.append(name)
            urlconf_type = get_converter_output_type(converter)
            sig_type = sig.parameters[name].annotation
            if urlconf_type == Parameter.empty:
                # TODO - only output this warning once per converter
                obj = converter.__class__
                errors.append(
                    checks.Warning(
                        f"Don\'t know output type for converter {obj.__module__}.{obj.__name__},"
                        " can\'t verify URL signatures.",
                        obj=obj,
                        id=f'urlchecker.W002.{obj.__module__}.{obj.__name__}',
                    )
                )
            elif sig_type == Parameter.empty:
                errors.append(
                    # This should be synced with W003 below.
                    checks.Warning(
                        f'View {callback_repr} missing type annotation for parameter `{name}`, can\'t check type.',
                        obj=url_pattern,
                        id='urlchecker.W003',
                    )
                )
            elif not _type_is_compatible(urlconf_type, sig_type):  # type: ignore
                errors.append(
                    checks.Error(
                        f'View {callback_repr} for parameter `{name}`,'  # type: ignore[union-attr]
                        f' annotated type {_name_type(sig_type)} does not match'  # type: ignore[union-attr]
                        f' expected `{_name_type(urlconf_type)}` from urlconf',  # type: ignore[union-attr]
                        obj=url_pattern,
                        id='urlchecker.E002',
                    )
                )
        else:
            errors.append(
                checks.Error(
                    f'View {callback_repr} signature does not contain `{name}` parameter',
                    obj=url_pattern,
                    id='urlchecker.E003',
                )
            )

    # Anything left over must have a default argument, either from signature, or from url_pattern.default_args
    used_from_default_args = []
    for name, param in sig.parameters.items():
        if name in used_from_sig:
            continue
        if name in url_pattern.default_args:
            used_from_default_args.append(name)
            sig_type = param.annotation
            default_arg = url_pattern.default_args[name]
            if sig_type == Parameter.empty:
                errors.append(
                    checks.Warning(
                        f'View {callback_repr} missing type annotation for parameter `{name}`, can\'t check type.',
                        obj=url_pattern,
                        id='urlchecker.W003',
                    )
                )
            elif not _instance_is_compatible(default_arg, sig_type):
                errors.append(
                    checks.Error(
                        f'View {callback_repr}: for parameter `{name}`,'
                        f' default argument {repr(default_arg)} in urlconf, type {_name_type(type(default_arg))},'
                        f' does not match annotated type {_name_type(sig_type)} from view signature',
                        obj=url_pattern,
                        id='urlchecker.E005',
                    )
                )
            continue
        if param.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD):
            # *args and **kwargs
            continue
        if param.default == Parameter.empty:
            errors.append(
                checks.Error(
                    f'View {callback_repr} signature contains `{name}` parameter without default or ULRconf parameter',
                    obj=url_pattern,
                    id='urlchecker.E004',
                )
            )

    # Anything left over in default_args is also an error
    for name in url_pattern.default_args:
        if name in used_from_default_args:
            continue
        errors.append(
            checks.Error(
                f'View {callback_repr} is being passed additional unexpected '
                f'parameter `{name}` from default arguments in urlconf',
                obj=url_pattern,
                id='urlchecker.E006',
            )
        )

    return errors


def _type_is_compatible(passed_type, accepted_type):
    try:
        return issubclass(passed_type, accepted_type)
    except TypeError as e:
        # For Python < 3.10 we get:
        #   Subscripted generics cannot be used with class and instance checks
        if 'Subscripted generics' in e.args[0]:
            # It's difficult to replicate Python 3.10 behaviour. So just let it pass,
            # rather than falsely say it's incompatible.
            return True
        elif 'parameterized generic' in e.args[0]:
            # Tricky to handle correctly
            return True
        else:
            raise  # pragma: no cover


def _instance_is_compatible(instance, accepted_type):
    try:
        return isinstance(instance, accepted_type)
    except TypeError as e:
        # Same as in _type_is_compatible
        if 'Subscripted generics' in e.args[0]:
            return True
        elif 'parameterized generic' in e.args[0]:
            return True
        else:
            raise  # pragma: no cover


def _name_type(type_hint):
    # Things like `Optional[int]`:
    # - repr() does a better job than `__name__`
    # - `__name__` is not available in some Python versions.
    return type_hint.__name__ if (hasattr(type_hint, "__name__") and type(type_hint) == type) else repr(type_hint)


CONVERTER_TYPES = {
    converters.IntConverter: int,
    converters.StringConverter: str,
    converters.UUIDConverter: uuid.UUID,
    converters.SlugConverter: str,
    converters.PathConverter: str,
}


def get_converter_output_type(converter) -> t.Union[int, str, uuid.UUID, t.Type[_empty]]:
    """Return the type that the converter will output."""
    for cls in converter.__class__.__mro__:
        if cls in CONVERTER_TYPES:
            return CONVERTER_TYPES[cls]

        if hasattr(cls, "to_python"):
            sig = signature(cls.to_python)
            if sig.return_annotation != Parameter.empty:
                return sig.return_annotation

    return Parameter.empty


class ViewSilencer:
    """Utility that checks whether errors for a view or set of views should be ignored."""

    def __init__(self, view_glob: str, errors: t.Iterable[str]):
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


def _build_view_silencers(silenced_views: t.Dict[str, str]) -> t.List[ViewSilencer]:
    return [
        ViewSilencer(view_glob=view_glob, errors=[f"urlchecker.{error}" for error in error_list.split(",")])
        for view_glob, error_list in silenced_views.items()
    ]


def _filter_errors(errors: t.List[Problem], silencers: t.List[ViewSilencer]) -> t.List[Problem]:
    return [error for error in errors if not any(silencer.matches(error) for silencer in silencers)]
