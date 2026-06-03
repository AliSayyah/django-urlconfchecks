"""URL patterns with deferred converter annotations that should fail compatibility checks."""

from __future__ import annotations

from django.urls import path, register_converter


class FutureIntConverter:
    """Converter with a deferred return annotation that does not match the view."""

    regex = "[0-9]+"

    def to_python(self, value: str) -> int:
        return int(value)

    def to_url(self, value: int) -> str:
        return str(value)


def future_converter_mismatch_view(request, slug: str):
    """View that does not match the converter's return type."""
    ...


register_converter(FutureIntConverter, "futureint")

urlpatterns = [
    path('future-converter-mismatch/<futureint:slug>/', future_converter_mismatch_view),
]
