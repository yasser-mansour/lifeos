from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel
from apps.projects.models import Project
from apps.school.models import Course

GOAL_TYPE_CHOICES = [
    ("personal", "Personal"),
    ("academic", "Academic"),
    ("financial", "Financial"),
    ("business", "Business"),
    ("project", "Project"),
    ("other", "Other"),
]
STATUS_CHOICES = [("active", "Active"), ("completed", "Completed"), ("abandoned", "Abandoned")]


class Goal(BaseModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    goal_type = models.CharField(max_length=10, choices=GOAL_TYPE_CHOICES, default="personal")
    target_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    current_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    unit = models.CharField(max_length=30, blank=True, default="")
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="goals")
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL, related_name="goals")
    derive_from_study_hours = models.BooleanField(default=False, help_text="Auto-compute progress from Study sessions since this goal was created.")

    class Meta:
        ordering = ["deadline", "-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("goals:detail", args=[self.pk])

    @property
    def effective_current_value(self) -> Decimal:
        if self.derive_from_study_hours:
            from apps.study.models import StudySession

            sessions = StudySession.objects.filter(status="completed", started_at__gte=self.created_at)
            if self.course:
                sessions = sessions.filter(course=self.course)
            total_hours = sum((s.duration_seconds for s in sessions), 0) / 3600
            return Decimal(str(round(total_hours, 1)))
        return self.current_value

    @property
    def progress_percent(self):
        if not self.target_value:
            return None
        return int(min(100, max(0, (self.effective_current_value / self.target_value) * 100)))

    @property
    def is_overdue(self):
        return bool(self.deadline and self.deadline < timezone.localdate() and self.status == "active")
