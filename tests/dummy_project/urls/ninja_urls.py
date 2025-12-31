"""URLConf using Django Ninja for tests."""

from django.urls import path
from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/items/{item_id}")
def get_item(request, item_id: int):
    return {"item_id": item_id}


urlpatterns = [
    path("api/", api.urls),
]
