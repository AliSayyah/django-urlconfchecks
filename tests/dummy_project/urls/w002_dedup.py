"""URL patterns that use several untyped converters."""

from django.urls import include, path, register_converter

from tests.dummy_project import views


class SharedUntypedConverter:
    regex = r"[0-9]+"

    def to_python(self, value: str):
        return int(value)

    def to_url(self, value: int):
        return str(value)


class FirstUntypedConverter:
    regex = r"[0-9]+"

    def to_python(self, value: str):
        return int(value)

    def to_url(self, value: int):
        return str(value)


class SecondUntypedConverter:
    regex = r"[0-9]+"

    def to_python(self, value: str):
        return int(value)

    def to_url(self, value: int):
        return str(value)


register_converter(SharedUntypedConverter, "w002_shared")
register_converter(FirstUntypedConverter, "w002_first")
register_converter(SecondUntypedConverter, "w002_second")

urlpatterns = [
    path("shared/<w002_shared:year>/", views.year_archive),
    path("first/<w002_first:year>/", views.year_archive),
    path("second/<w002_second:year>/", views.year_archive),
    path("included/", include("tests.dummy_project.urls.w002_dedup_child")),
]
