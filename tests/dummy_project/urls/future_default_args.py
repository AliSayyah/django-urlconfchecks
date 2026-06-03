"""URL patterns with deferred annotations checked against default arguments."""

from __future__ import annotations

from django.urls import path


def future_default_arg_view(request, year: int):
    """View whose deferred annotation matches the URLConf default argument."""
    ...


def future_default_arg_mismatch_view(request, year: int):
    """View whose deferred annotation does not match the URLConf default argument."""
    ...


urlpatterns = [
    path('future-default/', future_default_arg_view, kwargs={'year': 2024}),
    path('future-default-mismatch/', future_default_arg_mismatch_view, kwargs={'year': '2024'}),
]
