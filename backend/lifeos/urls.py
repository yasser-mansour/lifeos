from django.contrib import admin
from django.urls import include, path

from apps.core.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/", include("apps.core.api_urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.dashboard.urls")),
    path("study/", include("apps.study.urls")),
    path("focus/", include("apps.study.urls_focus")),
    path("finance/", include("apps.finance.urls")),
    path("tasks/", include("apps.tasks.urls")),
    path("projects/", include("apps.projects.urls")),
    path("people/", include("apps.people.urls")),
    path("school/", include("apps.school.urls")),
    path("journal/", include("apps.journal.urls")),
    path("writing/", include("apps.writing.urls")),
    path("goals/", include("apps.goals.urls")),
    path("notes/", include("apps.notes.urls")),
    path("calendar/", include("apps.calendar_app.urls")),
    path("inbox/", include("apps.inbox.urls")),
    path("devices/", include("apps.devices.urls")),
    path("search/", include("apps.search.urls")),
]
