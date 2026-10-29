"""Class-based views used by the CBV checker tests."""

from django.http import HttpResponse
from django.views import View


class InheritedMixin:
    """A user mixin whose handler must keep the URL class name in reports."""

    def get(self, request, pk: int):
        return HttpResponse()


class CleanView(InheritedMixin, View):
    def post(self, request, pk: int):
        return HttpResponse()


class BadMixin:
    """A user mixin whose faulty handler is reported under the URL's class name."""

    def get(self, request):
        return HttpResponse()


class InheritedBadView(BadMixin, View):
    pass


class BadView(View):
    def get(self, request, pk: str):
        return HttpResponse()

    def post(self, request):
        return HttpResponse()


class NoRequestView(View):
    def get(self, pk: int):
        return HttpResponse()


class RequiredView(View):
    def get(self, request, pk: int, required: int):
        return HttpResponse()


class StarView(View):
    def get(self, request, pk: str, *args, **kwargs):
        return HttpResponse()


class DispatchView(View):
    def dispatch(self, request, pk: str):
        return HttpResponse()

    def get(self, request, pk: int):
        return HttpResponse()


class ExplicitHeadView(View):
    def get(self, request, pk: int):
        return HttpResponse()

    def head(self, request, pk: str):
        return HttpResponse()


class AsyncView(View):
    async def get(self, request, pk: int):
        return HttpResponse()

    async def post(self, request, pk: str):
        return HttpResponse()


class IncludeView(View):
    def get(self, request, pk: int, flag: bool):
        return HttpResponse()


class ExtraView(View):
    def get(self, request, flag: int):
        return HttpResponse()
