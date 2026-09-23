import uuid

from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel
from apps.devices.models import Device
from apps.projects.models import Project
from apps.school.models import Course, Topic
from apps.tasks.models import Task

DOMAIN_CHOICES = [
    ("school", "School"),
    ("project", "Project"),
    ("business", "Business"),
    ("personal", "Personal"),
    ("writing", "Writing"),
    ("other", "Other"),
]
SCHOOL_DOMAINS = ["school"]

MODE_CHOICES = [("stopwatch", "Stopwatch"), ("countdown", "Countdown"), ("pomodoro", "Pomodoro")]
STATUS_CHOICES = [("active", "Active"), ("paused", "Paused"), ("completed", "Completed"), ("cancelled", "Cancelled")]
EVENT_TYPE_CHOICES = [
    ("start", "Start"),
    ("pause", "Pause"),
    ("resume", "Resume"),
    ("finish", "Finish"),
    ("cancel", "Cancel"),
    ("correction", "Correction"),
]
PHASE_CHOICES = [("focus", "Focus"), ("short_break", "Short Break"), ("long_break", "Long Break")]


class StudySession(BaseModel):
    """A "Focus Session" in product terms — one general timer engine. The
    `domain` decides which higher-level experience (Focus vs. Study) and
    which statistics a session counts toward; see docs/STUDY_ENGINE.md
    "Focus Engine" and spec §6-10. School stats must never include
    project/business work and vice versa — every stats query in
    services.py filters by domain rather than trusting the caller."""

    domain = models.CharField(max_length=10, choices=DOMAIN_CHOICES, default="other", db_index=True)

    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL, related_name="study_sessions")
    topic = models.ForeignKey(Topic, null=True, blank=True, on_delete=models.SET_NULL, related_name="study_sessions")
    task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL, related_name="study_sessions")
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="study_sessions")
    book = models.ForeignKey("writing.Book", null=True, blank=True, on_delete=models.SET_NULL, related_name="focus_sessions")

    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default="stopwatch")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active", db_index=True)

    planned_duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    # Pomodoro configuration (only meaningful when mode == "pomodoro")
    pomodoro_focus_seconds = models.PositiveIntegerField(default=25 * 60)
    pomodoro_short_break_seconds = models.PositiveIntegerField(default=5 * 60)
    pomodoro_long_break_seconds = models.PositiveIntegerField(default=15 * 60)
    pomodoro_cycles_before_long_break = models.PositiveIntegerField(default=4)
    current_phase = models.CharField(max_length=15, choices=PHASE_CHOICES, default="focus")
    completed_focus_cycles = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)

    origin_device = models.ForeignKey(Device, null=True, blank=True, on_delete=models.SET_NULL, related_name="originated_sessions")
    ending_device = models.ForeignKey(Device, null=True, blank=True, on_delete=models.SET_NULL, related_name="ended_sessions")

    # Corrections preserve history rather than rewriting it — see
    # docs/STUDY_ENGINE.md "Corrections" and spec §55.
    corrected_duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    correction_reason = models.CharField(max_length=255, blank=True, default="")

    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.focus_title} ({self.started_at:%Y-%m-%d %H:%M})"

    def get_absolute_url(self):
        from django.urls import reverse

        namespace = "study" if self.domain in SCHOOL_DOMAINS else "focus"
        return reverse(f"{namespace}:session_detail", args=[self.pk])

    @property
    def focus_title(self) -> str:
        """The Level-1 label for this session — what it's actually of,
        regardless of domain. Used everywhere a session is listed: active
        mode, history rows, recent-context shortcuts."""
        if self.course:
            return self.course.name
        if self.project:
            return self.project.name
        if self.book:
            return self.book.title
        return self.get_domain_display()

    @property
    def focus_subtitle(self) -> str:
        """The Level-2 line — domain plus whatever narrows it further."""
        domain_label = self.get_domain_display()
        detail = self.topic.name if self.topic else (self.task.title if self.task else None)
        return f"{domain_label} · {detail}" if detail else domain_label

    @property
    def duration_seconds(self) -> int:
        from apps.study.engine import compute_duration_seconds

        if self.corrected_duration_seconds is not None:
            return self.corrected_duration_seconds
        events = [(e.event_type, e.timestamp) for e in self.events.all().order_by("timestamp")]
        as_of = self.ended_at if self.status in ("completed", "cancelled") else None
        return compute_duration_seconds(events, as_of=as_of)

    @property
    def is_active_or_paused(self):
        return self.status in ("active", "paused")

    @property
    def remaining_seconds(self):
        if not self.planned_duration_seconds:
            return None
        return max(0, self.planned_duration_seconds - self.duration_seconds)


class StudySessionEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(StudySession, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=12, choices=EVENT_TYPE_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)
    device = models.ForeignKey(Device, null=True, blank=True, on_delete=models.SET_NULL)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.session_id} {self.event_type} @ {self.timestamp}"


class StudyGoal(BaseModel):
    PERIOD_CHOICES = [("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")]

    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    target_seconds = models.PositiveIntegerField()
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_period_display()} goal: {self.target_seconds}s"
