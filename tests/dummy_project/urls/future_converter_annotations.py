"""URL patterns whose converter annotations are stored as strings."""

from __future__ import annotations

from django.urls import path, register_converter


class FutureStringConverter:
    """Converter with a deferred return annotation."""

    regex = "[a-z]+"

    def to_python(self, value: str) -> str:
        return value

    def to_url(self, value: str) -> str:
        return value


def future_converter_view(request, slug: str):
    """View that matches the converter's return type."""
    ...


register_converter(FutureStringConverter, "futurestr")

urlpatterns = [
    path('future-converter/<futurestr:slug>/', future_converter_view),
]
