"""URL patterns that exercise Django's argument merge rules."""

from django.urls import include, path, re_path

from tests.dummy_project import views

urlpatterns = [
    # Include kwargs are inherited, and child path kwargs override them.
    path("include-good/", include([path("good/", views.include_flag_view)]), {"flag": True}),
    path("include-wrong-type/", include([path("wrong-type/", views.include_flag_view)]), {"flag": "yes"}),
    path("include-untyped/", include([path("untyped/", views.include_flag_untyped_view)]), {"flag": True}),
    path("include-extra/", include([path("extra/", views.include_no_kwargs_view)]), {"flag": True}),
    path(
        "include-nested/",
        include(
            [
                path(
                    "inner/",
                    include([path("nested/", views.include_nested_view)]),
                    {"inner": "value"},
                )
            ]
        ),
        {"outer": 1},
    ),
    path(
        "include-child-override/",
        include([path("child-override/", views.include_override_view, {"flag": 1})]),
        {
            "flag": "wrong",
        },
    ),
    path(
        "include-capture-override/<int:flag>/",
        include([path("capture-override/", views.include_capture_override_view)]),
        {"flag": "replacement"},
    ),
    # Named regex groups are keyword arguments, including through includes.
    re_path(r"^regex-parent/(?P<slug>[-\w]+)/", include([path("parent-ok/", views.regex_slug_view)])),
    re_path(
        r"^regex-parent-missing/(?P<slug>[-\w]+)/",
        include([path("parent-missing/", views.regex_no_slug_view)]),
    ),
    re_path(
        r"^regex-parent-int/(?P<slug>[-\w]+)/",
        include([path("parent-int/", views.regex_slug_int_view)]),
    ),
    re_path(
        r"^regex-child-converter/(?P<slug>[-\w]+)/",
        include([path("child-converter/<int:year>/", views.regex_child_converter_view)]),
    ),
    re_path(
        r"^regex-nested/(?P<outer>[-\w]+)/",
        include(
            [
                re_path(
                    r"^(?P<inner>[-\w]+)/",
                    include([path("nested-regex/<int:year>/", views.regex_nested_view)]),
                )
            ]
        ),
    ),
    # Leaf re_path() views and their extra kwargs.
    re_path(r"^regex-leaf/(?P<slug>[-\w]+)/$", views.regex_slug_view),
    re_path(r"^regex-leaf-int/(?P<slug>[-\w]+)/$", views.regex_slug_int_view),
    re_path(r"^regex-leaf-missing/(?P<slug>[-\w]+)/$", views.regex_leaf_no_slug_view),
    re_path(r"^regex-leaf-extra/(?P<slug>[-\w]+)/$", views.regex_required_extra_view),
    re_path(r"^regex-leaf-untyped/(?P<slug>[-\w]+)/$", views.regex_untyped_view),
    re_path(r"^regex-leaf-kwargs/$", views.regex_kwargs_view, kwargs={"flag": True}),
    re_path(r"^regex-leaf-extra-value/$", views.regex_extra_view, kwargs={"flag": True}),
    # Unnamed regex groups are positional unless a named group appears below.
    re_path(r"^positional/(\w+)/(\w+)/$", views.positional_view),
    re_path(r"^positional-too-many/(\w+)/(\w+)/$", views.positional_one_view),
    re_path(r"^positional-too-few/(\w+)/$", views.positional_two_required_view),
    re_path(
        r"^positional-parent/(\w+)/",
        include([re_path(r"^(?P<slug>\w+)/$", views.positional_parent_named_view)]),
    ),
    re_path(r"^positional-star/(\w+)/$", views.positional_args_view),
    # Star-argument callbacks still check named parameters and required leftovers.
    path(
        "star-varkw-mismatch/",
        include([path("varkw-mismatch/<int:pk>/", views.star_named_converter_view)]),
    ),
    path("star-varkw-required/", include([path("varkw-required/", views.star_required_view)])),
    path(
        "star-varkw-extra/",
        include([path("varkw-extra/", views.star_kwargs_view)]),
        {"flag": True},
    ),
    re_path(r"^star-varargs-surplus/(\w+)/(\w+)/$", views.star_args_surplus_view),
    re_path(r"^star-varargs-named/(\w+)/$", views.star_args_named_view),
    # URL defaults override captured values with the same name.
    path("default-good/<int:pk>/", views.default_pk_view, {"pk": 42}),
    path("default-wrong/<int:pk>/", views.default_pk_view, {"pk": "wrong"}),
]
