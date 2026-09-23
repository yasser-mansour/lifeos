from django.urls import path

from apps.inbox import views

app_name = "inbox"

urlpatterns = [
    path("", views.inbox_list, name="list"),
    path("capture/", views.capture, name="capture"),
    path("<uuid:pk>/to-task/", views.convert_to_task, name="to_task"),
    path("<uuid:pk>/to-note/", views.convert_to_note, name="to_note"),
    path("<uuid:pk>/dismiss/", views.dismiss, name="dismiss"),
]
