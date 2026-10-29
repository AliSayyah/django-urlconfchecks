"""Hostile callback and converter corpus for checker crash detection."""

from __future__ import annotations

import builtins
import functools
import sys
import types
from dataclasses import dataclass, field
from uuid import uuid4

from django.conf import settings
from django.http import HttpResponse
from django.test.utils import override_settings
from django.urls import clear_url_caches, path, register_converter

from django_urlconfchecks.check import check_url_signatures


class BrokenSignature:
    """Callable with a property that breaks inspect.signature."""

    def __call__(self, request):
        return HttpResponse()

    @property
    def __signature__(self):
        """Raise while inspect.signature reads the property."""
        raise RuntimeError("signature property")


class BrokenMetadata:
    """Callable with hostile callback metadata."""

    @property
    def __module__(self):
        """Raise while callback metadata is formatted."""
        raise RuntimeError("module property")

    def __call__(self, request):
        return HttpResponse()


class BrokenQualname:
    """Callable whose qualname cannot be read."""

    def __getattribute__(self, name):
        """Raise for qualname access while allowing normal attributes."""
        if name == "__qualname__":
            raise RuntimeError("qualname property")
        return object.__getattribute__(self, name)

    def __call__(self, request):
        return HttpResponse()


class PropertyConverter:
    regex = r"[^/]+"

    @property
    def to_python(self):
        raise RuntimeError("to_python property")

    def to_url(self, value):
        return str(value)


class StaticConverter:
    regex = r"[0-9]+"

    @staticmethod
    def to_python(value: str) -> int:
        return int(value)

    def to_url(self, value):
        return str(value)


class CallableUrlconf:
    """Callable object that also exposes the URLconf protocol."""

    urlpatterns = []

    def __call__(self):
        return self.urlpatterns


@dataclass
class RobustnessResult:
    """Result of the hostile corpus run."""

    cases: int = 0
    exceptions: list[str] = field(default_factory=list)

    @property
    def exit_code(self):
        return int(bool(self.exceptions))


def _ensure_settings():
    if not settings.configured:
        settings.configure(ROOT_URLCONF="tests.fuzz._empty", SECRET_KEY="fuzz", ALLOWED_HOSTS=["*"])


def _register_converters():
    for converter, name in ((PropertyConverter, "fuzz_bad"), (StaticConverter, "fuzz_static")):
        try:
            register_converter(converter, name)
        except Exception as exc:
            if name not in str(exc):
                raise


def _good(request, value: str):
    return HttpResponse()


def _annotation(request, value):
    return HttpResponse()


_annotation.__annotations__["value"] = "NoSuchName"


def run_robustness() -> RobustnessResult:
    """Run every hostile corpus entry and report any checker exception."""
    _ensure_settings()
    _register_converters()
    partial = functools.partial(_good)
    cases = [
        ("print", builtins.print, path("x/", builtins.print)),
        ("len", builtins.len, path("x/", builtins.len)),
        ("class", BrokenSignature, path("x/", BrokenSignature)),
        ("broken-signature", BrokenSignature(), path("x/", BrokenSignature())),
        ("broken-module", BrokenMetadata(), path("x/", BrokenMetadata())),
        ("broken-qualname", BrokenQualname(), path("x/", BrokenQualname())),
        ("partial", partial, path("x/<str:value>/", partial)),
        ("partial-of-partial", functools.partial(partial), path("x/<str:value>/", functools.partial(partial))),
        ("unresolved-annotation", _annotation, path("x/<str:value>/", _annotation)),
        ("bad-converter", _good, path("x/<fuzz_bad:value>/", _good)),
        ("static-converter", _good, path("x/<fuzz_static:value>/", _good)),
    ]
    result = RobustnessResult(cases=len(cases) + 2)
    module_name = f"tests.fuzz._robust_{uuid4().hex}"
    module = types.ModuleType(module_name)
    try:
        sys.modules[module_name] = module
        for label, _callback, pattern in cases:
            module.__dict__["urlpatterns"] = [pattern]
            try:
                with override_settings(ROOT_URLCONF=module_name, URLCONFCHECKS_SILENCED_VIEWS={}):
                    clear_url_caches()
                    check_url_signatures(None)
            except Exception as exc:
                result.exceptions.append(f"{label}: {type(exc).__name__}: {exc}")
            finally:
                clear_url_caches()
        for label, patterns in (("empty", []),):
            module.__dict__["urlpatterns"] = patterns
            try:
                with override_settings(ROOT_URLCONF=module_name, URLCONFCHECKS_SILENCED_VIEWS={}):
                    clear_url_caches()
                    check_url_signatures(None)
            except Exception as exc:
                result.exceptions.append(f"{label}: {type(exc).__name__}: {exc}")
        try:
            with override_settings(ROOT_URLCONF=CallableUrlconf(), URLCONFCHECKS_SILENCED_VIEWS={}):
                clear_url_caches()
                check_url_signatures(None)
        except Exception as exc:
            result.exceptions.append(f"callable-urlconf: {type(exc).__name__}: {exc}")
    finally:
        clear_url_caches()
        sys.modules.pop(module_name, None)
    print(f"robustness: cases={result.cases} exceptions={len(result.exceptions)}")
    for item in result.exceptions:
        print(f"  {item}")
    return result
