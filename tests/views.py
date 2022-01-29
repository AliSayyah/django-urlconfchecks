"""views for tests."""


def special_case(request):
    """This is a special case.

    Args:
        request: The request object.

    Returns:
        A response object.
    """
    pass


def year_archive(request, year: int):
    """This is a year archive.

    Args:
        request: The request object.
        year: The year.

    Returns:
        A response object.
    """
    pass


def month_archive(request, year: int, month: int):
    """This is a month archive.

    Args:
        request: The request object.
        year: The year.
        month: The month.

    Returns:
        A response object.
    """
    pass


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
    pass
