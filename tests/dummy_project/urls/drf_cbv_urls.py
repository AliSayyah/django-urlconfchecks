"""Django REST framework class-based view handler checks."""

from django.urls import include, path
from rest_framework import routers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView


class ArticleAPIView(APIView):
    def get(self, request, pk: int):
        return Response({"pk": pk})


class BadAPIView(APIView):
    def get(self, request, pk: str):
        return Response({"pk": pk})


class ArticleViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response([])

    def retrieve(self, request, pk: str | None = None):
        return Response({"pk": pk})

    @action(detail=True, methods=["get"])
    def custom(self, request, pk: str):
        return Response({"pk": pk})


class BadViewSet(viewsets.ViewSet):
    def retrieve(self, request, pk: int):
        return Response({"pk": pk})

    @action(detail=True, methods=["get"])
    def broken(self, request):
        return Response({})


router = routers.SimpleRouter()
router.register("articles", ArticleViewSet, basename="article")
router.register("bad", BadViewSet, basename="bad")

urlpatterns = [
    path("api/<int:pk>/", ArticleAPIView.as_view()),
    path("bad/<int:pk>/", BadAPIView.as_view()),
    path("", include(router.urls)),
]
