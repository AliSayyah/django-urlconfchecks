"""URL patterns with deferred annotations that cannot be resolved."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.urls import path

if TYPE_CHECKING:

    class MissingType:
        """Type-checker-only annotation target."""


def unresolved_annotation_view(request, slug: MissingType):
    """View with a deferred annotation that is intentionally unavailable."""
    ...


urlpatterns = [
    path('future-unresolved/<str:slug>/', unresolved_annotation_view),
]
