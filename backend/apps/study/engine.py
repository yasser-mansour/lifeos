"""The event-sourced timer engine. This module has exactly one job: turn an
ordered list of (event_type, timestamp) pairs into a correct elapsed-focus
duration. It is pure and has no Django ORM dependency, which is what makes
it possible to unit-test every timing edge case (0-second sessions, repeated
pause/resume, an in-progress session, a session that outlived an app
restart) without touching the database — see docs/STUDY_ENGINE.md.

The critical design decision (spec §53/§54): duration is *derived* from
START/RESUME/PAUSE/FINISH/CANCEL timestamps, never from an incrementing
counter. A counter can drift or get lost across app backgrounding, process
death, or a device switch; a replay of timestamped events cannot.
"""

from datetime import timedelta

RUNNING_EVENTS = {"start", "resume"}
STOPPING_EVENTS = {"pause", "finish", "cancel"}


def compute_duration_seconds(events, as_of=None):
    """events: iterable of (event_type, timestamp) in chronological order.
    as_of: the "now" to use if the session is still running (no trailing
    stop event) — pass None for "use timezone.now()" at call time via the
    caller, or a fixed instant for deterministic tests."""
    if as_of is None:
        from django.utils import timezone

        as_of = timezone.now()

    total = timedelta()
    running_since = None

    for event_type, ts in events:
        if event_type in RUNNING_EVENTS:
            if running_since is None:
                running_since = ts
        elif event_type in STOPPING_EVENTS:
            if running_since is not None:
                total += ts - running_since
                running_since = None
        # "correction" events carry no timing weight of their own — they
        # only ever affect StudySession.corrected_duration_seconds.

    if running_since is not None:
        total += as_of - running_since

    return max(0, int(total.total_seconds()))


def is_currently_running(events):
    """True if the last RUNNING event has no subsequent STOPPING event —
    i.e. the session is actively accumulating focus time right now."""
    running = False
    for event_type, _ts in sorted(events, key=lambda e: e[1]):
        if event_type in RUNNING_EVENTS:
            running = True
        elif event_type in STOPPING_EVENTS:
            running = False
    return running
