from django.urls import path

from apps.journal import views

app_name = "journal"

urlpatterns = [
    path("", views.entry_list, name="list"),
    path("new/", views.entry_new, name="new"),
    path("<uuid:pk>/", views.entry_detail, name="detail"),
    path("<uuid:pk>/autosave/", views.entry_autosave, name="autosave"),
    path("<uuid:pk>/delete/", views.entry_delete, name="delete"),
]
