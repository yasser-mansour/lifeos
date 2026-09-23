from django.urls import path

from apps.tasks import views

app_name = "tasks"

urlpatterns = [
    path("", views.task_list, name="list"),
    path("create/", views.task_create, name="create"),
    path("<uuid:pk>/complete/", views.task_complete, name="complete"),
    path("<uuid:pk>/edit/", views.task_update, name="update"),
    path("<uuid:pk>/panel/", views.task_detail_panel, name="detail_panel"),
    path("<uuid:pk>/", views.task_detail, name="detail"),
]
