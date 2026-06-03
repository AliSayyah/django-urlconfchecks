"""URL patterns with deferred annotations that should still fail compatibility checks."""

from __future__ import annotations

from django.urls import path


def future_annotation_mismatch_view(request, slug: int):
    """View with a deferred annotation that does not match the URL converter."""
    ...


urlpatterns = [
    path('future-mismatch/<str:slug>/', future_annotation_mismatch_view),
]
