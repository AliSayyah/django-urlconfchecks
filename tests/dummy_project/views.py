"""views for tests."""

from typing import Annotated, List, Optional, Union

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

    def get(self, request): ...


def non_optional_arg_view(request, val: int): ...


def optional_arg_view(request, val: Optional[int] = None): ...


def parameterized_generic_view(request, val: List[int]): ...


try:

    def parameterized_generic_view_2(request, val: list[int]): ...

except TypeError:
    parameterized_generic_view_2 = None


def annotated_int_view(request, val: Annotated[int, "year"]): ...


def union_int_str_view(request, val: Union[int, str]): ...


def bool_view(request, flag: bool): ...


def optional_list_view(request, val: Optional[list[int]] = None): ...


def tuple_view(request, val: tuple[int, str]): ...


def tuple_variadic_view(request, val: tuple[int, ...]): ...


def dict_view(request, val: dict[str, int]): ...


def set_view(request, val: set[int]): ...


def include_flag_view(request, flag: bool): ...


def include_flag_untyped_view(request, flag): ...


def include_no_kwargs_view(request): ...


def include_nested_view(request, outer: int, inner: str): ...


def include_override_view(request, flag: int): ...


def include_capture_override_view(request, flag: str): ...


def regex_slug_view(request, slug: str): ...


def regex_slug_int_view(request, slug: int): ...


def regex_leaf_no_slug_view(request): ...


def regex_no_slug_view(request): ...


def regex_required_extra_view(request, slug: str, missing: int): ...


def regex_untyped_view(request, slug): ...


def regex_child_converter_view(request, slug: str, year: int): ...


def regex_nested_view(request, outer: str, inner: str, year: int): ...


def regex_extra_view(request, flag: bool): ...


def regex_kwargs_view(request, **kwargs): ...


def positional_view(request, first: str, second: str): ...


def positional_one_view(request, first: str): ...


def positional_two_required_view(request, first: str, second: str): ...


def positional_args_view(request, *args): ...


def positional_parent_named_view(request, slug: str): ...


def default_pk_view(request, pk: int): ...


def regex_optional_view(request, page: str): ...


def regex_optional_default_view(request, page: str = ""): ...


def star_named_converter_view(request, pk: str, **kwargs): ...


def star_required_view(request, required, **kwargs): ...


def star_kwargs_view(request, **kwargs): ...


def star_args_surplus_view(request, *args): ...


def star_args_named_view(request, first: int, *args): ...
