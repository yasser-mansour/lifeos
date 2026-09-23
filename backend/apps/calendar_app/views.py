import calendar as cal_module
from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.calendar_app.forms import EventForm
from apps.calendar_app.models import Event
from apps.core.models import log_activity


def _parse_ym(request):
    today = timezone.localdate()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))
    return year, month


@login_required
def month_view(request):
    year, month = _parse_ym(request)
    first_weekday, days_in_month = cal_module.monthrange(year, month)
    first_of_month = date(year, month, 1)
    grid_start = first_of_month - timedelta(days=first_weekday)

    events_by_day = {}
    for event in Event.objects.filter(start__date__gte=grid_start, start__date__lte=grid_start + timedelta(days=41)):
        events_by_day.setdefault(timezone.localtime(event.start).date(), []).append(event)

    weeks = []
    cursor = grid_start
    for _ in range(6):
        week = []
        for _ in range(7):
            week.append({"date": cursor, "in_month": cursor.month == month, "events": events_by_day.get(cursor, [])})
            cursor += timedelta(days=1)
        weeks.append(week)
        if cursor > first_of_month + timedelta(days=days_in_month) and cursor.weekday() == 0:
            break

    prev_month = (first_of_month - timedelta(days=1)).replace(day=1)
    next_month = (first_of_month + timedelta(days=days_in_month))

    context = {
        "active_nav": "calendar",
        "weeks": weeks,
        "month_label": first_of_month.strftime("%B %Y"),
        "prev_year": prev_month.year, "prev_month": prev_month.month,
        "next_year": next_month.year, "next_month": next_month.month,
        "today": timezone.localdate(),
    }
    return render(request, "calendar_app/month.html", context)


@login_required
def week_view(request):
    today = timezone.localdate()
    start = today - timedelta(days=today.weekday())
    days = []
    for i in range(7):
        d = start + timedelta(days=i)
        days.append({"date": d, "events": Event.objects.filter(start__date=d)})
    return render(request, "calendar_app/week.html", {"active_nav": "calendar", "days": days})


@login_required
def day_view(request):
    today = timezone.localdate()
    events = Event.objects.filter(start__date=today).order_by("start")
    return render(request, "calendar_app/day.html", {"active_nav": "calendar", "day": today, "events": events})


@login_required
def agenda_view(request):
    now = timezone.now()
    events = Event.objects.filter(start__gte=now).order_by("start")[:50]
    return render(request, "calendar_app/agenda.html", {"active_nav": "calendar", "events": events})


@login_required
def event_new(request):
    return _event_form(request, event=None)


@login_required
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk)
    return _event_form(request, event=event)


def _event_form(request, event):
    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            saved = form.save()
            verb = "Updated" if event else "Added"
            log_activity(f"{verb} event {saved.title}", category="calendar", obj=saved)
            return redirect("calendar_app:month")
    else:
        # Create-in-context: "Schedule" from a Project/Person/Course page
        # pre-selects that parent, same pattern as study.views.start.
        initial = {}
        if event is None:
            date_str = request.GET.get("date")
            if date_str:
                initial["start"] = datetime.fromisoformat(date_str)
            project_id = request.GET.get("project")
            person_id = request.GET.get("person")
            course_id = request.GET.get("course")
            if project_id:
                initial["project"] = project_id
            if person_id:
                initial["person"] = person_id
            if course_id:
                initial["course"] = course_id
        form = EventForm(instance=event, initial=initial)
    context = {
        "active_nav": "calendar", "form": form, "event": event,
        "prefill_context": bool(event is None and (request.GET.get("project") or request.GET.get("person") or request.GET.get("course"))),
    }
    return render(request, "calendar_app/event_new.html", context)


@login_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        event.soft_delete()
        log_activity(f"Removed event {event.title}", category="calendar")
    return redirect("calendar_app:month")
