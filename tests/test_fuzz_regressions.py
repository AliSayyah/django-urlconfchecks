"""Regression tests for issues found by the URL checker fuzzing run."""

import sys
import types
import uuid
from typing import Literal, NewType, TypeVar

import pytest
from django.http import HttpResponse
from django.test.utils import override_settings
from django.urls import clear_url_caches, include, path, re_path, register_converter
from django.views import View

from django_urlconfchecks.check import _make_callback_repr, check_url_signatures


def _checked_urlconf(patterns):
    name = f"tests._fuzz_regression_{uuid.uuid4().hex}"
    module = types.ModuleType(name)
    module.__dict__["urlpatterns"] = patterns
    sys.modules[name] = module
    try:
        with override_settings(ROOT_URLCONF=name, URLCONFCHECKS_SILENCED_VIEWS={}):
            clear_url_caches()
            return check_url_signatures(None)
    finally:
        clear_url_caches()
        sys.modules.pop(name, None)


def _ids(errors):
    return [error.id for error in errors]


def test_positional_only_route_keyword_is_not_accepted_and_required_parameter_remains_missing():
    def view(request, item: int, /):
        return HttpResponse()

    errors = _checked_urlconf([path("x/<int:item>/", view)])
    assert _ids(errors) == ["urlchecker.E003", "urlchecker.E004"]
    assert "`item` parameter" in errors[0].msg


def test_positional_only_route_keyword_can_be_absorbed_by_kwargs():
    def view(request, item: int, /, **kwargs):
        return HttpResponse()

    errors = _checked_urlconf([path("x/<int:item>/", view)])
    assert "urlchecker.E003" not in _ids(errors)
    assert "urlchecker.E006" not in _ids(errors)
    assert "urlchecker.E004" in _ids(errors)


def test_positional_only_capture_from_include_is_checked_as_a_keyword():
    def view(request, item: int, /):
        return HttpResponse()

    child = [path("x/", view)]
    errors = _checked_urlconf([path("<int:item>/", include((child, "fuzz")))])
    assert _ids(errors) == ["urlchecker.E003", "urlchecker.E004"]


def test_request_must_have_a_positional_slot_but_varargs_are_valid():
    def keyword_only(*, request):
        return HttpResponse()

    def kwargs_only(**kwargs):
        return HttpResponse()

    def varargs(*args, **kwargs):
        return HttpResponse()

    def normal(request, **kwargs):
        return HttpResponse()

    errors = _checked_urlconf(
        [
            path("keyword/", keyword_only),
            path("kwargs/", kwargs_only),
            path("varargs/", varargs),
            path("normal/", normal),
        ]
    )
    assert sum(error.id == "urlchecker.E001" for error in errors) == 2
    assert all(
        any(name in error.msg for name in ("keyword_only", "kwargs_only"))
        for error in errors
        if error.id == "urlchecker.E001"
    )


def test_negative_lookaround_named_groups_are_not_route_kwargs_and_positive_groups_are():
    def no_capture(request):
        return HttpResponse()

    def positive_capture(request, value: str):
        return HttpResponse()

    errors = _checked_urlconf(
        [
            re_path(r"^negative/(?!(?P<value>a))b/$", no_capture),
            re_path(r"^positive/(?=(?P<value>b))b/$", positive_capture),
        ]
    )
    assert errors == []


def test_cbv_setup_is_checked():
    class SetupView(View):
        def setup(self, request):
            super().setup(request)

        def get(self, request, item: int):
            return HttpResponse()

    errors = _checked_urlconf([path("x/<int:item>/", SetupView.as_view())])
    assert _ids(errors) == ["urlchecker.E003"]
    assert ".SetupView.setup" in errors[0].msg


def test_cbv_setup_with_matching_parameters_is_valid():
    class SetupView(View):
        def setup(self, request, item: int):
            super().setup(request)
            self.item = item

        def get(self, request, item: int):
            return HttpResponse()

    assert _checked_urlconf([path("x/<int:item>/", SetupView.as_view())]) == []


