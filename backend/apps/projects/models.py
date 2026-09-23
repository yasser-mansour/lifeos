from django.db import models

from apps.core.choices import PRIORITY_CHOICES
from apps.core.models import BaseModel
from apps.people.models import Organization, Person

AREA_CHOICES = [("business", "Business"), ("school", "School"), ("personal", "Personal")]
STATUS_CHOICES = [
    ("idea", "Idea"),
    ("planning", "Planning"),
    ("active", "Active"),
    ("paused", "Paused"),
    ("completed", "Completed"),
    ("archived", "Archived"),
]


class Project(BaseModel):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    area = models.CharField(max_length=10, choices=AREA_CHOICES, default="personal")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal")
    start_date = models.DateField(null=True, blank=True)
    target_date = models.DateField(null=True, blank=True)
    archived = models.BooleanField(default=False)
    people = models.ManyToManyField(Person, blank=True, related_name="projects")
    # Same shape as `people` (a bare M2M, no per-link role table) — a
    # project's relationship to Heroku is already fully described by
    # Heroku's own relationship_types ("Service Provider"), the same way a
    # linked Person's role comes from their own relationship_types rather
    # than a second field on this M2M. Consistent with the existing
    # convention rather than introducing a second, richer pattern just for
    # organizations (Finance V2 spec §12 permits this: "a richer relation
    # table" is offered, not required).
    organizations = models.ManyToManyField(Organization, blank=True, related_name="projects")

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("projects:detail", args=[self.pk])

    @property
    def clients(self):
        # Filtered in Python rather than via a JSONField __contains lookup —
        # SQLite's JSON1 containment semantics for list membership are not
        # reliable enough to depend on for something client-facing.
        return [p for p in self.people.all() if p.is_client]
