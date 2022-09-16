"""Views with Optional args."""
from django.urls import path

from tests.dummy_project import views

urlpatterns = [
    # All these are valid
    path('good-with-val/<int:val>', views.optional_arg_view),
    path('good-without-val/', views.optional_arg_view),
    path('good-with-kwarg1/', views.optional_arg_view, kwargs={'val': None}),
    path('good-with-kwarg2/', views.optional_arg_view, kwargs={'val': 123}),
    # These are not
    path('bad-with-val/<path:val>', views.optional_arg_view),
    path('bad-with-kwarg1/', views.optional_arg_view, kwargs={'val': "abc"}),
]
