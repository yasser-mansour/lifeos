from django.contrib import admin

from apps.calendar_app.models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "start", "end", "category")
    date_hierarchy = "start"
