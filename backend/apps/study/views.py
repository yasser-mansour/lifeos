from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.models import log_activity
from apps.devices.models import Device
from apps.study import services
from apps.study.forms import CorrectionForm, StartSessionForm, StudyGoalForm
from apps.study.models import DOMAIN_CHOICES, SCHOOL_DOMAINS, StudyGoal, StudySession

DOMAIN_LABELS = dict(DOMAIN_CHOICES)


def _desktop_device():
    device, _ = Device.objects.get_or_create(platform="macos", device_type="primary", defaults={"name": "This Mac", "status": "online"})
    return device


@login_required
def overview(request):
    active = services.active_session()
    if active:
        return redirect("focus:active")
    context = {
        "active_nav": "study",
        **services.today_summary(domains=SCHOOL_DOMAINS),
        "weekly_series": services.weekly_series(domains=SCHOOL_DOMAINS),
        "courses": _course_totals(),
    }
    return render(request, "study/overview.html", context)


def _course_totals():
    from apps.school.models import Course

    rows = []
    for course in Course.objects.filter(archived=False):
        stats = services.course_study_stats(course)
        if stats["total_seconds"] > 0:
            rows.append({"course": course, "total_seconds": stats["total_seconds"]})
    return sorted(rows, key=lambda r: -r["total_seconds"])[:8]


@login_required
def start(request):
    """One engine, two entry points (spec §12: "Use one engine, multiple
    filtered experiences. Do not duplicate timer code."):
    /study/start/?domain=school lands here with School preset — Study's
    "Start Study". /focus/start/ lands here with no domain — Focus's
    "Start Focus", which shows the domain picker first. Recently-used
    context (spec §7/§29) is surfaced via _recent_contexts()."""
    active = services.active_session()
    if active:
        return redirect("focus:active")

    domain = request.POST.get("domain") or request.GET.get("domain")
    active_nav = "study" if domain in SCHOOL_DOMAINS else "focus"

    if request.method == "POST":
        form = StartSessionForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            mode = data["mode"]
            planned = None
            pomodoro = None
            if mode == "countdown":
                planned = (data.get("countdown_minutes") or 25) * 60
            elif mode == "pomodoro":
                pomodoro = {
                    "focus_seconds": (data.get("pomodoro_focus_minutes") or 25) * 60,
                    "short_break_seconds": (data.get("pomodoro_short_break_minutes") or 5) * 60,
                    "long_break_seconds": (data.get("pomodoro_long_break_minutes") or 15) * 60,
                    "cycles_before_long_break": data.get("pomodoro_cycles") or 4,
                }
                planned = pomodoro["focus_seconds"]

            session = services.start_session(
                domain=data["domain"], course=data.get("course"), topic=data.get("topic"), task=data.get("task"),
                project=data.get("project"), book=data.get("book"),
                mode=mode, planned_duration_seconds=planned, device=_desktop_device(), pomodoro=pomodoro,
            )
            log_activity(f"Started {DOMAIN_LABELS.get(session.domain, 'focus').lower()} session{' — ' + session.course.name if session.course else ''}", category="study", obj=session)
            return redirect("focus:active")
    else:
        initial = {"domain": domain or "other"}
        for field in ("course", "topic", "task", "project", "book"):
            value = request.GET.get(field)
            if value:
                initial[field] = value
        form = StartSessionForm(initial=initial)

    context = {
        "active_nav": active_nav, "form": form, "domain": domain,
        "recent": _recent_contexts(domain) if domain else {},
    }
    return render(request, "study/start.html", context)


def _recent_contexts(domain, limit=5):
    """Recently-used entities for the chosen domain, most recent first —
    the "one tap" shortcut spec §7/§29 asks for instead of re-filling a form
    every time. Distinct on the entity, not the session, so a course you
    study daily shows once, not five times."""
    from apps.school.models import Course
    from apps.projects.models import Project

    if domain in SCHOOL_DOMAINS:
        recent_ids = list(
            StudySession.objects.filter(domain__in=SCHOOL_DOMAINS, course__isnull=False)
            .order_by("-started_at").values_list("course_id", flat=True).distinct()[:limit]
        )
        courses = Course.objects.filter(pk__in=recent_ids)
        return {"courses": sorted(courses, key=lambda c: recent_ids.index(c.pk))}
    if domain in ("project", "business"):
        recent_ids = list(
            StudySession.objects.filter(domain=domain, project__isnull=False)
            .order_by("-started_at").values_list("project_id", flat=True).distinct()[:limit]
        )
        projects = Project.objects.filter(pk__in=recent_ids)
        return {"projects": sorted(projects, key=lambda p: recent_ids.index(p.pk))}
    return {}


@login_required
def active(request):
    session = services.active_session()
    if not session:
        return redirect("focus:start")
    active_nav = "study" if session.domain in SCHOOL_DOMAINS else "focus"
    return render(request, "study/active.html", {"active_nav": active_nav, "session": session, "immersive": True})


@login_required
def active_status(request):
    session = services.active_session()
    if not session:
        return JsonResponse({"active": False})
    return JsonResponse({
        "active": True,
        "status": session.status,
        "duration_seconds": session.duration_seconds,
        "remaining_seconds": session.remaining_seconds,
        "current_phase": session.current_phase,
    })


@login_required
@require_POST
def action_pause(request):
    session = services.active_session()
    if session:
        services.pause_session(session, device=_desktop_device())
    return redirect("focus:active")


@login_required
@require_POST
def action_resume(request):
    session = services.active_session()
    if session:
        services.resume_session(session, device=_desktop_device())
    return redirect("focus:active")


def _home_for_domain(domain):
    return "study:overview" if domain in SCHOOL_DOMAINS else "focus:overview"


