from django.contrib import admin

from apps.notes.models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("__str__", "project", "task", "person")
