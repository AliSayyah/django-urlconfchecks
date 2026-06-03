"""URL patterns whose view annotations are stored as strings."""

from __future__ import annotations

from django.urls import path


def future_annotation_view(request, slug: str):
    """View with annotations deferred by ``from __future__ import annotations``."""
    ...


urlpatterns = [
    path('future/<str:slug>/', future_annotation_view),
]
