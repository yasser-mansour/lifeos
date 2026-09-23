from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.core.models import Profile
from apps.goals.models import Goal
from apps.journal.models import JournalEntry
from apps.projects.models import Project


class JournalViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_empty_state(self):
        response = self.client.get(reverse("journal:list"))
        self.assertContains(response, "Nothing written yet")

    def test_compose_prompt_present(self):
        response = self.client.get(reverse("journal:list"))
        self.assertContains(response, "Write…")

    def test_new_entry_redirects_to_detail(self):
        response = self.client.get(reverse("journal:new"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(JournalEntry.objects.count(), 1)

    def test_autosave_persists_body(self):
        entry = JournalEntry.objects.create()
        response = self.client.post(reverse("journal:autosave", args=[entry.pk]), {
            "date": entry.date.isoformat(), "title": "Today", "mood": "good", "body": "It was a good day.",
        })
        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.body, "It was a good day.")

    def test_soft_delete_hides_entry(self):
        entry = JournalEntry.objects.create(title="Temp")
        self.client.post(reverse("journal:delete", args=[entry.pk]))
        self.assertFalse(JournalEntry.objects.filter(pk=entry.pk).exists())
        self.assertTrue(JournalEntry.all_objects.filter(pk=entry.pk).exists())

    def test_autosave_can_tag_with_project(self):
        """Journal↔Project/Goal is deliberately lightweight metadata, but it
        must still be settable, inspectable, and removable from normal UI —
        not just a dead column only reachable via admin/shell."""
        project = Project.objects.create(name="Northstar")
        entry = JournalEntry.objects.create()
        self.client.post(reverse("journal:autosave", args=[entry.pk]), {
            "date": entry.date.isoformat(), "title": "", "mood": "", "body": "", "project": str(project.pk),
        })
        entry.refresh_from_db()
        self.assertEqual(entry.project_id, project.pk)

    def test_autosave_can_tag_with_goal(self):
        goal = Goal.objects.create(title="Study 100 hours")
        entry = JournalEntry.objects.create()
        self.client.post(reverse("journal:autosave", args=[entry.pk]), {
            "date": entry.date.isoformat(), "title": "", "mood": "", "body": "", "goal": str(goal.pk),
        })
        entry.refresh_from_db()
        self.assertEqual(entry.goal_id, goal.pk)

    def test_autosave_can_remove_project_tag(self):
        project = Project.objects.create(name="Northstar")
        entry = JournalEntry.objects.create(project=project)
        self.client.post(reverse("journal:autosave", args=[entry.pk]), {
            "date": entry.date.isoformat(), "title": "", "mood": "", "body": "", "project": "",
        })
        entry.refresh_from_db()
        self.assertIsNone(entry.project)
        self.assertTrue(Project.objects.filter(pk=project.pk).exists())  # unlink, not delete

    def test_list_filters_by_project(self):
        project = Project.objects.create(name="Northstar")
        JournalEntry.objects.create(title="Project note", project=project)
        JournalEntry.objects.create(title="Unrelated note")
        response = self.client.get(reverse("journal:list"), {"project": project.pk})
        self.assertContains(response, "Project note")
        self.assertNotContains(response, "Unrelated note")

    def test_project_overview_links_to_filtered_journal(self):
        project = Project.objects.create(name="Northstar")
        JournalEntry.objects.create(title="Kickoff thoughts", project=project)
        response = self.client.get(reverse("projects:detail", args=[project.pk]))
        expected_link = f'{reverse("journal:list")}?project={project.pk}'
        self.assertContains(response, expected_link)
