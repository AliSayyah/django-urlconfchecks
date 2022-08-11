"""URLs using custom converters and subclassed converters, with errors."""
from django.urls import path, register_converter
from django.urls.converters import IntConverter

from tests.dummy_project import views


class YearConverter:
    # Converter with type hint on to_python, should be handled automatically.
    regex = "[0-9]{4}"

    def to_python(self, value: str) -> int:
        return int(value)

    def to_url(self, value: int):
        return f"{value:04}"


class YearConverterNoTypeHint:
    # Converter with no type hint, should raise warning
    regex = "[0-9]{4}"

    def to_python(self, value: str):
        return int(value)

    def to_url(self, value: int):
        return f"{value:04}"


class YearConverterViaSubclass(IntConverter):
    # Subclass converter, no to_python method,
    # so we should default to the type inferred for base class
    regex = "[0-9]{4}"


class YearConverterAsFloat(IntConverter):
    # Subclass - for this case we should infer from the sig on to_python
    # method, not the base class (this float type will cause a type error)
    def to_python(self, value: str) -> float:
        return float(super().to_python(value))


register_converter(YearConverter, "yyyy")
register_converter(YearConverterNoTypeHint, "yyyy_notype")
register_converter(YearConverterViaSubclass, "yyyy_subclass")
register_converter(YearConverterAsFloat, "yyyy_float")

urlpatterns = [
    path('articles_yyyy/<yyyy:year>/', views.year_archive),
    path('articles_yyyy_notype/<yyyy_notype:year>/', views.year_archive),
    path('articles_yyyy_subclass/<yyyy_subclass:year>/', views.year_archive),
    path('articles_yyyy_float/<yyyy_float:year>/', views.year_archive),
]
