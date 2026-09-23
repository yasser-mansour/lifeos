from django.db import models

from apps.core.models import BaseModel, Tag
from apps.goals.models import Goal
from apps.people.models import Person
from apps.projects.models import Project
from apps.school.models import Course
from apps.tasks.models import Task


class Note(BaseModel):
    title = models.CharField(max_length=200, blank=True, default="")
    content = models.TextField(blank=True, default="")
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="linked_notes")
    task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL, related_name="linked_notes")
    person = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name="linked_notes")
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL, related_name="linked_notes")
    goal = models.ForeignKey(Goal, null=True, blank=True, on_delete=models.SET_NULL, related_name="linked_notes")
    tags = models.ManyToManyField(Tag, blank=True, related_name="notes")

    def __str__(self):
        return self.title or "Untitled note"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("notes:detail", args=[self.pk])

    @property
    def linked_to(self):
        for obj in [self.project, self.task, self.person, self.course, self.goal]:
            if obj is not None:
                return obj
        return None
