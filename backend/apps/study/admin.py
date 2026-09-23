from django.contrib import admin

from apps.study.models import StudyGoal, StudySession, StudySessionEvent


class StudySessionEventInline(admin.TabularInline):
    model = StudySessionEvent
    extra = 0


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "mode", "status", "started_at", "ended_at")
    list_filter = ("mode", "status")
    inlines = [StudySessionEventInline]


@admin.register(StudyGoal)
class StudyGoalAdmin(admin.ModelAdmin):
    list_display = ("period", "target_seconds", "active")
