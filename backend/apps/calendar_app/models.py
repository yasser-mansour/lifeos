from django.db import models

from apps.core.models import BaseModel
from apps.people.models import Person
from apps.projects.models import Project
from apps.school.models import Course

CATEGORY_CHOICES = [("study", "Study"), ("work", "Work"), ("personal", "Personal"), ("other", "Other")]


class Event(BaseModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    all_day = models.BooleanField(default=False)
    location = models.CharField(max_length=200, blank=True, default="")
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default="other")
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="events")
    person = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name="events")
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL, related_name="events")
    reminder_minutes_before = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["start"]

    def __str__(self):
        return self.title
