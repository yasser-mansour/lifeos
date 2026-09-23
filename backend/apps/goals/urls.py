from django.urls import path

from apps.goals import views

app_name = "goals"

urlpatterns = [
    path("", views.goal_list, name="list"),
    path("create/", views.goal_create, name="create"),
    path("<uuid:pk>/", views.goal_detail, name="detail"),
    path("<uuid:pk>/edit/", views.goal_update, name="update"),
    path("<uuid:pk>/delete/", views.goal_delete, name="delete"),
    path("<uuid:pk>/progress/", views.goal_update_progress, name="update_progress"),
]
