from django.urls import path

from apps.study import views

app_name = "focus"

urlpatterns = [
    path("", views.focus_overview, name="overview"),
    path("start/", views.start, name="start"),
    path("active/", views.active, name="active"),
    path("active/status/", views.active_status, name="active_status"),
    path("active/pause/", views.action_pause, name="action_pause"),
    path("active/resume/", views.action_resume, name="action_resume"),
    path("active/finish/", views.action_finish, name="action_finish"),
    path("active/cancel/", views.action_cancel, name="action_cancel"),
    path("history/", views.focus_history, name="history"),
    path("statistics/", views.focus_statistics, name="statistics"),
    path("needs-classification/", views.needs_classification, name="needs_classification"),
    path("sessions/<uuid:pk>/", views.session_detail, name="session_detail"),
]