@pytest.mark.parametrize("descriptor", ["staticmethod", "classmethod"])
def test_cbv_staticmethod_and_classmethod_handlers_are_checked(descriptor):
    if descriptor == "staticmethod":

        class DescriptorView(View):
            get = staticmethod(lambda request: HttpResponse())

    else:

        class DescriptorView(View):
            @classmethod
            def get(cls, request):
                return HttpResponse()

    errors = _checked_urlconf([path("x/<int:item>/", DescriptorView.as_view())])
    assert _ids(errors) == ["urlchecker.E003"]
    assert ".DescriptorView.get" in errors[0].msg


@pytest.mark.parametrize("descriptor", ["staticmethod", "classmethod"])
def test_cbv_staticmethod_and_classmethod_handlers_with_matching_parameters_are_valid(descriptor):
    if descriptor == "staticmethod":

        class DescriptorView(View):
            @staticmethod
            def get(request, item: int):
                return HttpResponse()

    else:

        class DescriptorView(View):
            @classmethod
            def get(cls, request, item: int):
                return HttpResponse()

    assert _checked_urlconf([path("x/<int:item>/", DescriptorView.as_view())]) == []


def test_cbv_callable_object_handler_keeps_request_parameter():
    class CallableHandler:
        def __call__(self, request, item: int):
            return HttpResponse()

    class CallableView(View):
        get = CallableHandler()

    errors = _checked_urlconf([path("x/<int:item>/", CallableView.as_view())])
    assert "urlchecker.E001" not in _ids(errors)
    assert errors == []


def test_special_annotations_match_converter_types_and_extra_values():
    UserId = NewType("UserId", int)
    BoundInt = TypeVar("BoundInt", bound=int)
    Constrained = TypeVar("Constrained", int, str)

    def literal(request, value: Literal[1, 2]):
        return HttpResponse()

    def new_type(request, value: UserId):
        return HttpResponse()

    def bound(request, value: BoundInt):
        return HttpResponse()

    def constrained(request, value: Constrained):
        return HttpResponse()

    def extra(request, value: Literal[1, 2]):
        return HttpResponse()

    errors = _checked_urlconf(
        [
            path("literal/<int:value>/", literal),
            path("new/<int:value>/", new_type),
            path("bound/<int:value>/", bound),
            path("constrained/<int:value>/", constrained),
            path("extra/", extra, {"value": 1}),
        ]
    )
    assert errors == []

    def bad_literal(request, value: Literal["1"]):
        return HttpResponse()

    def bad_extra(request, value: Literal[2]):
        return HttpResponse()

    errors = _checked_urlconf([path("literal/<int:value>/", bad_literal), path("extra/", bad_extra, {"value": 1})])
    assert _ids(errors) == ["urlchecker.E002", "urlchecker.E005"]

    TextId = NewType("TextId", str)

    def bad_new_type(request, value: TextId):
        return HttpResponse()

    BadBound = TypeVar("BadBound", bound=str)

    def bad_bound(request, value: BadBound):
        return HttpResponse()

    errors = _checked_urlconf([path("new/<int:value>/", bad_new_type), path("bound/<int:value>/", bad_bound)])
    assert _ids(errors) == ["urlchecker.E002", "urlchecker.E002"]


def test_hostile_signature_callback_emits_w005():
    class BrokenCallable:
        @property
        def __signature__(self):
            raise RuntimeError("signature property")

        def __call__(self, request):
            return HttpResponse()

    errors = _checked_urlconf([path("x/", BrokenCallable())])
    assert _ids(errors) == ["urlchecker.W005"]
    assert "RuntimeError: signature property" in errors[0].msg


def test_hostile_signature_class_callback_emits_w005():
    class BrokenMeta(type):
        @property
        def __signature__(cls):
            raise RuntimeError("class signature")

    class BrokenClass(metaclass=BrokenMeta):
        def __init__(self, request):
            pass

    errors = _checked_urlconf([path("x/", BrokenClass)])
    assert _ids(errors) == ["urlchecker.W005"]
    assert "RuntimeError: class signature" in errors[0].msg


