from collections import defaultdict
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from apps.study.models import SCHOOL_DOMAINS, StudyGoal, StudySession, StudySessionEvent

# Project.area is already exactly business/school/personal (see
# apps.projects.models.AREA_CHOICES) — a session's domain inherits it
# directly, no separate mapping table to keep in sync.
PROJECT_AREA_TO_DOMAIN = {"business": "business", "school": "school", "personal": "personal"}


def domain_for_project(project):
    if project is None:
        return "other"
    return PROJECT_AREA_TO_DOMAIN.get(project.area, "other")


def scope_by_domain(qs, domains):
    """Every stats/query function takes an explicit `domains` filter rather
    than trusting a default, so School and Project/Business numbers can
    never silently bleed into each other (spec §9/§19 — "layered" but
    isolated statistics). `domains=None` means "all" (used by Focus, the
    cross-domain engine); Study always passes SCHOOL_DOMAINS explicitly."""
    if domains is None:
        return qs
    return qs.filter(domain__in=domains)


def start_session(*, domain="other", course=None, topic=None, task=None, project=None, book=None, mode="stopwatch", planned_duration_seconds=None, device=None, pomodoro=None, client_id=None):
    now = timezone.now()
    session = StudySession(
        domain=domain, course=course, topic=topic, task=task, project=project, book=book,
        mode=mode, status="active", started_at=now, origin_device=device,
        planned_duration_seconds=planned_duration_seconds,
    )
    if client_id:
        # Honor an offline-first client's own UUID (Android generates the id
        # before it ever reaches the network) so the row never needs an
        # after-the-fact id-reconciliation pass on the client — see
        # StudySessionViewSet._start_from_request. Collision with an existing
        # row is left to the database's own PK constraint: astronomically
        # unlikely for a properly-generated UUID, and a clear 500 beats
        # silent corruption if it ever somehow happened.
        session.id = client_id
    if mode == "pomodoro" and pomodoro:
        session.pomodoro_focus_seconds = pomodoro.get("focus_seconds", session.pomodoro_focus_seconds)
        session.pomodoro_short_break_seconds = pomodoro.get("short_break_seconds", session.pomodoro_short_break_seconds)
        session.pomodoro_long_break_seconds = pomodoro.get("long_break_seconds", session.pomodoro_long_break_seconds)
        session.pomodoro_cycles_before_long_break = pomodoro.get("cycles_before_long_break", session.pomodoro_cycles_before_long_break)
    session.save()
    StudySessionEvent.objects.create(session=session, event_type="start", timestamp=now, device=device)
    return session


def pause_session(session: StudySession, device=None, phase=None):
    now = timezone.now()
    session.status = "paused"
    if phase:
        session.current_phase = phase
    session.save(update_fields=["status", "current_phase"])
    StudySessionEvent.objects.create(session=session, event_type="pause", timestamp=now, device=device, metadata={"phase": phase} if phase else {})
    return session


def resume_session(session: StudySession, device=None, phase=None):
    now = timezone.now()
    session.status = "active"
    if phase:
        session.current_phase = phase
    session.save(update_fields=["status", "current_phase"])
    StudySessionEvent.objects.create(session=session, event_type="resume", timestamp=now, device=device, metadata={"phase": phase} if phase else {})
    return session


def finish_session(session: StudySession, device=None):
    now = timezone.now()
    session.status = "completed"
    session.ended_at = now
    session.ending_device = device
    session.save(update_fields=["status", "ended_at", "ending_device"])
    StudySessionEvent.objects.create(session=session, event_type="finish", timestamp=now, device=device)
    return session


def cancel_session(session: StudySession, device=None):
    now = timezone.now()
    session.status = "cancelled"
    session.ended_at = now
    session.ending_device = device
    session.save(update_fields=["status", "ended_at", "ending_device"])
    StudySessionEvent.objects.create(session=session, event_type="cancel", timestamp=now, device=device)
    return session


def correct_session(session: StudySession, corrected_seconds: int, reason: str, device=None):
    original_seconds = session.duration_seconds
    session.corrected_duration_seconds = corrected_seconds
    session.correction_reason = reason
    session.save(update_fields=["corrected_duration_seconds", "correction_reason"])
    StudySessionEvent.objects.create(
        session=session, event_type="correction", timestamp=timezone.now(), device=device,
        metadata={"original_seconds": original_seconds, "corrected_seconds": corrected_seconds, "reason": reason},
    )
    return session


