from django.contrib import admin

from apps.core.models import ActivityEvent, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "default_currency", "theme", "onboarded_at")


@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    list_display = ("verb", "category", "created_at", "device_name")
    list_filter = ("category",)
    date_hierarchy = "created_at"
