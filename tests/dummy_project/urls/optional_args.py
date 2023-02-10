"""Views with Optional args."""
from typing import Optional

from django.urls import path, register_converter

from tests.dummy_project import views


class OptInt:
    """Optional int - zero or more digits, converted to None if zero length."""

    regex = r"\d*"

    def to_python(self, value) -> Optional[int]:
        return None if value == "" else int(value)

    def to_url(self, value):
        return "" if value is None else str(value)


class OptStr:
    """Optional str, converted to None if zero length."""

    regex = r".*"

    def to_python(self, value) -> Optional[str]:
        return None if value == "" else value

    def to_url(self, value):
        return "" if value is None else str(value)


register_converter(OptInt, "optint")
register_converter(OptStr, "optstr")


# We currently don't check all of these properly. Our tests ensure that
# valid ones are not rejected, but not that invalid ones are rejected.
urlpatterns = [
    # All these are valid.
    path('good-with-val/<int:val>', views.optional_arg_view),
    path('good-without-val/', views.optional_arg_view),
    path('good-with-kwarg1/', views.optional_arg_view, kwargs={'val': None}),
    path('good-with-kwarg2/', views.optional_arg_view, kwargs={'val': 123}),
    path('good-with-optint/<optint:val>', views.optional_arg_view),
    # These are not
    path('bad-with-val/<path:val>', views.optional_arg_view),
    path('bad-with-kwarg1/', views.optional_arg_view, kwargs={'val': "abc"}),
    path('bad-with-optint/<optint:val>', views.non_optional_arg_view),
    path('bad-with-optstr/<optstr:val>', views.non_optional_arg_view),
    path('bad-with-optstr-2/<optstr:val>', views.optional_arg_view),
]
