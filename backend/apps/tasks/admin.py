from django.contrib import admin

from apps.tasks.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "priority", "due_date", "project", "course")
    list_filter = ("status", "priority")
    search_fields = ("title",)
