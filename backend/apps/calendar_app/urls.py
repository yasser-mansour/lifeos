from django.urls import path

from apps.calendar_app import views

app_name = "calendar_app"

urlpatterns = [
    path("", views.month_view, name="month"),
    path("week/", views.week_view, name="week"),
    path("day/", views.day_view, name="day"),
    path("agenda/", views.agenda_view, name="agenda"),
    path("event/new/", views.event_new, name="event_new"),
    path("event/<uuid:pk>/edit/", views.event_edit, name="event_edit"),
    path("event/<uuid:pk>/delete/", views.event_delete, name="event_delete"),
]
