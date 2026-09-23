from django.db import models
from django.utils import timezone

from apps.core.choices import PRIORITY_CHOICES
from apps.core.models import BaseModel, Tag
from apps.people.models import Person
from apps.projects.models import Project
from apps.school.models import Course

STATUS_CHOICES = [
    ("inbox", "Inbox"),
    ("todo", "Todo"),
    ("in_progress", "In Progress"),
    ("waiting", "Waiting"),
    ("done", "Done"),
    ("cancelled", "Cancelled"),
]

OPEN_STATUSES = ["inbox", "todo", "in_progress", "waiting"]


class Task(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="todo", db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal")

    due_date = models.DateField(null=True, blank=True)
    due_time = models.TimeField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)

    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
    person = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
    tags = models.ManyToManyField(Tag, blank=True, related_name="tasks")

    estimated_minutes = models.PositiveIntegerField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Waiting-for specifics (spec: "Waiting For deserves dedicated behavior")
    waiting_on = models.CharField(max_length=150, blank=True, default="")
    waiting_for_person = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name="waiting_tasks")
    follow_up_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-priority", "due_date", "-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("tasks:detail", args=[self.pk])

    @property
    def is_overdue(self):
        if not self.due_date or self.status in ("done", "cancelled"):
            return False
        return self.due_date < timezone.localdate()

    @property
    def is_waiting_overdue(self):
        return self.status == "waiting" and self.follow_up_date and self.follow_up_date < timezone.localdate()

    def mark_done(self):
        self.status = "done"
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])

    def mark_waiting(self, waiting_on="", follow_up_date=None):
        self.status = "waiting"
        if waiting_on:
            self.waiting_on = waiting_on
        if follow_up_date:
            self.follow_up_date = follow_up_date
        self.save(update_fields=["status", "waiting_on", "follow_up_date"])
