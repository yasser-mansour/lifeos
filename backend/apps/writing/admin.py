from django.contrib import admin

from apps.writing.models import Book, Chapter, WritingNote


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "status")
    inlines = [ChapterInline]


@admin.register(WritingNote)
class WritingNoteAdmin(admin.ModelAdmin):
    list_display = ("title", "book")
