PRIORITY_RANK = {"urgent": 3, "high": 2, "normal": 1, "low": 0}


def next_tasks(limit=None):
    """Home's "Next Tasks" ordering (spec §66/§67) — three groups, each
    internally sorted by priority (urgent first) then a tie-breaker:

      A. Overdue (has a due_date in the past)  — due_date ascending, then created_at ascending
      B. Due today or later (has a future/today due_date) — due_date ascending, then created_at ascending
      C. No due date — created_at ascending

    Groups run A, B, C in that order — every dated task (overdue or not)
    outranks every undated one. Within a group, priority always wins first;
    the date/created_at fields only break ties between same-priority tasks.
    Done/cancelled tasks are excluded entirely."""
    from django.db.models import Case, IntegerField, When
    from django.utils import timezone

    from apps.tasks.models import OPEN_STATUSES, Task

    today = timezone.localdate()

    open_tasks = (
        Task.objects.filter(status__in=OPEN_STATUSES)
        .select_related("project", "course")
        .annotate(
            priority_rank=Case(
                *[When(priority=key, then=rank) for key, rank in PRIORITY_RANK.items()],
                default=PRIORITY_RANK["normal"],
                output_field=IntegerField(),
            )
        )
    )

    overdue = list(open_tasks.filter(due_date__lt=today).order_by("-priority_rank", "due_date", "created_at"))
    upcoming = list(open_tasks.filter(due_date__gte=today).order_by("-priority_rank", "due_date", "created_at"))
    undated = list(open_tasks.filter(due_date__isnull=True).order_by("-priority_rank", "created_at"))

    ordered = overdue + upcoming + undated
    return ordered[:limit] if limit else ordered


def task_focus_summary(task):
    from apps.study.models import StudySession

    sessions = StudySession.objects.filter(task=task, status="completed")
    total_seconds = sum((s.duration_seconds for s in sessions), 0)
    return {"sessions": sessions.order_by("-started_at"), "total_seconds": total_seconds, "session_count": sessions.count()}
