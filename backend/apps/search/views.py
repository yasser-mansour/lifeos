from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from apps.core.templatetags.icons import icon


def _icon(name):
    return str(icon(name))


@login_required
def search_api(request):
    query = request.GET.get("q", "").strip()
    groups = []

    if not query:
        groups.append({
            "label": "Quick actions",
            "items": [
                {"title": "Start Focus", "url": "/study/start/", "icon_svg": _icon("study")},
                {"title": "Add Transaction", "url": "/finance/transactions/new/", "icon_svg": _icon("finance")},
                {"title": "New Task", "url": "/tasks/?new=1", "icon_svg": _icon("tasks")},
                {"title": "New Journal Entry", "url": "/journal/new/", "icon_svg": _icon("journal")},
            ],
        })
        return JsonResponse({"groups": groups})

    from apps.calendar_app.models import Event
    from apps.finance.models import Account, Transaction
    from apps.goals.models import Goal
    from apps.journal.models import JournalEntry
    from apps.notes.models import Note
    from apps.people.models import Person
    from apps.projects.models import Project
    from apps.school.models import Course
    from apps.study.models import StudySession
    from apps.tasks.models import Task
    from apps.writing.models import Book

    def add_group(label, icon_name, items):
        if items:
            groups.append({"label": label, "items": [{**i, "icon_svg": _icon(icon_name)} for i in items]})

    add_group("Tasks", "tasks", [
        {"title": t.title, "url": t.get_absolute_url(), "hint": t.get_status_display()}
        for t in Task.objects.filter(title__icontains=query)[:5]
    ])
    add_group("Projects", "projects", [
        {"title": p.name, "url": p.get_absolute_url(), "hint": p.get_status_display()}
        for p in Project.objects.filter(name__icontains=query)[:5]
    ])
    add_group("People", "people", [
        {"title": p.name, "url": f"/people/{p.pk}/", "hint": p.organization}
        for p in Person.objects.filter(name__icontains=query)[:5]
    ])
    add_group("Courses", "study", [
        {"title": c.name, "url": c.get_absolute_url(), "hint": "Course"}
        for c in Course.objects.filter(name__icontains=query)[:5]
    ])
    add_group("Accounts", "finance", [
        {"title": a.name, "url": a.get_absolute_url(), "hint": a.get_context_display()}
        for a in Account.objects.filter(name__icontains=query)[:5]
    ])
    add_group("Transactions", "finance", [
        {"title": t.description or t.get_type_display(), "url": t.account.get_absolute_url(), "hint": str(t.date)}
        for t in Transaction.objects.filter(description__icontains=query)[:5]
    ])
    add_group("Journal", "journal", [
        {"title": j.title or f"Entry — {j.date}", "url": j.get_absolute_url(), "hint": str(j.date)}
        for j in JournalEntry.objects.filter(title__icontains=query)[:5]
    ])
    add_group("Notes", "notes", [
        {"title": n.title or "Untitled", "url": n.get_absolute_url()}
        for n in Note.objects.filter(title__icontains=query)[:5]
    ])
    add_group("Writing", "writing", [
        {"title": b.title, "url": b.get_absolute_url(), "hint": b.get_status_display()}
        for b in Book.objects.filter(title__icontains=query)[:5]
    ])
    add_group("Goals", "goals", [
        {"title": g.title, "url": "/goals/", "hint": g.get_goal_type_display()}
        for g in Goal.objects.filter(title__icontains=query)[:5]
    ])
    add_group("Calendar", "calendar", [
        {"title": e.title, "url": "/calendar/agenda/", "hint": str(e.start.date())}
        for e in Event.objects.filter(title__icontains=query)[:5]
    ])
    add_group("Study sessions", "study", [
        {"title": s.course.name if s.course else "Focus session", "url": s.get_absolute_url(), "hint": str(s.started_at.date())}
        for s in StudySession.objects.filter(course__name__icontains=query, status="completed")[:5]
    ])

    return JsonResponse({"groups": groups})
