"""views for tests."""

from typing import List, Optional

from django.views import View


def bad_view(slug: str):
    """View missing the `request` parameter."""
    ...


def special_case(request):
    """This is a special case.

    Args:
        request: The request object.

    Returns:
        A response object.
    """
    ...


def year_archive(request, year: int):
    """This is a year archive.

    Args:
        request: The request object.
        year: The year.

    Returns:
        A response object.
    """
    ...


def year_archive_untyped(request, year):
    """This is a year archive (with no type hint)."""
    ...


def month_archive(request, year: int, month: int):
    """This is a month archive.

    Args:
        request: The request object.
        year: The year.
        month: The month.

    Returns:
        A response object.
    """
    ...


def article_detail(request, year: int, month: int, slug: str):
    """This is an article detail.

    Args:
        request: The request object.
        year: The year.
        month: The month.
        slug: The slug.

    Returns:
        A response object.
    """
    ...


class CBVView(View):
    """This is a simple class based view."""

    def get(self, request):
        ...


def optional_arg_view(request, val: Optional[int] = None):
    ...


def parameterized_generic_view(request, val: List[int]):
    ...


try:

    def parameterized_generic_view_2(request, val: list[int]):  # type: ignore
        ...

except TypeError:
    parameterized_generic_view_2 = None  # type: ignore
