from django.contrib import admin

from apps.journal.models import JournalEntry


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ("__str__", "date", "mood")
    date_hierarchy = "date"
