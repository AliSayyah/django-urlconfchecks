"""Views with parameterized generics."""

from django.urls import path

from tests.dummy_project import views

# Currently we aren't able to check to these types (we just allow them to pass
# and don't crash), but this lists some of the cases we'd need to handle

urlpatterns = [
    # All these are valid
    path('good-with-kwarg2/', views.parameterized_generic_view, kwargs={'val': [123]}),
    # These are not
    path('bad-with-val/<path:val>', views.parameterized_generic_view),
    path('bad-with-kwarg1/', views.parameterized_generic_view, kwargs={'val': "abc"}),
    path('bad-with-kwarg2/', views.parameterized_generic_view, kwargs={'val': ["abc"]}),
]

if views.parameterized_generic_view_2 is not None:
    urlpatterns = [
        # All these are valid
        path('good-2-with-kwarg2/', views.parameterized_generic_view_2, kwargs={'val': [123]}),
        path('good-optional-list/', views.optional_list_view, kwargs={'val': [1, 2, 3]}),
        path('good-tuple-fixed/', views.tuple_view, kwargs={'val': (1, 'x')}),
        path('good-tuple-variadic/', views.tuple_variadic_view, kwargs={'val': (1, 2, 3)}),
        path('good-dict/', views.dict_view, kwargs={'val': {'a': 1}}),
        path('good-set/', views.set_view, kwargs={'val': {1, 2}}),
        # These are not
        path('bad-2-with-val/<path:val>', views.parameterized_generic_view_2),
        path('bad-2-with-kwarg1/', views.parameterized_generic_view_2, kwargs={'val': "abc"}),
        path('bad-2-with-kwarg2/', views.parameterized_generic_view_2, kwargs={'val': ["abc"]}),
        path('bad-tuple-with-val/<path:val>', views.tuple_view),
        path('bad-tuple-wronglen/', views.tuple_view, kwargs={'val': (1, 2, 3)}),
        path('bad-tuple-wrong-elem/', views.tuple_view, kwargs={'val': (1, 2)}),
        path('bad-tuple-variadic/', views.tuple_variadic_view, kwargs={'val': ('a',)}),
        path('bad-dict/', views.dict_view, kwargs={'val': {1: 'a'}}),
        path('bad-set/', views.set_view, kwargs={'val': {'a'}}),
    ]
