from django.contrib import admin

from apps.goals.models import Goal


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("title", "goal_type", "status", "deadline")
    list_filter = ("goal_type", "status")
