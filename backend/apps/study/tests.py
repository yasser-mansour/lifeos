import uuid
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Profile
from apps.devices.models import Device
from apps.projects.models import Project
from apps.school.models import Course
from apps.study import services
from apps.study.engine import compute_duration_seconds, is_currently_running
from apps.study.models import StudySession

NOW = timezone.now()


def t(seconds_offset):
    return NOW + timedelta(seconds=seconds_offset)


class TimerEngineTests(TestCase):
    """Pure event-replay math — no database involved, exactly the kind of
    edge cases spec §126 asks for."""

    def test_zero_second_session(self):
        events = [("start", t(0)), ("finish", t(0))]
        self.assertEqual(compute_duration_seconds(events), 0)

    def test_one_second_session(self):
        events = [("start", t(0)), ("finish", t(1))]
        self.assertEqual(compute_duration_seconds(events), 1)

    def test_fifty_nine_seconds(self):
        events = [("start", t(0)), ("finish", t(59))]
        self.assertEqual(compute_duration_seconds(events), 59)

    def test_one_minute(self):
        events = [("start", t(0)), ("finish", t(60))]
        self.assertEqual(compute_duration_seconds(events), 60)

    def test_fifty_nine_minutes(self):
        events = [("start", t(0)), ("finish", t(59 * 60))]
        self.assertEqual(compute_duration_seconds(events), 59 * 60)

    def test_one_hour(self):
        events = [("start", t(0)), ("finish", t(3600))]
        self.assertEqual(compute_duration_seconds(events), 3600)

    def test_three_hours(self):
        events = [("start", t(0)), ("finish", t(3 * 3600))]
        self.assertEqual(compute_duration_seconds(events), 3 * 3600)

    def test_six_hours(self):
        events = [("start", t(0)), ("finish", t(6 * 3600))]
        self.assertEqual(compute_duration_seconds(events), 6 * 3600)

    def test_very_long_session(self):
        events = [("start", t(0)), ("finish", t(20 * 3600))]
        self.assertEqual(compute_duration_seconds(events), 20 * 3600)

    def test_single_pause_excludes_paused_time(self):
        events = [("start", t(0)), ("pause", t(60)), ("resume", t(600)), ("finish", t(660))]
        # 0-60 (60s active) + 600-660 (60s active) = 120s; the 540s pause gap is excluded.
        self.assertEqual(compute_duration_seconds(events), 120)

    def test_multiple_pauses(self):
        events = [
            ("start", t(0)), ("pause", t(100)),
            ("resume", t(200)), ("pause", t(250)),
            ("resume", t(300)), ("finish", t(320)),
        ]
        # active: 0-100 (100) + 200-250 (50) + 300-320 (20) = 170
        self.assertEqual(compute_duration_seconds(events), 170)

    def test_in_progress_session_counts_up_to_as_of(self):
        events = [("start", t(0))]
        self.assertEqual(compute_duration_seconds(events, as_of=t(45)), 45)

    def test_paused_session_freezes_at_pause_point(self):
        events = [("start", t(0)), ("pause", t(30))]
        # as_of far in the future must not add any time — it's paused.
        self.assertEqual(compute_duration_seconds(events, as_of=t(9999)), 30)

    def test_cancelled_session_stops_accumulating(self):
        events = [("start", t(0)), ("cancel", t(15))]
        self.assertEqual(compute_duration_seconds(events, as_of=t(500)), 15)

    def test_is_currently_running(self):
        self.assertTrue(is_currently_running([("start", t(0))]))
        self.assertFalse(is_currently_running([("start", t(0)), ("pause", t(10))]))
        self.assertTrue(is_currently_running([("start", t(0)), ("pause", t(10)), ("resume", t(20))]))
        self.assertFalse(is_currently_running([("start", t(0)), ("finish", t(10))]))