@login_required
@require_POST
def action_finish(request):
    session = services.active_session()
    if session:
        services.finish_session(session, device=_desktop_device())
        log_activity(f"Finished {session.duration_seconds // 60}m {DOMAIN_LABELS.get(session.domain, 'focus').lower()} session", category="study", obj=session)
        return redirect(_home_for_domain(session.domain))
    return redirect("focus:overview")


@login_required
@require_POST
def action_cancel(request):
    session = services.active_session()
    if session:
        services.cancel_session(session, device=_desktop_device())
        return redirect(_home_for_domain(session.domain))
    return redirect("focus:overview")


def _history(request, domains, active_nav, template):
    sessions = services.scope_by_domain(StudySession.objects.filter(status="completed"), domains).select_related("course", "topic", "project", "book", "origin_device")
    course_id = request.GET.get("course")
    if course_id:
        sessions = sessions.filter(course_id=course_id)

    grouped = {}
    for session in sessions:
        day = timezone.localtime(session.started_at).date()
        grouped.setdefault(day, []).append(session)

    context = {"active_nav": active_nav, "grouped": sorted(grouped.items(), key=lambda kv: kv[0], reverse=True)}
    return render(request, template, context)


@login_required
def history(request):
    return _history(request, SCHOOL_DOMAINS, "study", "study/history.html")


@login_required
def focus_history(request):
    return _history(request, None, "focus", "focus/history.html")


@login_required
def session_detail(request, pk):
    session = get_object_or_404(StudySession, pk=pk)
    if request.method == "POST":
        form = CorrectionForm(request.POST)
        if form.is_valid():
            seconds = (form.cleaned_data.get("corrected_hours") or 0) * 3600 + (form.cleaned_data.get("corrected_minutes") or 0) * 60
            services.correct_session(session, seconds, form.cleaned_data["reason"], device=_desktop_device())
            return redirect("focus:session_detail", pk=pk)
    active_nav = "study" if session.domain in SCHOOL_DOMAINS else "focus"
    context = {"active_nav": active_nav, "session": session, "events": session.events.all(), "correction_form": CorrectionForm()}
    return render(request, "study/session_detail.html", context)


@login_required
def statistics(request):
    days = services.heatmap_data()
    # Pad to a whole number of weeks (Mon-start) so the grid renders evenly.
    lead_padding = days[0]["date"].weekday()
    padded = [None] * lead_padding + days
    padded += [None] * (-len(padded) % 7)
    weeks = [padded[i : i + 7] for i in range(0, len(padded), 7)]
    # Transpose weeks-of-days into weekday-rows-of-weeks so the heatmap reads
    # left-to-right as time and top-to-bottom as Mon..Sun, GitHub-style.
    heatmap_rows = [[week[weekday] for week in weeks] for weekday in range(7)]
    context = {"active_nav": "study", "stats": services.full_statistics(), "heatmap_rows": heatmap_rows}
    return render(request, "study/statistics.html", context)


@login_required
def goals(request):
    if request.method == "POST":
        form = StudyGoalForm(request.POST)
        if form.is_valid():
            period = form.cleaned_data["period"]
            StudyGoal.objects.filter(period=period, active=True).update(active=False)
            StudyGoal.objects.create(period=period, target_seconds=int(form.cleaned_data["target_hours"] * 3600), active=True)
    context = {
        "active_nav": "study",
        "goal_forms": StudyGoalForm(),
        "goals": {p: services.active_goal(p) for p, _ in StudyGoal.PERIOD_CHOICES},
    }
    return render(request, "study/goals.html", context)


# ---------------- Focus (general, cross-domain) — spec §12: same engine,
# a differently-filtered experience. See _history/start above for the
# session-lifecycle views these share with Study. ----------------

@login_required
def focus_overview(request):
    active = services.active_session()
    if active:
        return redirect("focus:active")
    context = {
        "active_nav": "focus",
        "breakdown": services.focus_today_breakdown(),
        "recent": StudySession.objects.filter(status="completed").select_related("course", "project", "book").order_by("-started_at")[:5],
        "needs_classification_count": StudySession.objects.filter(status="completed", domain="other", course__isnull=True, project__isnull=True, book__isnull=True).count(),
    }
    return render(request, "focus/overview.html", context)


@login_required
def focus_statistics(request):
    days = services.heatmap_data(domains=None)
    lead_padding = days[0]["date"].weekday()
    padded = [None] * lead_padding + days
    padded += [None] * (-len(padded) % 7)
    weeks = [padded[i : i + 7] for i in range(0, len(padded), 7)]
    heatmap_rows = [[week[weekday] for week in weeks] for weekday in range(7)]
    context = {"active_nav": "focus", "stats": services.full_statistics(domains=None), "heatmap_rows": heatmap_rows}
    return render(request, "focus/statistics.html", context)


@login_required
def needs_classification(request):
    """spec §5/§22: legacy sessions the conservative migration couldn't
    place (no course/topic/project/book at all) wait here for a human
    decision rather than being guessed into a domain."""
    sessions = StudySession.objects.filter(
        status="completed", domain="other", course__isnull=True, project__isnull=True, book__isnull=True,
    ).order_by("-started_at")
    if request.method == "POST":
        session = get_object_or_404(StudySession, pk=request.POST.get("session_id"))
        new_domain = request.POST.get("domain")
        if new_domain in dict(DOMAIN_CHOICES):
            session.domain = new_domain
            session.save(update_fields=["domain"])
            log_activity(f"Classified a legacy focus session as {DOMAIN_LABELS.get(new_domain, new_domain)}", category="study", obj=session)
        return redirect("focus:needs_classification")
    return render(request, "focus/needs_classification.html", {"active_nav": "focus", "sessions": sessions, "domain_choices": DOMAIN_CHOICES})
