from django.contrib import admin

from apps.inbox.models import InboxItem


@admin.register(InboxItem)
class InboxItemAdmin(admin.ModelAdmin):
    list_display = ("__str__", "processed", "converted_to", "created_at")
