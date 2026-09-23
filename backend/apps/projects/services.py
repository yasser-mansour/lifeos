from decimal import Decimal

from django.utils import timezone


def projects_needing_attention(limit=6):
    """Active projects with an overdue task, or nothing touched in two
    weeks — the Home dashboard's "Projects requiring attention" section
    (spec §13/§20)."""
    from apps.projects.models import Project

    stale_cutoff = timezone.now() - timezone.timedelta(days=14)
    rows = []
    for project in Project.objects.filter(status="active").prefetch_related("tasks"):
        overdue_tasks = [t for t in project.tasks.all() if t.is_overdue]
        if overdue_tasks:
            rows.append({"name": project.name, "get_absolute_url": project.get_absolute_url(), "reason": f"{len(overdue_tasks)} overdue task{'s' if len(overdue_tasks) != 1 else ''}"})
        elif project.updated_at < stale_cutoff:
            rows.append({"name": project.name, "get_absolute_url": project.get_absolute_url(), "reason": "No activity in 2+ weeks"})
        if len(rows) >= limit:
            break
    return rows


def project_summary(project):
    """Everything the project detail page's Overview tab needs, aggregated
    live from related records — never stored as an authoritative field
    (see spec: "Do not store project profit as authoritative manually
    edited field")."""
    from apps.finance.models import Transaction
    from apps.study.services import project_focus_stats
    from apps.tasks.models import Task

    transactions = Transaction.objects.filter(project=project)
    revenue = sum((t.amount for t in transactions if t.type in ("income",)), Decimal("0.00"))
    expenses = sum((t.amount for t in transactions if t.type in ("expense",)), Decimal("0.00"))

    tasks = Task.objects.filter(project=project)
    open_tasks = tasks.exclude(status__in=["done", "cancelled"])

    focus = project_focus_stats(project)

    return {
        "revenue": revenue,
        "expenses": expenses,
        "profit": revenue - expenses,
        "focus_seconds": focus["total_seconds"],
        "focus_week_seconds": focus["week_seconds"],
        "open_tasks_count": open_tasks.count(),
        "tasks": tasks[:20],
        "transactions": transactions.order_by("-date")[:20],
        "sessions": focus["recent_sessions"],
        "upcoming_events": project.events.filter(start__gte=timezone.now())[:5],
    }
