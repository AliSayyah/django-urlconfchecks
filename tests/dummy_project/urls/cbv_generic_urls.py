"""Django generic class-based views used by framework regression tests."""

from django.urls import path
from django.views.generic import DeleteView, DetailView, FormView, ListView, RedirectView, TemplateView

urlpatterns = [
    path("template/", TemplateView.as_view()),
    path("redirect/<int:pk>/", RedirectView.as_view(url="/target/<int:pk>/")),
    path("list/", ListView.as_view()),
    path("detail/<int:pk>/", DetailView.as_view()),
    path("form/", FormView.as_view()),
    path("delete/<int:pk>/", DeleteView.as_view()),
]