def test_hostile_signature_cbv_handler_emits_w005_with_handler_repr():
    class BrokenHandler:
        @property
        def __signature__(self):
            raise RuntimeError("handler signature")

        def __call__(self, request):
            return HttpResponse()

    class BrokenView(View):
        get = BrokenHandler()

    errors = _checked_urlconf([path("x/", BrokenView.as_view())])
    assert _ids(errors) == ["urlchecker.W005"]
    assert "BrokenView.get" in errors[0].msg


def test_hostile_callback_metadata_has_safe_fallback_repr():
    class HostileMetadata:
        def __getattribute__(self, name):
            if name in {"__module__", "__qualname__"}:
                raise RuntimeError("metadata property")
            return super().__getattribute__(name)

        def __call__(self, request):
            return HttpResponse()

    assert _make_callback_repr(HostileMetadata()).endswith(".HostileMetadata")
    assert _checked_urlconf([path("x/", HostileMetadata())]) == []


def test_converter_with_non_callable_to_python_emits_w002():
    class BrokenConverter:
        regex = r"[0-9]+"
        to_python = property(lambda self: int)

        def to_url(self, value):
            return str(value)

    register_converter(BrokenConverter, "broken_fuzz_converter")

    def view(request, value: int):
        return HttpResponse()

    errors = _checked_urlconf([path("x/<broken_fuzz_converter:value>/", view)])
    assert len(errors) == 1
    assert errors[0].id.startswith("urlchecker.W002.")


def test_converter_with_uninspectable_to_python_emits_w002():
    class BrokenToPython:
        @property
        def __signature__(self):
            raise RuntimeError("converter signature")

        def __call__(self, value):
            return int(value)

    class BrokenConverter:
        regex = r"[0-9]+"
        to_python = BrokenToPython()

        def to_url(self, value):
            return str(value)

    register_converter(BrokenConverter, "broken_fuzz_signature_converter")

    def view(request, value: int):
        return HttpResponse()

    errors = _checked_urlconf([path("x/<broken_fuzz_signature_converter:value>/", view)])
    assert len(errors) == 1
    assert errors[0].id.startswith("urlchecker.W002.")


def test_request_parameter_with_another_name_is_not_reported_as_missing_a_source():
    """Django passes the request to the first positional parameter whatever its name."""

    def view(req, **kwargs):
        return HttpResponse()

    errors = _checked_urlconf([path("x/<int:pk>/", view)])
    assert _ids(errors) == ["urlchecker.W001"]


def test_positional_url_values_skip_the_request_parameter_whatever_its_name():
    def view(req, a: str):
        return HttpResponse()

    errors = _checked_urlconf([re_path(r"^x/(\w+)/$", view)])
    # Only the (name-based) E001; `a` receives the positional value, nothing is unsourced.
    assert _ids(errors) == ["urlchecker.E001"]
    assert "found `req`" in errors[0].msg


def test_positional_url_value_and_keyword_for_the_same_parameter():
    """Found by the fuzz tool: Django raises "got multiple values for argument"."""

    def view(request, parent):
        return HttpResponse()

    errors = _checked_urlconf([path("<int:parent>/", include([re_path(r"^f/([a-z]+)/$", view)]))])
    assert "urlchecker.E008" in _ids(errors)
    assert "receives `parent` both as a positional argument" in next(e for e in errors if e.id == "urlchecker.E008").msg


def test_positional_only_parameter_and_keyword_of_the_same_name_do_not_collide():
    def view(request, parent, /, **kwargs):
        return HttpResponse()

    errors = _checked_urlconf([path("<int:parent>/", include([re_path(r"^f/([a-z]+)/$", view)]))])
    assert "urlchecker.E008" not in _ids(errors)


def test_optional_group_supplied_by_an_include_kwarg_is_always_present():
    """Found by the fuzz tool: when the group doesn't match, Django keeps the include() kwarg."""

    def view(request, p0: str | int):
        return HttpResponse()

    with_fallback = _checked_urlconf([path("x/", include([re_path(r"^f/(?P<p0>[a-z]+)?/$", view)]), {"p0": 3})])
    without_fallback = _checked_urlconf([path("x/", include([re_path(r"^f/(?P<p0>[a-z]+)?/$", view)]))])
    assert "urlchecker.W004" not in _ids(with_fallback)
    assert "urlchecker.W004" in _ids(without_fallback)