def active_session():
    """The single in-progress session, if any — active or paused, on any
    device. Recovery (spec §58) and cross-device display (spec §79) both
    read this same source of truth rather than per-device local state."""
    return StudySession.objects.filter(status__in=["active", "paused"]).order_by("-started_at").first()


def study_day_seconds(date, domains=None):
    total = 0
    qs = scope_by_domain(StudySession.objects.filter(status="completed", started_at__date=date), domains)
    for session in qs:
        total += session.duration_seconds
    return total


def compute_streak(as_of=None, domains=None):
    as_of = as_of or timezone.localdate()
    completed_dates = set(
        scope_by_domain(StudySession.objects.filter(status="completed"), domains).values_list("started_at__date", flat=True).distinct()
    )
    if not completed_dates:
        return 0, 0

    current = 0
    cursor = as_of
    # A still-open "today" with zero sessions doesn't break a streak that
    # continues from yesterday — only count backward while days are present.
    if as_of not in completed_dates:
        cursor = as_of - timedelta(days=1)
    while cursor in completed_dates:
        current += 1
        cursor -= timedelta(days=1)

    longest = 0
    running = 0
    for d in sorted(completed_dates):
        if (d - timedelta(days=1)) in completed_dates:
            running += 1
        else:
            running = 1
        longest = max(longest, running)

    return current, longest


def active_goal(period):
    return StudyGoal.objects.filter(period=period, active=True).first()


def today_summary(domains=SCHOOL_DOMAINS):
    """Defaults to SCHOOL — this is what Study's overview and Home's Study
    mini-panel have always meant by "today." Pass domains=None for the
    cross-domain Focus equivalent."""
    today = timezone.localdate()
    sessions_today = scope_by_domain(StudySession.objects.filter(status="completed", started_at__date=today), domains).select_related("course", "topic")
    today_seconds = sum((s.duration_seconds for s in sessions_today), 0)
    current_streak, longest_streak = compute_streak(domains=domains)
    goal = active_goal("daily")
    return {
        "today_seconds": today_seconds,
        "sessions_today": sessions_today.order_by("-started_at"),
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "goal_seconds": goal.target_seconds if goal else None,
    }


def focus_today_breakdown():
    """Cross-domain "Total Focus today" plus its per-domain split — Home's
    Focus panel and the general Focus overview both read this. School's own
    number here must always equal today_summary(SCHOOL_DOMAINS)["today_seconds"]."""
    today = timezone.localdate()
    sessions_today = StudySession.objects.filter(status="completed", started_at__date=today)
    by_domain = defaultdict(int)
    for s in sessions_today:
        by_domain[s.domain] += s.duration_seconds
    return {
        "total_seconds": sum(by_domain.values()),
        "school_seconds": by_domain.get("school", 0),
        "project_seconds": by_domain.get("project", 0) + by_domain.get("business", 0),
        "writing_seconds": by_domain.get("writing", 0),
        "personal_seconds": by_domain.get("personal", 0),
        "other_seconds": by_domain.get("other", 0),
    }


def week_bounds(as_of=None):
    as_of = as_of or timezone.localdate()
    start = as_of - timedelta(days=as_of.weekday())
    return start, start + timedelta(days=6)


def weekly_series(as_of=None, domains=SCHOOL_DOMAINS):
    start, end = week_bounds(as_of)
    days = []
    cursor = start
    while cursor <= end:
        days.append({"date": cursor, "seconds": study_day_seconds(cursor, domains=domains)})
        cursor += timedelta(days=1)
    return days


def course_study_stats(course):
    # A course is inherently a SCHOOL relationship — the domain filter here
    # is defense-in-depth, not load-bearing, since only school sessions can
    # realistically carry a course under the classification rules.
    sessions = scope_by_domain(StudySession.objects.filter(course=course, status="completed"), SCHOOL_DOMAINS)
    total_seconds = sum((s.duration_seconds for s in sessions), 0)
    week_start, week_end = week_bounds()
    week_seconds = sum((s.duration_seconds for s in sessions.filter(started_at__date__gte=week_start, started_at__date__lte=week_end)), 0)
    return {"total_seconds": total_seconds, "week_seconds": week_seconds, "recent_sessions": sessions.order_by("-started_at")[:8]}


