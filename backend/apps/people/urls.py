from django.urls import path

from apps.people import views

app_name = "people"

urlpatterns = [
    path("", views.person_list, name="list"),
    path("create/", views.person_create, name="create"),
    path("<uuid:pk>/panel/", views.person_detail_panel, name="detail_panel"),
    path("<uuid:pk>/", views.person_detail, name="detail"),
    path("<uuid:pk>/edit/", views.person_update, name="update"),
    path("<uuid:pk>/delete/", views.person_delete, name="delete"),
    path("<uuid:pk>/projects/link/", views.person_link_project, name="link_project"),
    path("<uuid:pk>/projects/<uuid:project_id>/unlink/", views.person_unlink_project, name="unlink_project"),
    # Organizations — same URL shape as Person above.
    path("organizations/create/", views.org_create, name="org_create"),
    path("organizations/<uuid:pk>/panel/", views.org_detail_panel, name="org_detail_panel"),
    path("organizations/<uuid:pk>/", views.org_detail, name="org_detail"),
    path("organizations/<uuid:pk>/edit/", views.org_update, name="org_update"),
    path("organizations/<uuid:pk>/archive/", views.org_archive_toggle, name="org_archive_toggle"),
    path("organizations/<uuid:pk>/delete/", views.org_delete, name="org_delete"),
    path("organizations/<uuid:pk>/projects/link/", views.org_link_project, name="org_link_project"),
    path("organizations/<uuid:pk>/projects/<uuid:project_id>/unlink/", views.org_unlink_project, name="org_unlink_project"),
]
