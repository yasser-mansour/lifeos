from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from apps.calendar_app.services import today_agenda
from apps.core.models import ActivityEvent
from apps.finance.services import finance_overview
from apps.projects.services import projects_needing_attention
from apps.study.services import today_summary
from apps.tasks.models import Task
from apps.tasks.services import next_tasks


@login_required
def home(request):
    now = timezone.localtime()
    hour = now.hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    study = today_summary()
    personal = finance_overview(context="personal")
    business = finance_overview(context="business")

    waiting_tasks = Task.objects.filter(status="waiting").select_related("waiting_for_person")
    waiting_items = [
        {"title": t.title, "waiting_on": t.waiting_on or (t.waiting_for_person.name if t.waiting_for_person else "someone"), "is_overdue": t.is_waiting_overdue}
        for t in waiting_tasks
    ]

    context = {
        "active_nav": "home",
        "greeting": greeting,
        "today": now,
        "today_items": today_agenda(),
        "study_today_seconds": study["today_seconds"],
        "study_goal_seconds": study["goal_seconds"],
        "study_streak": study["current_streak"],
        "finance_total": personal["total_balance"] + business["total_balance"],
        "finance_personal_total": personal["total_balance"],
        "finance_business_total": business["total_balance"],
        "finance_has_accounts": bool(personal["accounts"] or business["accounts"]),
        "next_tasks": next_tasks(limit=5),
        "projects_attention": projects_needing_attention(),
        "waiting_items": waiting_items,
        "recent_activity": ActivityEvent.objects.all()[:8],
    }
    return render(request, "dashboard/home.html", context)
