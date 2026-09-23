from django.urls import path

from apps.projects import views

app_name = "projects"

urlpatterns = [
    path("", views.project_list, name="list"),
    path("create/", views.project_create, name="create"),
    path("<uuid:pk>/", views.project_detail, name="detail"),
    path("<uuid:pk>/edit/", views.project_update, name="update"),
    path("<uuid:pk>/people/link/", views.project_link_person, name="link_person"),
    path("<uuid:pk>/people/<uuid:person_id>/unlink/", views.project_unlink_person, name="unlink_person"),
]
