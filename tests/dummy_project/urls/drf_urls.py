"""URLConf using Django REST framework for tests."""

from django.urls import include, path
from rest_framework import routers, viewsets
from rest_framework.request import Request
from rest_framework.response import Response


class ArticleViewSet(viewsets.ViewSet):
    """Minimal DRF viewset for URLConf checks."""

    def list(self, request: Request):
        return Response([])

    def retrieve(self, request: Request, pk: str | None = None):
        return Response({"pk": pk})


router = routers.SimpleRouter()
router.register("articles", ArticleViewSet, basename="article")

urlpatterns = [
    path("api/", include(router.urls)),
]
