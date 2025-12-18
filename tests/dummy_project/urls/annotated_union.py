"""URL patterns for Annotated and Union-annotated views."""

from django.urls import path

from tests.dummy_project import views

urlpatterns = [
    path("annotated/<int:val>/", views.annotated_int_view),
    path("union-int/<int:val>/", views.union_int_str_view),
    path("union-str/<slug:val>/", views.union_int_str_view),
]
