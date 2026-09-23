from django.urls import path

from apps.notes import views

app_name = "notes"

urlpatterns = [
    path("", views.note_list, name="list"),
    path("new/", views.note_new, name="new"),
    path("<uuid:pk>/", views.note_detail, name="detail"),
    path("<uuid:pk>/autosave/", views.note_autosave, name="autosave"),
    path("<uuid:pk>/delete/", views.note_delete, name="delete"),
]