class SessionLifecycleTests(TestCase):
    def test_start_creates_active_session_with_start_event(self):
        session = services.start_session(mode="stopwatch")
        self.assertEqual(session.status, "active")
        self.assertEqual(session.events.count(), 1)
        self.assertEqual(session.events.first().event_type, "start")

    def test_pause_then_resume_round_trip(self):
        session = services.start_session(mode="stopwatch")
        services.pause_session(session)
        session.refresh_from_db()
        self.assertEqual(session.status, "paused")
        services.resume_session(session)
        session.refresh_from_db()
        self.assertEqual(session.status, "active")
        self.assertEqual(list(session.events.values_list("event_type", flat=True)), ["start", "pause", "resume"])

    def test_finish_sets_completed_and_ended_at(self):
        session = services.start_session(mode="stopwatch")
        services.finish_session(session)
        session.refresh_from_db()
        self.assertEqual(session.status, "completed")
        self.assertIsNotNone(session.ended_at)

    def test_client_id_is_honored_so_offline_clients_never_need_id_reconciliation(self):
        """Android generates the session id locally, before the device is
        ever online, then pushes 'start' followed by pause/finish/etc against
        that same id. If the server minted its own id instead, every
        follow-up action would 404. See StudySessionViewSet._start_from_request."""
        client_id = uuid.uuid4()
        session = services.start_session(mode="stopwatch", client_id=client_id)
        self.assertEqual(session.id, client_id)

    def test_missing_client_id_still_autogenerates_normally(self):
        session = services.start_session(mode="stopwatch")
        self.assertIsNotNone(session.id)

    def test_countdown_reaching_zero_and_continuing(self):
        session = services.start_session(mode="countdown", planned_duration_seconds=1)
        session.events.filter(event_type="start").update(timestamp=t(-2))
        session.refresh_from_db()
        self.assertEqual(session.remaining_seconds, 0)  # clamped, never negative
        # session is still open — "continue" just means not calling finish yet.
        self.assertEqual(session.status, "active")

    def test_abandoned_session_is_cancelled_not_deleted(self):
        session = services.start_session(mode="stopwatch")
        services.cancel_session(session)
        self.assertTrue(StudySession.objects.filter(pk=session.pk, status="cancelled").exists())

    def test_active_session_recovery_returns_the_open_session(self):
        session = services.start_session(mode="stopwatch")
        found = services.active_session()
        self.assertEqual(found.pk, session.pk)

    def test_no_active_session_when_all_finished(self):
        session = services.start_session(mode="stopwatch")
        services.finish_session(session)
        self.assertIsNone(services.active_session())

    def test_multiple_devices_recorded_on_session(self):
        mac = Device.objects.create(name="MacBook", platform="macos")
        phone = Device.objects.create(name="Galaxy A25", platform="android")
        session = services.start_session(mode="stopwatch", device=mac)
        services.pause_session(session, device=phone)
        self.assertEqual(session.origin_device_id, mac.pk)
        self.assertEqual(session.events.last().device_id, phone.pk)

    def test_correction_preserves_original_history(self):
        session = services.start_session(mode="stopwatch")
        session.events.filter(event_type="start").update(timestamp=t(-8100))  # 2h15m ago
        services.finish_session(session)
        session.refresh_from_db()
        original = session.duration_seconds
        services.correct_session(session, corrected_seconds=7500, reason="Timer left running")  # 2h05m
        session.refresh_from_db()
        self.assertEqual(session.duration_seconds, 7500)
        correction_event = session.events.filter(event_type="correction").first()
        self.assertEqual(correction_event.metadata["original_seconds"], original)
        self.assertEqual(correction_event.metadata["corrected_seconds"], 7500)
        # Original start/finish events are still there, untouched:
        self.assertTrue(session.events.filter(event_type="start").exists())
        self.assertTrue(session.events.filter(event_type="finish").exists())


class StreakTests(TestCase):
    def _completed_session_on(self, date):
        session = StudySession.objects.create(mode="stopwatch", status="completed", started_at=timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.min.time()) + timedelta(hours=10)))
        session.corrected_duration_seconds = 1800
        session.save()
        return session

    def test_no_sessions_means_zero_streak(self):
        current, longest = services.compute_streak()
        self.assertEqual((current, longest), (0, 0))

    def test_consecutive_days_build_a_streak(self):
        today = timezone.localdate()
        for offset in range(3):
            self._completed_session_on(today - timedelta(days=offset))
        current, longest = services.compute_streak(as_of=today)
        self.assertEqual(current, 3)
        self.assertEqual(longest, 3)

    def test_gap_breaks_streak(self):
        today = timezone.localdate()
        self._completed_session_on(today)
        self._completed_session_on(today - timedelta(days=1))
        self._completed_session_on(today - timedelta(days=5))  # gap
        current, _ = services.compute_streak(as_of=today)
        self.assertEqual(current, 2)

    def test_streak_survives_a_still_open_today_with_no_session_yet(self):
        today = timezone.localdate()
        self._completed_session_on(today - timedelta(days=1))
        self._completed_session_on(today - timedelta(days=2))
        current, _ = services.compute_streak(as_of=today)
        self.assertEqual(current, 2)


class StudyStatisticsTests(TestCase):
    def test_statistics_across_empty_data_does_not_crash(self):
        stats = services.full_statistics()
        self.assertEqual(stats["sessions"]["total"], 0)
        self.assertEqual(stats["time"]["today"], 0)

    def test_statistics_aggregate_across_days(self):
        course = Course.objects.create(name="Mathematics")
        today = timezone.now()
        s1 = StudySession.objects.create(domain="school", mode="stopwatch", status="completed", course=course, started_at=today, corrected_duration_seconds=3600)
        s2 = StudySession.objects.create(domain="school", mode="pomodoro", status="completed", course=course, started_at=today - timedelta(days=1), corrected_duration_seconds=1800)
        stats = services.full_statistics()
        self.assertEqual(stats["sessions"]["completed"], 2)
        self.assertEqual(stats["time"]["today"], s1.duration_seconds)
        self.assertIn("Mathematics", stats["distribution"]["course"])


class StudyViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_overview_empty_state(self):
        response = self.client.get(reverse("study:overview"))
        self.assertContains(response, "No study sessions yet")

    def test_start_session_via_form_then_active_page(self):
        response = self.client.post(reverse("study:start"), {"domain": "school", "mode": "stopwatch"})
        self.assertRedirects(response, reverse("focus:active"))
        self.assertTrue(StudySession.objects.filter(status="active").exists())

    def test_overview_redirects_to_active_when_session_running(self):
        services.start_session(mode="stopwatch")
        response = self.client.get(reverse("study:overview"))
        self.assertRedirects(response, reverse("focus:active"))

    def test_pause_and_finish_flow(self):
        session = services.start_session(mode="stopwatch")
        self.client.post(reverse("study:action_pause"))
        session.refresh_from_db()
        self.assertEqual(session.status, "paused")
        self.client.post(reverse("study:action_finish"))
        session.refresh_from_db()
        self.assertEqual(session.status, "completed")

    def test_active_status_endpoint(self):
        services.start_session(mode="stopwatch")
        response = self.client.get(reverse("study:active_status"))
        data = response.json()
        self.assertTrue(data["active"])
        self.assertIn("duration_seconds", data)


class DomainIsolationTests(TestCase):
    """The entire point of the Focus/Study rearchitecture: a business or
    project session must never count toward School statistics, and vice
    versa. This is spec workflow C's explicit acceptance test — verified
    here at the service layer, not just eyeballed in the UI."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")
        self.course = Course.objects.create(name="Mathematics")
        self.project = Project.objects.create(name="Northstar", area="business")
        self.school_session = StudySession.objects.create(
            domain="school", course=self.course, mode="stopwatch", status="completed",
            started_at=timezone.now(), corrected_duration_seconds=3600,
        )
        self.business_session = StudySession.objects.create(
            domain="business", project=self.project, mode="stopwatch", status="completed",
            started_at=timezone.now(), corrected_duration_seconds=1800,
        )

    def test_school_today_summary_excludes_business_session(self):
        summary = services.today_summary(domains=["school"])
        self.assertEqual(summary["today_seconds"], 3600)  # only the Mathematics session

    def test_business_project_focus_stats_excludes_school_session(self):
        stats = services.project_focus_stats(self.project)
        self.assertEqual(stats["total_seconds"], 1800)  # only the Northstar session

    def test_course_study_stats_excludes_business_session(self):
        stats = services.course_study_stats(self.course)
        self.assertEqual(stats["total_seconds"], 3600)

    def test_focus_today_breakdown_separates_school_from_business(self):
        breakdown = services.focus_today_breakdown()
        self.assertEqual(breakdown["school_seconds"], 3600)
        self.assertEqual(breakdown["project_seconds"], 1800)  # business folds into "project" for Home's display
        self.assertEqual(breakdown["total_seconds"], 5400)

    def test_full_statistics_school_default_excludes_business(self):
        stats = services.full_statistics()  # default domains=SCHOOL_DOMAINS
        self.assertEqual(stats["time"]["today"], 3600)
        self.assertEqual(stats["sessions"]["completed"], 1)

    def test_full_statistics_cross_domain_includes_both(self):
        stats = services.full_statistics(domains=None)
        self.assertEqual(stats["time"]["today"], 5400)
        self.assertEqual(stats["sessions"]["completed"], 2)

    def test_study_history_page_excludes_business_session(self):
        response = self.client.get(reverse("study:history"))
        self.assertNotContains(response, "Northstar")
        self.assertContains(response, "Mathematics")

    def test_focus_history_page_includes_both(self):
        response = self.client.get(reverse("focus:history"))
        self.assertContains(response, "Northstar")
        self.assertContains(response, "Mathematics")

    def test_legacy_session_classification_migration_logic(self):
        """Exercises the same deterministic rule the data migration uses,
        at the unit level (course/topic -> school; project -> project.area;
        neither -> other, never guessed)."""
        from apps.study.services import domain_for_project

        self.assertEqual(domain_for_project(self.project), "business")
        personal_project = Project.objects.create(name="LifeOS", area="personal")
        self.assertEqual(domain_for_project(personal_project), "personal")
        self.assertEqual(domain_for_project(None), "other")


class PomodoroPhaseApiTests(TestCase):
    """A Pomodoro client (Android or desktop) pauses to end one phase and
    resumes to start the next — the API action must actually forward that
    phase to the service, or current_phase never reflects it server-side
    even though StudySessionSerializer exposes the field (see apps.study.api)."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")
        self.session = services.start_session(mode="pomodoro")

    def test_pause_with_phase_updates_current_phase(self):
        response = self.client.post(f"/api/study-sessions/{self.session.id}/pause/", {"phase": "short_break"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current_phase"], "short_break")
        self.session.refresh_from_db()
        self.assertEqual(self.session.current_phase, "short_break")

    def test_resume_with_phase_updates_current_phase(self):
        self.client.post(f"/api/study-sessions/{self.session.id}/pause/", {"phase": "short_break"})
        response = self.client.post(f"/api/study-sessions/{self.session.id}/resume/", {"phase": "focus"})
        self.assertEqual(response.json()["current_phase"], "focus")

    def test_pause_without_phase_leaves_current_phase_untouched(self):
        response = self.client.post(f"/api/study-sessions/{self.session.id}/pause/")
        self.assertEqual(response.json()["current_phase"], "focus")
