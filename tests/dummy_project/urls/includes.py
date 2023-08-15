"""URLs for testing `django.urls.include` support."""

from django.urls import include, path

from tests.dummy_project import views

# When using 'include' which should include parameters collected from before

urlpatterns = [
    # All these are valid:
    path(
        "<int:year>/",
        include(
            [
                # `year` is passed from above
                path('', views.year_archive, name="good-year-archive"),
                path('<int:month>/', views.month_archive, name="good-month-archive"),
                path('<int:month>/<slug:slug>/', views.article_detail, name="good-detail"),
                path(
                    'nested/<int:month>/',
                    include(
                        [
                            # `year` and `month` are passed from above
                            path('', views.month_archive, name="good-month-archive-nested"),
                        ]
                    ),
                ),
            ]
        ),
    ),
    # These are not
    path(
        "bad-include/<slug:slug>/",
        include(
            [
                # year_archive does not take `slug` param
                path('bad-year/<int:year>', views.year_archive, name="bad-year-archive"),
            ]
        ),
    ),
]
