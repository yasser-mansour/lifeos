from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.calendar_app.models import Event
from apps.core.models import Profile
from apps.people.models import Person
from apps.projects.models import Project
from apps.school.models import Course


class CalendarViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_month_view_renders(self):
        response = self.client.get(reverse("calendar_app:month"))
        self.assertEqual(response.status_code, 200)

    def test_month_view_shows_todays_event(self):
        Event.objects.create(title="Team sync", start=timezone.now())
        response = self.client.get(reverse("calendar_app:month"))
        self.assertContains(response, "Team sync")

    def test_create_event(self):
        response = self.client.post(reverse("calendar_app:event_new"), {
            "title": "Exam prep", "start": "2026-09-01T09:00", "category": "study",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Event.objects.filter(title="Exam prep").exists())

    def test_agenda_empty_state(self):
        response = self.client.get(reverse("calendar_app:agenda"))
        self.assertContains(response, "Nothing upcoming")

    def test_new_event_from_project_page_prefills_project(self):
        """Regression: EventForm always had project/person/course fields,
        but the GET-initial handling only ever read `date` — a "Schedule"
        link from a Project/Person/Course page silently dropped the context."""
        project = Project.objects.create(name="Northstar")
        response = self.client.get(reverse("calendar_app:event_new"), {"project": project.pk})
        self.assertContains(response, f'<option value="{project.pk}" selected>')

    def test_new_event_from_person_page_prefills_person(self):
        person = Person.objects.create(name="Sara Bennani")
        response = self.client.get(reverse("calendar_app:event_new"), {"person": person.pk})
        self.assertContains(response, f'<option value="{person.pk}" selected>')

    def test_new_event_from_course_page_prefills_course(self):
        course = Course.objects.create(name="Algorithms")
        response = self.client.get(reverse("calendar_app:event_new"), {"course": course.pk})
        self.assertContains(response, f'<option value="{course.pk}" selected>')

    def test_month_grid_event_links_to_edit_not_create(self):
        """Regression: each day cell used to be a single <a> wrapping both
        the date number and every event chip inside it — clicking an
        existing event actually opened "New Event" for that day instead of
        editing the event, since nested <a> tags aren't valid HTML and the
        outer link always won."""
        event = Event.objects.create(title="Team sync", start=timezone.now())
        response = self.client.get(reverse("calendar_app:month"))
        self.assertContains(response, reverse("calendar_app:event_edit", args=[event.pk]))


class EventEditDeleteTests(TestCase):
    """Regression coverage: no event detail/edit view existed at all — once
    created, an event's Project/Person/Course link could never be viewed,
    changed, or removed from normal UI."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_edit_page_renders_with_current_values(self):
        event = Event.objects.create(title="Team sync", start=timezone.now())
        response = self.client.get(reverse("calendar_app:event_edit", args=[event.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Team sync")

    def test_edit_changes_project_link(self):
        project_a = Project.objects.create(name="Project A")
        project_b = Project.objects.create(name="Project B")
        event = Event.objects.create(title="Kickoff", start=timezone.now(), project=project_a)
        response = self.client.post(reverse("calendar_app:event_edit", args=[event.pk]), {
            "title": "Kickoff", "start": "2026-09-01T09:00", "category": "work", "project": project_b.pk,
        })
        self.assertRedirects(response, reverse("calendar_app:month"))
        event.refresh_from_db()
        self.assertEqual(event.project_id, project_b.pk)

    def test_edit_can_remove_project_link(self):
        project = Project.objects.create(name="Northstar")
        event = Event.objects.create(title="Kickoff", start=timezone.now(), project=project)
        self.client.post(reverse("calendar_app:event_edit", args=[event.pk]), {
            "title": "Kickoff", "start": "2026-09-01T09:00", "category": "work", "project": "",
        })
        event.refresh_from_db()
        self.assertIsNone(event.project)
        self.assertTrue(Project.objects.filter(pk=project.pk).exists())  # unlink, not delete

    def test_delete_event_soft_deletes(self):
        event = Event.objects.create(title="Gone Soon", start=timezone.now())
        response = self.client.post(reverse("calendar_app:event_delete", args=[event.pk]))
        self.assertRedirects(response, reverse("calendar_app:month"))
        self.assertFalse(Event.objects.filter(pk=event.pk).exists())
        self.assertTrue(Event.all_objects.filter(pk=event.pk).exists())


class EventEntryPointTests(TestCase):
    """The other side of each relationship: Project/Person/Course pages must
    show upcoming linked events and offer a real "Schedule" entry point."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_project_overview_shows_upcoming_event(self):
        project = Project.objects.create(name="Northstar")
        Event.objects.create(title="Client kickoff", start=timezone.now() + timezone.timedelta(days=1), project=project)
        response = self.client.get(reverse("projects:detail", args=[project.pk]))
        self.assertContains(response, "Client kickoff")

    def test_project_overview_hides_past_events(self):
        project = Project.objects.create(name="Northstar")
        Event.objects.create(title="Old meeting", start=timezone.now() - timezone.timedelta(days=30), project=project)
        response = self.client.get(reverse("projects:detail", args=[project.pk]))
        self.assertNotContains(response, "Old meeting")

    def test_person_panel_shows_upcoming_event(self):
        person = Person.objects.create(name="Sara Bennani")
        Event.objects.create(title="Follow-up call", start=timezone.now() + timezone.timedelta(days=1), person=person)
        response = self.client.get(reverse("people:detail", args=[person.pk]))
        self.assertContains(response, "Follow-up call")

    def test_course_detail_shows_upcoming_event(self):
        course = Course.objects.create(name="Algorithms")
        Event.objects.create(title="Guest lecture", start=timezone.now() + timezone.timedelta(days=1), course=course)
        response = self.client.get(course.get_absolute_url())
        self.assertContains(response, "Guest lecture")
