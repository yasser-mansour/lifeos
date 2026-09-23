from django.db import models

from apps.core.models import BaseModel

BOOK_STATUS_CHOICES = [("idea", "Idea"), ("drafting", "Drafting"), ("editing", "Editing"), ("complete", "Complete")]
CHAPTER_STATUS_CHOICES = [("draft", "Draft"), ("review", "Review"), ("final", "Final")]


class Book(BaseModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=10, choices=BOOK_STATUS_CHOICES, default="idea")

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("writing:book_detail", args=[self.pk])

    @property
    def total_word_count(self):
        return sum(self.chapters.values_list("word_count", flat=True))


class Chapter(BaseModel):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chapters")
    title = models.CharField(max_length=200, blank=True, default="Untitled Chapter")
    order = models.PositiveIntegerField(default=0)
    content = models.TextField(blank=True, default="")
    status = models.CharField(max_length=10, choices=CHAPTER_STATUS_CHOICES, default="draft")
    word_count = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.book.title} — {self.title}"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("writing:chapter_edit", args=[self.pk])

    def save(self, *args, **kwargs):
        self.word_count = len(self.content.split())
        super().save(*args, **kwargs)


class WritingNote(BaseModel):
    """Freeform research / idea notes attached to a book (spec: Writing →
    Ideas / Notes / research)."""

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="writing_notes")
    title = models.CharField(max_length=200, blank=True, default="")
    content = models.TextField(blank=True, default="")

    def __str__(self):
        return self.title or "Note"
