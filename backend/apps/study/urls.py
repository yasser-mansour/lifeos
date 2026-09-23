from django.urls import path

from apps.study import views

app_name = "study"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("start/", views.start, name="start"),
    path("active/", views.active, name="active"),
    path("active/status/", views.active_status, name="active_status"),
    path("active/pause/", views.action_pause, name="action_pause"),
    path("active/resume/", views.action_resume, name="action_resume"),
    path("active/finish/", views.action_finish, name="action_finish"),
    path("active/cancel/", views.action_cancel, name="action_cancel"),
    path("history/", views.history, name="history"),
    path("statistics/", views.statistics, name="statistics"),
    path("goals/", views.goals, name="goals"),
    path("sessions/<uuid:pk>/", views.session_detail, name="session_detail"),
]