def project_focus_stats(project):
    """Mirror of course_study_stats for a Project's own Focus page (spec §20)."""
    sessions = StudySession.objects.filter(project=project, status="completed")
    total_seconds = sum((s.duration_seconds for s in sessions), 0)
    week_start, week_end = week_bounds()
    week_seconds = sum((s.duration_seconds for s in sessions.filter(started_at__date__gte=week_start, started_at__date__lte=week_end)), 0)
    return {"total_seconds": total_seconds, "week_seconds": week_seconds, "recent_sessions": sessions.order_by("-started_at")[:8]}


def heatmap_data(weeks=53, domains=SCHOOL_DOMAINS):
    today = timezone.localdate()
    start = today - timedelta(days=weeks * 7 - 1)
    totals = defaultdict(int)
    sessions = scope_by_domain(StudySession.objects.filter(status="completed", started_at__date__gte=start), domains)
    for s in sessions:
        totals[s.started_at.date()] += s.duration_seconds

    days = []
    cursor = start
    max_seconds = max(totals.values()) if totals else 0
    while cursor <= today:
        seconds = totals.get(cursor, 0)
        if seconds == 0:
            level = 0
        elif max_seconds <= 0:
            level = 0
        else:
            ratio = seconds / max_seconds
            level = 1 if ratio < 0.25 else 2 if ratio < 0.5 else 3 if ratio < 0.75 else 4
        days.append({"date": cursor, "seconds": seconds, "level": level})
        cursor += timedelta(days=1)
    return days


def _range_seconds(start_date, end_date, domains=None):
    sessions = scope_by_domain(StudySession.objects.filter(status="completed", started_at__date__gte=start_date, started_at__date__lte=end_date), domains)
    return sum((s.duration_seconds for s in sessions), 0)


def full_statistics(domains=SCHOOL_DOMAINS):
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    week_start, week_end = week_bounds(today)
    last_week_start, last_week_end = week_start - timedelta(days=7), week_start - timedelta(days=1)
    month_start = today.replace(day=1)
    last_month_end = month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    year_start = today.replace(month=1, day=1)

    all_sessions = scope_by_domain(StudySession.objects.all(), domains)
    completed = all_sessions.filter(status="completed")
    durations = [s.duration_seconds for s in completed]

    current_streak, longest_streak = compute_streak(domains=domains)
    study_days = set(completed.values_list("started_at__date", flat=True).distinct())

    weekday_totals = defaultdict(int)
    hour_totals = defaultdict(int)
    course_totals = defaultdict(int)
    mode_totals = defaultdict(int)
    device_totals = defaultdict(int)
    domain_totals = defaultdict(int)

    for s in completed.select_related("course", "origin_device"):
        weekday_totals[s.started_at.weekday()] += s.duration_seconds
        hour_totals[s.started_at.hour] += s.duration_seconds
        course_totals[s.course.name if s.course else "No course"] += s.duration_seconds
        mode_totals[s.get_mode_display()] += s.duration_seconds
        device_totals[s.origin_device.name if s.origin_device else "Unknown device"] += s.duration_seconds
        domain_totals[s.get_domain_display()] += s.duration_seconds

    return {
        "time": {
            "today": _range_seconds(today, today, domains=domains),
            "yesterday": _range_seconds(yesterday, yesterday, domains=domains),
            "this_week": _range_seconds(week_start, week_end, domains=domains),
            "last_week": _range_seconds(last_week_start, last_week_end, domains=domains),
            "this_month": _range_seconds(month_start, today, domains=domains),
            "last_month": _range_seconds(last_month_start, last_month_end, domains=domains),
            "this_year": _range_seconds(year_start, today, domains=domains),
            "all_time": sum(durations, 0),
        },
        "sessions": {
            "total": all_sessions.count(),
            "completed": completed.count(),
            "abandoned": all_sessions.filter(status="cancelled").count(),
            "interrupted": all_sessions.filter(status="paused").count(),
            "average": int(sum(durations) / len(durations)) if durations else 0,
            "median": sorted(durations)[len(durations) // 2] if durations else 0,
            "longest": max(durations) if durations else 0,
            "shortest": min(durations) if durations else 0,
        },
        "consistency": {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "study_days": len(study_days),
            "avg_seconds_per_study_day": int(sum(durations) / len(study_days)) if study_days else 0,
        },
        "distribution": {
            "course": dict(course_totals),
            "mode": dict(mode_totals),
            "device": dict(device_totals),
            "domain": dict(domain_totals),
        },
        "patterns": {
            "weekday": {
                name: weekday_totals.get(i, 0)
                for i, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
            },
            "hour": {h: hour_totals.get(h, 0) for h in range(24)},
        },
    }
