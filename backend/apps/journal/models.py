from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel, Tag
from apps.goals.models import Goal
from apps.projects.models import Project

MOOD_CHOICES = [("great", "Great"), ("good", "Good"), ("okay", "Okay"), ("low", "Low"), ("rough", "Rough")]


class JournalEntry(BaseModel):
    date = models.DateField(default=timezone.localdate)
    title = models.CharField(max_length=200, blank=True, default="")
    body = models.TextField(blank=True, default="")
    mood = models.CharField(max_length=10, choices=MOOD_CHOICES, blank=True, default="")
    tags = models.ManyToManyField(Tag, blank=True, related_name="journal_entries")
    # Deliberately lightweight — an entry can optionally carry a project/goal
    # tag for context, but Journal is not a full bidirectional relationship
    # hub like Notes; there's no dedicated list UI on the Project/Goal side.
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="journal_entries")
    goal = models.ForeignKey(Goal, null=True, blank=True, on_delete=models.SET_NULL, related_name="journal_entries")

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name_plural = "journal entries"

    def __str__(self):
        return self.title or f"Entry — {self.date}"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("journal:detail", args=[self.pk])
