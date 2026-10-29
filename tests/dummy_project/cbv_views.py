"""Class-based views used by the CBV checker tests."""

from django.http import HttpResponse
from django.views import View


class InheritedMixin:
    """A user mixin whose handler must keep the URL class name in reports."""

    def get(self, request, pk: int):
        return HttpResponse(f"get {pk}")


class CleanView(InheritedMixin, View):
    def post(self, request, pk: int):
        return HttpResponse(f"post {pk}")


class BadMixin:
    """A user mixin whose faulty handler is reported under the URL's class name."""

    def get(self, request):
        return HttpResponse("get")


class InheritedBadView(BadMixin, View):
    pass


class BadView(View):
    def get(self, request, pk: str):
        return HttpResponse(f"get {pk}")

    def post(self, request):
        return HttpResponse("post")


class NoRequestView(View):
    def get(self, pk: int):
        return HttpResponse(f"get {pk}")


class RequiredView(View):
    def get(self, request, pk: int, required: int):
        return HttpResponse(f"get {pk} {required}")


class StarView(View):
    def get(self, request, pk: str, *args, **kwargs):
        return HttpResponse(f"get {pk}")


class DispatchView(View):
    def dispatch(self, request, pk: str):
        return HttpResponse("dispatch")

    def get(self, request, pk: int):
        return HttpResponse(f"get {pk}")


class ExplicitHeadView(View):
    def get(self, request, pk: int):
        return HttpResponse(f"get {pk}")

    def head(self, request, pk: str):
        return HttpResponse(f"head {pk}")


class AsyncView(View):
    async def get(self, request, pk: int):
        return HttpResponse(f"get {pk}")

    async def post(self, request, pk: str):
        return HttpResponse(f"post {pk}")


class IncludeView(View):
    def get(self, request, pk: int, flag: bool):
        return HttpResponse(f"get {pk} {flag}")


class ExtraView(View):
    def get(self, request, flag: int):
        return HttpResponse(f"get {flag}")
