# Study Engine

## The core decision: events, not counters

A study session's duration is never stored as a number that gets incremented. It's computed by replaying an ordered list of `StudySessionEvent` rows (`start` / `pause` / `resume` / `finish` / `cancel` / `correction`) through a pure function:

- Backend: `apps/study/engine.py::compute_duration_seconds(events, as_of)`
- Android: `study/StudyTimerEngine.kt::computeDurationSeconds(events, asOfEpochMs)`

The algorithm (identical on both sides): walk the events in timestamp order, tracking a `running_since` timestamp. `start`/`resume` set it if unset; `pause`/`finish`/`cancel` add `(event.timestamp - running_since)` to the total and clear it. If the walk ends with `running_since` still set (the session is still open), add `(as_of - running_since)` — this is the only place "now" enters the calculation, and it's passed in as a parameter rather than read internally, which is what makes the function trivially unit-testable with fixed timestamps.

This is why the timer survives a backgrounded app, a locked screen, a killed process, or a Mac that was asleep for the entire session: none of those states affect the event log, so replaying it afterward gives the same correct answer as replaying it live would have.

## Session lifecycle

`apps/study/services.py` (backend) and `data/repository/StudyRepository.kt` (Android) both expose the same five operations, each of which does exactly one thing — append one event, then update `status`:

`start_session` → `pause_session` → `resume_session` → (repeat) → `finish_session` (or `cancel_session`).

On Android, every one of these is **local-first**: they write to Room immediately and return, with no network round-trip required. `SyncWorker` pushes the resulting events to the backend later, whenever connectivity to the paired Mac exists. This is what makes "start a session, keep studying with the Mac off" work (spec §74).

## Pomodoro

Break transitions reuse the same `pause`/`resume` event types (with `metadata: {"phase": "short_break"}` etc. on the backend) rather than inventing a parallel state machine — a break *is*, mechanically, a pause: focus time stops accumulating, and resuming focus is mechanically identical to resuming from any other pause. `StudySession.current_phase` tracks which phase is active for display purposes.

## Corrections preserve history

`correct_session(session, corrected_seconds, reason)` does not rewrite or delete any existing event. It sets `StudySession.corrected_duration_seconds` (which, when present, `duration_seconds` returns directly instead of computing from events) and appends a `correction` event whose `metadata` records `{original_seconds, corrected_seconds, reason}`. The original `start`/`pause`/`resume`/`finish` events are still there, still inspectable — a correction is additive, not destructive (spec §55).

## Streaks

A study day counts if at least one `completed` session exists with `started_at` on that local date — deliberately simple (spec §65's own stated default rule), not gated on a minimum duration. `apps/study/services.py::compute_streak()` walks backward from today; if today has no completed session yet, it starts counting from yesterday instead of breaking the streak at zero (a still-open "today" shouldn't erase yesterday's momentum). Longest streak is computed by scanning all distinct completed-session dates for the longest run of consecutive days.

## Statistics

`apps/study/services.py::full_statistics()` computes, from real session data only (no hardcoded numbers): time totals across seven ranges (today/yesterday/this+last week/this+last month/this year/all time), session counts and abandonment/interruption counts, average/median/longest/shortest duration, current/longest streak and average time per study day, distribution by course/mode/device, and time-of-day/weekday patterns. The heatmap (`heatmap_data()`) buckets daily totals into five intensity levels relative to the maximum day in the window, GitHub-contribution-graph style; the desktop view transposes the resulting weeks-of-days list into weekday-rows-of-weeks so it reads left-to-right as time.

## Device tracking and cross-device sessions

Every `StudySession` records `origin_device` and `ending_device`; every `StudySessionEvent` records which device produced it. `apps/study/services.py::active_session()` is the single source of truth for "is there a session in progress" — it doesn't care which device asked, so a session started on Android and later opened on the Mac (once synced) is the same row, not a duplicate (spec §79). `SyncWorker`'s conflict rule (see `docs/SYNC.md`) is "a session with local unsynced edits wins over an incoming pull" — so a pause tapped on the phone a second before a periodic sync can't be silently overwritten by a stale server read.

## Test coverage

`apps/study/tests.py` (35 tests) and `StudyTimerEngineTest.kt` (10 tests) both cover: 0-second/1-second/59-second/1-minute/1-hour/multi-hour sessions, single and multiple pauses, an in-progress session's duration continuing to grow, a paused session's duration freezing regardless of how much later it's queried, cancelled sessions, streak continuity and gaps, and (backend only, since it needs the full Django app stack) statistics aggregation, goal tracking, and the HTTP-level start/pause/finish/cancel flow.
